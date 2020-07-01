from django.db import models

SECHENOVA = "Сеченовка"
PIROGOVA = "Пироговка"


class Student(models.Model):
    name = models.CharField(
        max_length=100,
    )
    school = models.ForeignKey(
        'School',
        on_delete=models.DO_NOTHING,
        related_name='students'
    )
    bvi = models.BooleanField()
    application_date = models.DateField()
    funded_only = models.BooleanField()
    is_checked = models.BooleanField(
        default=False,
    )
    is_winner = models.BooleanField(
        default=False,
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-application_date']


class School(models.Model):
    name = models.CharField(
        max_length=100,
    )

    def __str__(self):
        return self.name


def sech_count(qs):
    return qs.filter(school__name=SECHENOVA).count()


def sech_bvi_count(qs):
    return qs.filter(school__name=SECHENOVA, bvi=True).count()


def pirogova_count(qs):
    return qs.filter(school__name=PIROGOVA).count()


def pirogova_bvi_count(qs):
    return qs.filter(school__name=PIROGOVA, bvi=True).count()


def sech_funded_only_count(qs):
    return qs.filter(school__name=SECHENOVA, funded_only=True).count()


def pirogova_funded_only_count(qs):
    return qs.filter(school__name=PIROGOVA, funded_only=True).count()


def pirogova_winners_count(qs):
    return qs.filter(school__name=PIROGOVA, is_winner=True).count()


def sechenova_winners_count(qs):
    return qs.filter(school__name=SECHENOVA, is_winner=True).count()
