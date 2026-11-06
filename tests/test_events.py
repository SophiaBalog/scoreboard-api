"""Події матчу: вкладений ресурс, стан матчу, порядок перевірок 404 → 409 → 400."""

EVENT_KEYS = {"id", "kind", "minute", "player", "team", "team_name"}


def test_events_list_is_a_bare_array(api, finished_match):
    response = api.get(f"/api/v1/matches/{finished_match['id']}/events/")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list), (
        "Вкладений список віддається голим масивом: пагінація generic-класів "
        "на @action не розповсюджується."
    )
    assert len(body) == 4, "У сидованому завершеному матчі чотири події."
    assert set(body[0]) == EVENT_KEYS


def test_events_are_ordered_by_minute(api, finished_match):
    response = api.get(f"/api/v1/matches/{finished_match['id']}/events/")
    assert response.status_code == 200, response.text[:300]
    minutes = [event["minute"] for event in response.json()]
    assert minutes == sorted(minutes)


def test_events_of_unknown_match_give_404(api):
    response = api.get("/api/v1/matches/999999999/events/")
    assert response.status_code == 404


def test_add_event_to_live_match(api, live_match, team_ids):
    response = api.post(
        f"/api/v1/matches/{live_match['id']}/events/",
        json={"kind": "goal", "minute": 23, "player": "Петренко", "team": live_match["home"]},
    )
    assert response.status_code == 201, response.text[:300]
    assert set(response.json()) == EVENT_KEYS

    listing = api.get(f"/api/v1/matches/{live_match['id']}/events/")
    assert [event["id"] for event in listing.json()] == [response.json()["id"]]


def test_goal_changes_the_score(api, live_match):
    api.post(
        f"/api/v1/matches/{live_match['id']}/events/",
        json={"kind": "goal", "minute": 10, "player": "Шевчук", "team": live_match["home"]},
    )
    api.post(
        f"/api/v1/matches/{live_match['id']}/events/",
        json={"kind": "card", "minute": 11, "player": "Шевчук", "team": live_match["home"]},
    )
    match = api.get(f"/api/v1/matches/{live_match['id']}/").json()
    assert "score" in match, "У матчі немає поля score — див. контракт."
    assert match["score"] == {"home": 1, "away": 0}, (
        "Рахунок рахується лише з подій kind=goal."
    )


def test_event_in_scheduled_match_is_conflict(api, new_match):
    match = new_match()
    response = api.post(
        f"/api/v1/matches/{match['id']}/events/",
        json={"kind": "goal", "minute": 5, "player": "Хтось", "team": match["home"]},
    )
    assert response.status_code == 409
    body = response.json()
    assert body.get("code") == "match_not_live"
    assert "detail" in body


def test_event_in_finished_match_is_conflict(api, finished_match):
    response = api.post(
        f"/api/v1/matches/{finished_match['id']}/events/",
        json={"kind": "goal", "minute": 90, "player": "Хтось", "team": finished_match["home"]},
    )
    assert response.status_code == 409
    assert response.json().get("code") == "match_not_live"


def test_foreign_team_gives_400(api, live_match, team_ids):
    foreign = next(
        team_id for team_id in team_ids
        if team_id not in (live_match["home"], live_match["away"])
    )
    response = api.post(
        f"/api/v1/matches/{live_match['id']}/events/",
        json={"kind": "goal", "minute": 30, "player": "Чужий", "team": foreign},
    )
    assert response.status_code == 400
    assert "team" in response.json(), (
        "Команда, яка не грає в цьому матчі, — помилка поля team. "
        "Перевірку робить сам серіалізатор, бо йому передано контекст матчу."
    )


def test_minute_above_120_gives_400(api, live_match):
    response = api.post(
        f"/api/v1/matches/{live_match['id']}/events/",
        json={"kind": "goal", "minute": 121, "player": "Пізній", "team": live_match["home"]},
    )
    assert response.status_code == 400
    assert "minute" in response.json()


def test_unknown_kind_gives_400(api, live_match):
    response = api.post(
        f"/api/v1/matches/{live_match['id']}/events/",
        json={"kind": "penalty", "minute": 40, "player": "Хтось", "team": live_match["home"]},
    )
    assert response.status_code == 400
    assert "kind" in response.json()


def test_conflict_wins_over_validation(api, new_match, team_ids):
    """Стан матчу перевіряється ПЕРЕД валідацією тіла: 409, а не 400."""
    match = new_match()
    foreign = next(
        team_id for team_id in team_ids if team_id not in (match["home"], match["away"])
    )
    response = api.post(
        f"/api/v1/matches/{match['id']}/events/",
        json={"kind": "penalty", "minute": 999, "player": "", "team": foreign},
    )
    assert response.status_code == 409, (
        "Тіло тут погане з трьох причин, але матч навіть не триває. "
        "Порядок перевірок із контракту: 404 → 409 → 400."
    )
