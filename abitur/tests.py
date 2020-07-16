import os
from unittest import TestCase, TestSuite
from unittest.mock import patch, MagicMock

from django.urls import reverse

from abitur.models import Student
from abitur.parsers import PirogovaParser, SechenovaParser, SechenovaBVIParser
from django.conf import settings
from django.test import TestCase as DjangoTestCase
from json import load


def mock_pdf(data):
    tables = [MagicMock(data=table) for table in data]
    mock = MagicMock()
    mock.__iter__.return_value = tables
    return mock


class ParserTestCase(TestCase):
    app = 'abitur'
    fixtures_dir = 'fixtures'
    file_name = ''
    page_name = ''
    data_name = ''
    parser_class = None
    expected_source = ''

    @classmethod
    def setUpClass(cls):
        file_path = os.path.join(settings.BASE_DIR, cls.app, cls.fixtures_dir, cls.file_name)
        page_path = os.path.join(settings.BASE_DIR, cls.app, cls.fixtures_dir, cls.page_name)
        data_path = os.path.join(settings.BASE_DIR, cls.app, cls.fixtures_dir, cls.data_name)

        cls.parser = cls.parser_class()

        with open(file_path, 'rb') as file:
            cls.file = file.read()

        with open(page_path, 'rb') as page:
            cls.page = page.read()

        with open(data_path) as data:
            cls.data = load(data)

        cls.parser._page = cls.page

    def test_get_source(self):
        self.parser.get_source()

        self.assertEqual(
            self.parser.source_url, self.expected_source, 'get_source returns correct source url'
        )

    @patch('abitur.parsers.PirogovaParser.get_source')
    @patch('abitur.parsers.read_pdf')
    def test_get_file(self, mock_read_pdf, _):
        mock_read_pdf.return_value = self.file
        file = self.parser.get_file()

        self.assertEqual(file, self.file, 'get_file returns a file produced by read_pdf')


class PirogovaParserTest(ParserTestCase):
    file_name = 'pirogova_list.pdf'
    page_name = 'pirogova_page.html'
    data_name = 'pirogova_data.json'
    parser_class = PirogovaParser
    expected_source = 'http://rsmu.ru/fileadmin/rsmu/img/abiturients/2020/03_07_2020_biologija.pdf'

    def test_parse_tables(self):
        pdf_mock = mock_pdf(self.data)
        self.parser.parse_tables(pdf_mock)
        expected_bvi = 1
        expected_funded_only = 27
        expected_others = 34
        expected_total = expected_bvi + expected_others + expected_funded_only

        self.assertEqual(len(self.parser), expected_total)
        self.assertEqual(len(self.parser.categories['bvi']), expected_bvi)
        self.assertEqual(len(self.parser.categories['funded_only']), expected_funded_only)
        self.assertEqual(len(self.parser.categories['general']), expected_others)


class SechenovaParserTest(ParserTestCase):
    file_name = 'sechenova_list.pdf'
    page_name = 'sechenova_page.html'
    data_name = 'sechenova_data.json'
    parser_class = SechenovaParser
    expected_source = 'https://www.sechenov.ru/upload/iblock/d62/' \
                      'Bakalavriat_-spetsialitet-_-spisok-lits-podavshikh-dokumenty.pdf'

    def test_parse_tables(self):
        pdf_mock = mock_pdf(self.data)
        self.parser.parse_tables(pdf_mock)
        expected_funded_only = 28
        expected_others = 46
        expected_total = expected_others + expected_funded_only

        self.assertEqual(len(self.parser), expected_total)
        self.assertEqual(len(self.parser.categories['funded_only']), expected_funded_only)
        self.assertEqual(len(self.parser.categories['general']), expected_others)


class SechenovaBVIParserTest(ParserTestCase):
    file_name = 'sechenova_bvi_list.pdf'
    page_name = 'sechenova_page.html'
    data_name = 'sechenova_bvi_data.json'
    parser_class = SechenovaBVIParser
    expected_source = 'https://www.sechenov.ru/upload/iblock/5b9/' \
                      'Bakalavriat_-spetsialitet-_-spisok-lits-podavshikh-dokumenty-bez-VI.pdf'

    def test_parse_tables(self):
        pdf_mock = mock_pdf(self.data)
        self.parser.parse_tables(pdf_mock)
        expected_total = 0

        self.assertEqual(len(self.parser), expected_total)


class ViewTests(DjangoTestCase):
    fixtures = ['students.json']

    def test_abitur_view(self):
        path = reverse('abitur')
        response = self.client.get(path)

        self.assertEqual(response.status_code, 200)

    def test_check_view(self):
        path = reverse('check-student')
        student = Student.objects.first()
        before_check = student.is_checked
        payload = {'tag': 'i', 'student_id': student.id}
        response = self.client.post(path, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(not before_check)

    def test_winner_view(self):
        path = reverse('olympics-winner')
        random_student = Student.objects.first()
        before_check = random_student.is_winner
        payload = {'student_id': random_student.id}
        response = self.client.post(path, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(not before_check)


test_cases = (PirogovaParserTest, SechenovaParserTest, SechenovaBVIParserTest, ViewTests)


def load_tests(loader, *_):
    suite = TestSuite()
    for test_case in test_cases:
        tests = loader.loadTestsFromTestCase(test_case)
        suite.addTests(tests)
    return suite
