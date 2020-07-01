import asyncio
import logging
from itertools import zip_longest

from bs4 import BeautifulSoup
from camelot import read_pdf

from .utils import table_rows, find_funded, make_date, get_school

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


class Parser:
    link_text = ''
    base_url = ''
    url = ''
    pages = ''
    school = None

    def __init__(self):
        self._file = None
        self.source = ''
        self._page = None
        self._general = []
        self._school = None
        self._contract = []
        self._funded_only = []
        self._minus_funded_only = []
        self.students = []

    async def run(self, session, executor):
        logger.debug('Parser is running.')
        await self.get_page(session)
        self._school = await get_school(self.school)
        loop = asyncio.get_event_loop()
        process_task = loop.run_in_executor(executor, self._run)
        finished_parser = await process_task
        logger.debug('Parser finished.')
        return finished_parser

    def __len__(self):
        return len(self.students)

    def __iter__(self):
        for student in self.students:
            yield student

    def add_student(self, student, *, funded):
        raise NotImplementedError("Each Parser subclass must implement it's own method")

    async def get_page(self, session):
        async with session.get(self.url) as response:
            logger.debug(f'Response received with status {response.status}.')
            self._page = await response.read()

    def get_source(self):
        soup = BeautifulSoup(self._page, 'html.parser')
        link_element = soup.find('a', text=self.link_text)
        self.source = self.base_url + link_element.get('href', '')
        return self.source

    def get_file(self):
        file = read_pdf(self.source, pages=self.pages)
        return file

    def _run(self):
        logger.debug('Parsing...')
        self.get_source()
        file = self.get_file()
        logger.debug('File processed.')
        self.parse_tables(file)
        logger.debug(
            f'Parsed, students found: {len(self._general)} general, {len(self._contract)} contract.'
        )
        self._funded_only, self._minus_funded_only = find_funded(self._general, self._contract)
        logger.debug(
            f'Funded only: {len(self._funded_only)}, '
            f'except funded only: {len(self._minus_funded_only)}'
        )

        for student_1, student_2 in zip_longest(self._funded_only, self._minus_funded_only):
            if student_1 is not None:
                self.add_student(student_1, funded=True)
            if student_2 is not None:
                self.add_student(student_2, funded=False)

        logger.debug(f'{len(self)} students added.')

        return self

    def parse_tables(self, file):
        raise NotImplementedError("Each Parser subclass must implement it's own method")

    def clean_rows(self, file):
        raise NotImplementedError("Each Parser subclass must implement it's own method")


class PirogovaParser(Parser):
    link_text = '06.03.01 Биология'
    base_url = 'http://rsmu.ru/'
    url = 'http://rsmu.ru/21087.html'
    pages = 'all'
    school = PIROGOVA

    def __init__(self):
        super().__init__()

    def add_student(self, student, *, funded):
        student_dict = dict(
            name=student[0].lower().title(),
            bvi=True if student[1].lower() == 'да' else False,
            application_date=make_date(student[2]),
            school=self._school,
            funded_only=funded
        )
        self.students.append(student_dict)

    def get_file(self):
        file = super().get_file()
        return file[2:]

    def parse_tables(self, file):
        next_student_number = 1
        current_table = self._general

        for row in self.clean_rows(file):
            if row[0].isdigit() and int(row[0]) == next_student_number:
                next_student_number += 1
            else:
                current_table = self._contract
                next_student_number = 2

            name, bvi, date = row[1], row[4], row[5]
            current_table.append((name, bvi, date))

        logger.debug(
            f'Parsed, students found: {len(self._general)} general, {len(self._contract)} contract.'
        )

    def clean_rows(self, file):
        for row in table_rows(file):
            if row[0] and row[0] != '№':
                yield row


class SechenovaParser(Parser):
    link_text = 'Бакалавриат, специалитет - список лиц подавших документы.pdf'
    link_bvi_text = 'Бакалавриат, специалитет - список лиц подавших документы без ВИ.pdf'
    base_url = 'https://www.sechenov.ru/'
    url = 'https://www.sechenov.ru/admissions/priemnaya-kampaniya-2020/spiski-lits-podavshikh-dokumenty-2020-2021.php'
    pages = '1-4'
    school = SECHENOVA
    bvi = False

    def __init__(self):
        super().__init__()

    def add_student(self, student, *, funded):
        student_dict = dict(
            name=student[0].lower().title(),
            bvi=self.bvi,
            application_date=make_date(student[1]),
            school=self._school,
            funded_only=funded
        )
        self.students.append(student_dict)

    def parse_tables(self, file):
        next_student_number = 1
        current_table = self._contract

        for row in self.clean_rows(file):
            if int(row[0]) == next_student_number:
                next_student_number += 1
            else:
                current_table = self._general
                next_student_number = 2

            name, date = row[1], row[2]
            current_table.append((name, date))

        logger.debug(
            f'Parsed, students found: {len(self._general)} general, {len(self._contract)} contract.'
        )

    def clean_rows(self, file):
        go = False

        for row in table_rows(file):
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
            yield row

    @staticmethod
    def break_predicate(row):
        return '06.05.01' in row[0] and 'особой' in row[0]

    @staticmethod
    def start_predicate(row):
        return '06.05.01' in row[0]


class SechenovaBVIParser(SechenovaParser):
    link_text = 'Бакалавриат, специалитет - список лиц подавших документы без ВИ.pdf'
    pages = 'all'
    bvi = True

    def __init__(self):
        super().__init__()
