import asyncio
import logging

from collections import namedtuple

from bs4 import BeautifulSoup
from camelot import read_pdf
from aiohttp import ClientConnectionError

from .utils import table_rows, make_date, get_school


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(process)d - %(name)s - %(funcName)s - %(message)s', datefmt='[%H:%M:%S]'
)
h = logging.StreamHandler()
h.setFormatter(formatter)
logger.addHandler(h)

PIROGOVA = "Пироговка"
SECHENOVA = 'Сеченовка'
pirogova_categories = namedtuple(
    'pirogova_categories', 'bvi special general contract')
sechenova_categories = namedtuple(
    'sechenova_categories', 'contract general')
sechenova_bvi_categories = namedtuple(
    'sechenova_bvi_categories', 'general contract')

parser_registry = []


def register(parser_class):
    parser_registry.append(parser_class)
    return parser_class


class Category:

    def __init__(self, raw_students, bvi=False, funded_only=False):
        self.bvi = bvi
        self.funded_only = funded_only
        self._students = raw_students

    def __len__(self):
        return len(self._students)

    def __iter__(self):
        for student in self._students:
            yield student

    def make_student(self, name, date, school):
        student = dict(
            name=name.lower().title(),
            bvi=self.bvi,
            application_date=make_date(date),
            school=school,
            funded_only=self.funded_only
        )
        return student


class Parser:
    link_text = ''
    base_url = ''
    page_url = ''
    pages = ''
    school_name = None

    def __init__(self):
        self._raw_categories = None
        self.categories = {}
        self._page = None
        self._school = None
        self.source_url = ''

    async def run(self, session, executor):
        logger.debug('Parser is running.')
        await self.get_page(session)
        self._school = await get_school(self.school_name)
        loop = asyncio.get_event_loop()
        process_task = loop.run_in_executor(executor, self._run)
        finished_parser = await process_task
        logger.debug('Parser finished.')
        return finished_parser

    def __len__(self):
        return sum([len(category) for category in self.categories.values()])

    def __iter__(self):
        for category in self.categories.values():
            for student in category:
                yield category.make_student(*student, self._school)

    async def get_page(self, session):
        async with session.get(self.page_url) as response:
            logger.debug(f'Response received with status {response.status}.')
            if response.status != 200:
                raise ClientConnectionError()
            self._page = await response.read()

    def get_source(self):
        soup = BeautifulSoup(self._page, 'html.parser')
        link_element = soup.find('a', text=self.link_text)

        if not link_element:
            raise ClientConnectionError('Link not found')

        self.source_url = self.base_url + link_element.get('href', '')

    def get_file(self):
        self.get_source()
        file = read_pdf(self.source_url, pages=self.pages)
        return file

    def _run(self):
        logger.debug('Parsing...')
        file = self.get_file()
        logger.debug('File processed.')
        self.parse_tables(file)
        logger.debug(f'{len(self)} students added.')
        return self

    def parse_tables(self, file):
        next_student_number = 1
        current_category_index = 0
        current_category = self._raw_categories[current_category_index]

        for row, name_index, date_index in self.clean_rows(file):
            if int(row[0]) == next_student_number:
                next_student_number += 1
            else:
                current_category_index += 1
                current_category = self._raw_categories[current_category_index]
                next_student_number = 2

            name, date = row[name_index], row[date_index]
            current_category.append((name, date))

        self.clean_categories()

    def clean_rows(self, file):
        raise NotImplementedError("Each Parser subclass must implement it's own method")

    def clean_categories(self):
        raise NotImplementedError("Each Parser subclass must implement it's own method")


@register
class PirogovaParser(Parser):
    link_text = '06.03.01 Биология'
    base_url = 'http://rsmu.ru/'
    page_url = 'http://rsmu.ru/21087.html'
    pages = 'all'
    school_name = PIROGOVA

    def __init__(self):
        super().__init__()
        self._raw_categories = pirogova_categories(bvi=[], special=[], general=[], contract=[])

    def clean_rows(self, file):
        for row, name_index, date_index in table_rows(file, self.find_columns):
            if row[0] and row[0] != '№':
                yield row, name_index, date_index

    def clean_categories(self):
        general_set = set(self._raw_categories.general) ^ set(self._raw_categories.bvi)
        contract_set = set(self._raw_categories.contract)
        funded_only = general_set - contract_set
        except_funded_only = general_set - funded_only

        self.categories = {
            'bvi': Category(self._raw_categories.bvi, bvi=True),
            'funded_only': Category(funded_only, funded_only=True),
            'general': Category(except_funded_only)
        }

    @staticmethod
    def find_columns(table):
        head_row = table.data[0]
        try:
            date = head_row.index('Дата подачи \nзаявления')
            name = head_row.index('Фамилия, имя, отчество')
        except ValueError as e:
            raise ValueError('Column not found in row') from e
        return name, date


@register
class SechenovaParser(Parser):
    link_text = 'Бакалавриат, специалитет - список лиц подавших документы.pdf'
    link_bvi_text = 'Бакалавриат, специалитет - список лиц подавших документы без ВИ.pdf'
    base_url = 'https://www.sechenov.ru/'
    page_url = 'https://www.sechenov.ru/admissions/priemnaya-kampaniya-2020/' \
               'spiski-lits-podavshikh-dokumenty-2020-2021.php'
    pages = '1-6'
    school_name = SECHENOVA

    def __init__(self):
        super().__init__()
        self._raw_categories = sechenova_categories(contract=[], general=[])

    def clean_rows(self, file):
        go = False

        for row, name_index, date_index in table_rows(file, self.find_columns):
            if self.start_predicate(row):
                go = True
            if not go:
                continue
            if self.break_predicate(row):
                break
            if '\n' in row[0]:
                row = row[0].split('\n')
            if not row[0].isdigit():
                continue
            yield row, name_index, date_index

    def clean_categories(self):
        general_set = set(self._raw_categories.general)
        contract_set = set(self._raw_categories.contract)
        funded_only = general_set - contract_set
        except_funded_only = general_set - funded_only

        self.categories = {
            'funded_only': Category(funded_only, funded_only=True),
            'general': Category(except_funded_only)
        }

    @staticmethod
    def break_predicate(row):
        return ('06.05.01' in row[0] and 'особой' in row[0]) or '19.03.01' in row[0]

    @staticmethod
    def start_predicate(row):
        return '06.05.01' in row[0]

    @staticmethod
    def find_columns(_):
        name_index = 1
        date_index = 2
        return name_index, date_index


@register
class SechenovaBVIParser(SechenovaParser):
    link_text = 'Бакалавриат, специалитет - список лиц подавших документы без ВИ.pdf'
    pages = 'all'

    def __init__(self):
        super().__init__()
        self._raw_categories = sechenova_bvi_categories(general=[], contract=[])

    def clean_categories(self):
        general_set = set(self._raw_categories.general)
        contract_set = set(self._raw_categories.contract)
        funded_only = general_set - contract_set
        except_funded_only = general_set - funded_only

        self.categories = {
            'funded_only': Category(funded_only, bvi=True, funded_only=True),
            'general': Category(except_funded_only, bvi=True),
        }
