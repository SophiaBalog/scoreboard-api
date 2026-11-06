"""Серіалізатори табло. Усі `fields` перелічені явно — без "__all__"."""

import datetime

from rest_framework import serializers

from .models import Event, Match, Tournament


class TournamentSerializer(serializers.ModelSerializer):
    # Лише читання: кількість матчів турніру (related_name="matches").
    matches_count = serializers.IntegerField(source="matches.count", read_only=True)

    class Meta:
        model = Tournament
        fields = ["id", "slug", "name", "starts_on", "matches_count"]


class MatchSerializer(serializers.ModelSerializer):
    home_name = serializers.CharField(source="home.name", read_only=True)
    away_name = serializers.CharField(source="away.name", read_only=True)
    score = serializers.SerializerMethodField()
    # Контракт віддає час у UTC із суфіксом Z, незалежно від TIME_ZONE проєкту.
    starts_at = serializers.DateTimeField(default_timezone=datetime.timezone.utc)

    class Meta:
        model = Match
        fields = [
            "id", "tournament", "home", "away",
            "home_name", "away_name", "starts_at", "status", "score",
        ]

    def get_score(self, obj):
        """Рахунок не зберігається — рахуємо лише з подій kind="goal"."""
        goals = obj.events.filter(kind=Event.Kind.GOAL)
        return {
            "home": goals.filter(team_id=obj.home_id).count(),
            "away": goals.filter(team_id=obj.away_id).count(),
        }

    def validate(self, attrs):
        # При PATCH у attrs може не бути home/away — беремо їх із наявного матчу.
        home = attrs.get("home", getattr(self.instance, "home", None))
        away = attrs.get("away", getattr(self.instance, "away", None))
        if home is not None and home == away:
            raise serializers.ValidationError(
                {"away": ["Команда не може грати сама із собою."]}
            )
        return attrs


class EventSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = Event
        fields = ["id", "kind", "minute", "player", "team", "team_name"]

    def validate_team(self, team):
        # Матч передає в'юха: EventSerializer(data=..., context={"match": match})
        match = self.context["match"]
        if team.pk not in (match.home_id, match.away_id):
            raise serializers.ValidationError("Команда не грає в цьому матчі.")
        return team
