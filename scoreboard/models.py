"""Моделі табло турніру.

Цей файл видається студентові готовим і **не змінюється**: тестовий набір
спирається на наявні поля. Уся робота ПР №2.16.3 відбувається в
``serializers.py``, ``views.py`` і ``urls.py``.
"""

from django.core.validators import MaxValueValidator
from django.db import models


class Team(models.Model):
    name = models.CharField("назва", max_length=60, unique=True)
    short_name = models.CharField("абревіатура", max_length=3)

    class Meta:
        verbose_name = "команда"
        verbose_name_plural = "команди"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tournament(models.Model):
    name = models.CharField("назва", max_length=120)
    slug = models.SlugField("слаг", unique=True)
    starts_on = models.DateField("дата початку")

    class Meta:
        verbose_name = "турнір"
        verbose_name_plural = "турніри"
        ordering = ["starts_on", "id"]

    def __str__(self):
        return self.name


class Match(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "запланований"
        LIVE = "live", "триває"
        FINISHED = "finished", "завершений"

    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name="matches", verbose_name="турнір"
    )
    home = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name="home_matches", verbose_name="господарі"
    )
    away = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name="away_matches", verbose_name="гості"
    )
    starts_at = models.DateTimeField("початок")
    status = models.CharField(
        "стан", max_length=10, choices=Status.choices, default=Status.SCHEDULED
    )

    class Meta:
        verbose_name = "матч"
        verbose_name_plural = "матчі"
        ordering = ["starts_at", "id"]

    def __str__(self):
        return f"{self.home} — {self.away}"


class Event(models.Model):
    class Kind(models.TextChoices):
        GOAL = "goal", "гол"
        CARD = "card", "картка"
        SUB = "sub", "заміна"

    match = models.ForeignKey(
        Match, on_delete=models.CASCADE, related_name="events", verbose_name="матч"
    )
    team = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name="events", verbose_name="команда"
    )
    kind = models.CharField("тип", max_length=10, choices=Kind.choices)
    minute = models.PositiveSmallIntegerField("хвилина", validators=[MaxValueValidator(120)])
    player = models.CharField("гравець", max_length=60)
    created_at = models.DateTimeField("створено", auto_now_add=True)

    class Meta:
        verbose_name = "подія"
        verbose_name_plural = "події"
        ordering = ["minute", "id"]

    def __str__(self):
        return f"{self.get_kind_display()} {self.minute}' — {self.player}"
