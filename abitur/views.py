from json import loads, JSONDecodeError

from aiohttp import ClientConnectionError
from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import View, RedirectView

from .crawler import AsyncCrawler
from .forms import PeriodFilterForm
from .models import Student, sech_count, pirogova_count, sech_bvi_count, sech_funded_only_count, \
    pirogova_funded_only_count, pirogova_winners_count, sechenova_winners_count, pirogova_bvi_count
from .utils import make_checksum, update_records
from .parsers import parser_registry


class AjaxWinnerView(View):

    def post(self, request, *args, **kwargs):
        data = self.decode_request()
        self.update_student(data)
        return HttpResponse(status=200)

    def update_student(self, data):
        student = self.get_student(data)

        if student.is_winner:
            student.is_winner = False
        else:
            student.is_winner = True

        student.save()

    def decode_request(self):
        try:
            data = loads(self.request.body)
        except JSONDecodeError:
            return HttpResponse(status=400)
        return data

    @staticmethod
    def get_student(data):
        student_id = data.get('student_id')
        student = get_object_or_404(Student, pk=student_id)
        return student


class AjaxCheckedView(AjaxWinnerView):

    def update_student(self, data):
        student = self.get_student(data)
        tag = self.get_tag(data)

        if student.is_checked and tag == 'i':
            student.is_checked = False
        else:
            student.is_checked = True
        student.save()

    @staticmethod
    def get_tag(data):
        tag = data.get('tag')
        return tag


class UpdateView(View):
    def post(self, request, *args, **kwargs):
        crawler = AsyncCrawler(*parser_registry)
        try:
            parsers = crawler.crawl()
        except ClientConnectionError:
            messages.error(request, 'Не удалось обновить списки. Попробуйте повторить позже.')
        else:
            update_records(parsers)
            self.update_checksum(parsers)
            cache.get_or_set('initialized', True)

        return redirect('abitur')

    @staticmethod
    def update_checksum(parsers):
        checksum_string = ''.join([make_checksum(parser.source_url) for parser in parsers])
        cache.set('checksum', checksum_string)


class AbiturView(View):
    template_name = 'abitur.html'
    alert_text_ok = 'Обновление не требуется'
    alert_class_ok = 'alert-success'
    alert_text_warning = 'Пора обновить'
    alert_class_warning = 'alert-danger'
    alert_text_error = 'Не удалось проверить обновления'
    alert_class_error = 'alert-danger'

    def get(self, request, *args, **kwargs):
        initialized = cache.get('initialized', False)
        form = PeriodFilterForm(self.request.GET)

        if not initialized:
            ctx = {
                'form': form,
                'alert_text': self.alert_text_warning,
                'alert_class': self.alert_class_warning
            }
        else:
            ctx = self.get_context(form)

        return render(request, 'abitur/abitur.html', ctx)

    def get_context(self, form):
        period = form.get_period()

        students = Student.objects.select_related('school').all()
        students_filtered = students.filter(period)
        alert_text, alert_class = self.check_sources()

        ctx = {
            'form': form,
            'students': students_filtered,
            'sech_count': sech_count(students),
            'pirogova_count': pirogova_count(students),
            'sech_bvi_count': sech_bvi_count(students),
            'pirogova_bvi_count': pirogova_bvi_count(students),
            'total_count': students.count(),
            'sech_funded_only_count': sech_funded_only_count(students),
            'pirogova_funded_only_count': pirogova_funded_only_count(students),
            'pirogova_winners_count': pirogova_winners_count(students),
            'sechenova_winners_count': sechenova_winners_count(students),
            'alert_text': alert_text,
            'alert_class': alert_class,
        }

        return ctx

    def check_sources(self):
        checksum = self.total_checksum()

        if checksum is None:
            return self.alert_text_error, self.alert_class_error

        cached_checksum = cache.get('checksum')

        if cached_checksum:
            if cached_checksum != checksum:
                return self.alert_text_warning, self.alert_class_warning
            return self.alert_text_ok, self.alert_class_ok

    @staticmethod
    def total_checksum():
        crawler = AsyncCrawler(*parser_registry)
        try:
            sources = crawler.get_sources()
        except ClientConnectionError:
            return None
        return ''.join([make_checksum(link) for link in sources])


class HomeView(RedirectView):
    url = reverse_lazy('abitur')
