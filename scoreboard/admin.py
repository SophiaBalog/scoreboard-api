from django.contrib import admin

from .models import Event, Match, Team, Tournament


class EventInline(admin.TabularInline):
    model = Event
    extra = 0


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "short_name"]


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "starts_on"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ["__str__", "tournament", "starts_at", "status"]
    list_filter = ["status", "tournament"]
    inlines = [EventInline]
