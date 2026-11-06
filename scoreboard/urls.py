from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("tournaments", views.TournamentViewSet, basename="tournament")
# basename="match" дає ім'я маршруту "match-detail", яке потрібне для Location.
router.register("matches", views.MatchViewSet, basename="match")

urlpatterns = [
    path("api/v1/", include(router.urls)),
    path("api/v1/scoreboard/", views.scoreboard, name="scoreboard"),
]
