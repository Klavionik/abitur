from datetime import datetime
from zlib import adler32
from itertools import chain

from asgiref.sync import sync_to_async

from abitur.models import Student, School


def find_funded(general, contract):
    general_set = set(general)
    contract_set = set(contract)
    funded_only = general_set - contract_set
    except_funded_only = general_set - funded_only

    return funded_only, except_funded_only


def table_rows(pdf_file, find_column_indices):
    for table in pdf_file:
        name_index, date_index = find_column_indices(table)
        for row in table.data:
            yield row, name_index, date_index


def make_date(string):
    return datetime.strptime(string, '%d.%m.%Y')


def make_checksum(link):
    return str(adler32(link.encode()))


def update_records(parsers):
    for student_dict in chain.from_iterable(parsers):
        Student.objects.get_or_create(**student_dict)


@sync_to_async
def get_school(name):
    return School.objects.get(name=name)
