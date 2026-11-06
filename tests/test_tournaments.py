"""Турніри: конверт пагінації, пошук за слагом, read-only колекція."""

PAGINATION_KEYS = {"count", "next", "previous", "results"}
TOURNAMENT_KEYS = {"id", "slug", "name", "starts_on", "matches_count"}


def test_list_has_pagination_envelope(api):
    response = api.get("/api/v1/tournaments/")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == PAGINATION_KEYS, (
        "Список колекції віддається в конверті {count, next, previous, results}. "
        "Голий масив означає, що пагінація не підключена."
    )
    assert isinstance(body["results"], list)


def test_tournament_object_shape(tournament):
    assert set(tournament) == TOURNAMENT_KEYS
    assert isinstance(tournament["matches_count"], int)


def test_lookup_is_by_slug_not_id(api, tournament):
    """Деталі турніру шукаються за слагом. Адреса з id контрактом не передбачена."""
    by_slug = api.get(f"/api/v1/tournaments/{tournament['slug']}/")
    assert by_slug.status_code == 200
    assert by_slug.json()["slug"] == tournament["slug"]


def test_unknown_slug_gives_404_with_detail(api):
    response = api.get("/api/v1/tournaments/nemaie-takoho-turniru/")
    assert response.status_code == 404
    assert "detail" in response.json(), "404 має віддавати {\"detail\": \"...\"}"


def test_collection_is_read_only(api, tournament):
    response = api.post(
        "/api/v1/tournaments/",
        json={"name": "Лівий турнір", "slug": "livyi", "starts_on": "2030-01-01"},
    )
    assert response.status_code == 405, (
        "Турніри доступні лише для читання — потрібен ReadOnlyModelViewSet, "
        "а не ModelViewSet."
    )
