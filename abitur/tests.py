import os
from unittest import TestCase
from unittest.mock import patch
from abitur.parsers import PirogovaParser
from django.conf import settings
import camelot


class PirogovaParserTest(TestCase):
    file_path = os.path.join(settings.BASE_DIR, 'abitur', 'fixtures', 'pirogova_list.pdf')
    page_path = os.path.join(settings.BASE_DIR, 'abitur', 'fixtures', 'pirogova_page.html')
    source_url = 'http://rsmu.ru/fileadmin/rsmu/img/abiturients/2020/03_07_2020_biologija.pdf'

    @classmethod
    def setUpClass(cls):
        cls.parser = PirogovaParser()

        with open(cls.file_path, 'rb') as file:
            cls.file = file.read()

        with open(cls.page_path, 'rb') as page:
            cls.page = page.read()

        cls.parser._page = cls.page

    def test_get_source(self):
        self.parser.get_source()

        self.assertEqual(self.parser.source_url, self.source_url)

    @patch('abitur.parsers.PirogovaParser.get_source')
    @patch('abitur.parsers.read_pdf')
    def test_get_file(self, mock_read_pdf, _):
        mock_read_pdf.return_value = self.file
        file = self.parser.get_file()

        self.assertEqual(file, self.file)

    def test_parse_tables(self):
        pdf = camelot.read_pdf(self.file_path, pages='all')
        self.parser.parse_tables(pdf)
        expected_total = 62
        expected_bvi = 1
        expected_funded_only = 27
        expected_others = 34

        self.assertEqual(len(self.parser), expected_total)
        self.assertEqual(len(self.parser.categories[0]), expected_bvi)
        self.assertEqual(len(self.parser.categories[1]), expected_funded_only)
        self.assertEqual(len(self.parser.categories[2]), expected_others)
