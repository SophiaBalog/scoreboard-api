"""Матчі: форма об'єкта, створення, переходи стану, заборонені методи."""

PAGINATION_KEYS = {"count", "next", "previous", "results"}
MATCH_KEYS = {
    "id", "tournament", "home", "away", "home_name", "away_name",
    "starts_at", "status", "score",
}


def test_list_has_pagination_envelope(api):
    response = api.get("/api/v1/matches/")
    assert response.status_code == 200
    assert set(response.json()) == PAGINATION_KEYS


def test_match_object_shape(finished_match):
    assert set(finished_match) == MATCH_KEYS, (
        "Набір полів матчу перевіряється точно. Зайве поле — теж розбіжність "
        "із контрактом: fields треба перелічувати явно, а не через \"__all__\"."
    )
    assert isinstance(finished_match["home_name"], str)
    assert isinstance(finished_match["away_name"], str)


def test_score_is_counted_from_goal_events(finished_match):
    assert "score" in finished_match, (
        "У матчі немає поля score. Його не віддає ModelSerializer сам — "
        "рахунок доводиться рахувати, бо в моделі його немає."
    )
    score = finished_match["score"]
    assert set(score) == {"home", "away"}
    assert (score["home"], score["away"]) == (2, 1), (
        "У сидованому завершеному матчі три голи і одна картка. "
        "Рахунок 2:1 — якщо вийшло 2:2, у підрахунок потрапила картка."
    )


def test_create_returns_201_and_location(api, new_match):
    match = new_match()
    detail = api.get(f"/api/v1/matches/{match['id']}/")
    assert detail.status_code == 200

    response = api.post(
        "/api/v1/matches/",
        json={
            "tournament": match["tournament"],
            "home": match["home"],
            "away": match["away"],
            "starts_at": "2030-02-02T20:00:00Z",
        },
    )
    assert response.status_code == 201
    assert "Location" in response.headers, (
        "DRF не додає Location сам — заголовок треба поставити у create()."
    )
    assert str(response.json()["id"]) in response.headers["Location"]
    api.delete(f"/api/v1/matches/{response.json()['id']}/")


def test_create_ignores_status_from_body(api, tournament, team_ids):
    response = api.post(
        "/api/v1/matches/",
        json={
            "tournament": tournament["id"],
            "home": team_ids[0],
            "away": team_ids[1],
            "starts_at": "2030-03-03T20:00:00Z",
            "status": "live",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "scheduled", (
        "Новий матч завжди scheduled: стан змінюється лише переходами, "
        "а не довільним значенням у тілі POST."
    )
    api.delete(f"/api/v1/matches/{response.json()['id']}/")


def test_same_team_on_both_sides_gives_400(api, tournament, team_ids):
    response = api.post(
        "/api/v1/matches/",
        json={
            "tournament": tournament["id"],
            "home": team_ids[0],
            "away": team_ids[0],
            "starts_at": "2030-04-04T20:00:00Z",
        },
    )
    assert response.status_code == 400
    assert "away" in response.json(), (
        "Помилка має прийти словником за полями, під ключем away."
    )


def test_unknown_tournament_gives_400_not_500(api, team_ids):
    response = api.post(
        "/api/v1/matches/",
        json={
            "tournament": 10 ** 9,
            "home": team_ids[0],
            "away": team_ids[1],
            "starts_at": "2030-05-05T20:00:00Z",
        },
    )
    assert response.status_code == 400, (
        "Неіснуючий id у зв'язку — це 400 від PrimaryKeyRelatedField, не 500."
    )


def test_put_is_not_allowed(api, new_match):
    match = new_match()
    response = api.put(
        f"/api/v1/matches/{match['id']}/",
        json={
            "tournament": match["tournament"],
            "home": match["home"],
            "away": match["away"],
            "starts_at": "2030-06-06T20:00:00Z",
            "status": "live",
        },
    )
    assert response.status_code == 405, (
        "Повна заміна матчу контрактом не передбачена: обмежте http_method_names."
    )


def test_scheduled_to_live_is_allowed(api, new_match):
    match = new_match()
    response = api.patch(f"/api/v1/matches/{match['id']}/", json={"status": "live"})
    assert response.status_code == 200
    assert response.json()["status"] == "live"


def test_live_to_finished_is_allowed(api, live_match):
    response = api.patch(f"/api/v1/matches/{live_match['id']}/", json={"status": "finished"})
    assert response.status_code == 200
    assert response.json()["status"] == "finished"


def test_scheduled_to_finished_is_conflict(api, new_match):
    match = new_match()
    response = api.patch(f"/api/v1/matches/{match['id']}/", json={"status": "finished"})
    assert response.status_code == 409, (
        "Матч не може завершитись, не почавшись. Це конфлікт стану (409), "
        "а не помилка валідації (400)."
    )
    body = response.json()
    assert body.get("code") == "invalid_status_transition"
    assert "detail" in body


def test_live_to_scheduled_is_conflict(api, live_match):
    response = api.patch(f"/api/v1/matches/{live_match['id']}/", json={"status": "scheduled"})
    assert response.status_code == 409
    assert response.json().get("code") == "invalid_status_transition"


def test_same_status_is_not_a_conflict(api, new_match):
    match = new_match()
    response = api.patch(f"/api/v1/matches/{match['id']}/", json={"status": "scheduled"})
    assert response.status_code == 200, (
        "PATCH із тим самим станом нічого не змінює і конфліктом не є."
    )


def test_patch_without_status_works(api, new_match):
    match = new_match()
    response = api.patch(
        f"/api/v1/matches/{match['id']}/", json={"starts_at": "2030-07-07T20:00:00Z"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "scheduled"


def test_delete_scheduled_then_404(api, tournament, team_ids):
    created = api.post(
        "/api/v1/matches/",
        json={
            "tournament": tournament["id"],
            "home": team_ids[0],
            "away": team_ids[1],
            "starts_at": "2030-08-08T20:00:00Z",
        },
    )
    match_id = created.json()["id"]

    first = api.delete(f"/api/v1/matches/{match_id}/")
    assert first.status_code == 204
    assert first.content == b"", "204 віддається без тіла."

    second = api.delete(f"/api/v1/matches/{match_id}/")
    assert second.status_code == 404, "Повторне видалення — 404, а не 204."


def test_delete_started_match_is_conflict(api, live_match):
    response = api.delete(f"/api/v1/matches/{live_match['id']}/")
    assert response.status_code == 409
    assert response.json().get("code") == "match_started"


def test_unknown_match_gives_404(api):
    response = api.get("/api/v1/matches/999999999/")
    assert response.status_code == 404
    assert "detail" in response.json()
