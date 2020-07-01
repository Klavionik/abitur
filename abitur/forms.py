from django import forms
from datetime import date, timedelta
from django.db.models import Q


class PeriodFilterForm(forms.Form):
    last_three_days = 'default'
    last_week = 'week'
    last_month = 'month'
    all = 'all'

    PERIOD_CHOICES = (
        (last_three_days, 'За три дня'),
        (last_week, 'За неделю'),
        (last_month, 'За месяц'),
        (all, 'За все время'),
    )

    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        required=False,
    )

    def is_valid(self):
        if super().is_valid():
            period = self.cleaned_data['period']
            if period == self.last_week:
                return Q(application_date__gte=date.today() - timedelta(days=7))
            if period == self.last_month:
                return Q(application_date__month=date.today().month)
            if period == self.all:
                return Q()
        return Q(application_date__gte=date.today() - timedelta(days=3))

    def get_period(self):
        return self.is_valid()
