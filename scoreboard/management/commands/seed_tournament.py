"""Сид для ПР №2.16.3.

Створює турнір `kubok-it21` із трьома матчами — по одному в кожному стані.
Тестовий набір спирається саме на цей турнір: три матчі, шість команд,
завершений матч із рахунком 2:1.

    python manage.py seed_tournament            # ідемпотентно, нічого не ламає
    python manage.py seed_tournament --flush    # стерти все й насипати заново
"""

import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from scoreboard.models import Event, Match, Team, Tournament

SLUG = "kubok-it21"

TEAMS = [
    ("Соколи", "СОК"),
    ("Леви", "ЛЕВ"),
    ("Вовки", "ВОВ"),
    ("Орли", "ОРЛ"),
    ("Тигри", "ТИГ"),
    ("Бобри", "БОБ"),
]


def aware(year, month, day, hour):
    naive = datetime.datetime(year, month, day, hour, 0)
    return timezone.make_aware(naive, datetime.timezone.utc)


class Command(BaseCommand):
    help = "Створює демо-турнір для ПР №2.16.3"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="стерти всі турніри, матчі, події і команди перед сидом",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            Event.objects.all().delete()
            Match.objects.all().delete()
            Tournament.objects.all().delete()
            Team.objects.all().delete()
            self.stdout.write("Старі дані стерті.")

        teams = {}
        for name, short_name in TEAMS:
            team, _ = Team.objects.get_or_create(name=name, defaults={"short_name": short_name})
            teams[name] = team

        tournament, created = Tournament.objects.get_or_create(
            slug=SLUG,
            defaults={"name": "Кубок ІТ-21", "starts_on": datetime.date(2026, 11, 10)},
        )
        if not created and tournament.matches.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Турнір {SLUG} уже має матчі — сид не чіпає їх. "
                    "Для чистого стану запустіть із --flush."
                )
            )
            return

        finished = Match.objects.create(
            tournament=tournament,
            home=teams["Соколи"],
            away=teams["Леви"],
            starts_at=aware(2026, 11, 10, 10),
            status=Match.Status.FINISHED,
        )
        Event.objects.bulk_create(
            [
                Event(match=finished, team=teams["Соколи"], kind=Event.Kind.GOAL,
                      minute=12, player="Петренко"),
                Event(match=finished, team=teams["Леви"], kind=Event.Kind.GOAL,
                      minute=34, player="Іваненко"),
                Event(match=finished, team=teams["Соколи"], kind=Event.Kind.GOAL,
                      minute=77, player="Петренко"),
                Event(match=finished, team=teams["Леви"], kind=Event.Kind.CARD,
                      minute=80, player="Коваленко"),
            ]
        )

        live = Match.objects.create(
            tournament=tournament,
            home=teams["Вовки"],
            away=teams["Орли"],
            starts_at=aware(2026, 11, 10, 12),
            status=Match.Status.LIVE,
        )
        Event.objects.bulk_create(
            [
                Event(match=live, team=teams["Вовки"], kind=Event.Kind.GOAL,
                      minute=20, player="Шевчук"),
                Event(match=live, team=teams["Орли"], kind=Event.Kind.GOAL,
                      minute=55, player="Мельник"),
            ]
        )

        Match.objects.create(
            tournament=tournament,
            home=teams["Тигри"],
            away=teams["Бобри"],
            starts_at=aware(2026, 11, 10, 14),
            status=Match.Status.SCHEDULED,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: турнір {SLUG}, {len(TEAMS)} команд, 3 матчі "
                "(finished 2:1, live 1:1, scheduled)."
            )
        )
