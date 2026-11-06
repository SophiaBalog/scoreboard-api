"""Табло: голий масив матчів, що тривають."""

MATCH_KEYS = {
    "id", "tournament", "home", "away", "home_name", "away_name",
    "starts_at", "status", "score",
}


def test_scoreboard_is_a_bare_array(api):
    response = api.get("/api/v1/scoreboard/")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list), (
        "Табло — один зведений звіт, а не колекція: конверт пагінації тут зайвий."
    )


def test_scoreboard_contains_only_live_matches(api):
    body = api.get("/api/v1/scoreboard/").json()
    assert body, "Сидований турнір містить матч у стані live — табло не може бути порожнім."
    assert {match["status"] for match in body} == {"live"}
    assert set(body[0]) == MATCH_KEYS


def test_scoreboard_is_ordered_by_start_time(api):
    body = api.get("/api/v1/scoreboard/").json()
    starts = [match["starts_at"] for match in body]
    assert starts == sorted(starts)


def test_started_match_appears_on_scoreboard(api, live_match):
    api.post(
        f"/api/v1/matches/{live_match['id']}/events/",
        json={"kind": "goal", "minute": 7, "player": "Мельник", "team": live_match["away"]},
    )
    board = api.get("/api/v1/scoreboard/").json()
    mine = [match for match in board if match["id"] == live_match["id"]]
    assert mine, "Матч, переведений у live, має з'явитись на табло."
    assert mine[0].get("score") == {"home": 0, "away": 1}, (
        "Табло віддає ті самі поля матчу, що й /api/v1/matches/{id}/, разом із score."
    )


def test_finished_match_leaves_scoreboard(api, live_match):
    api.patch(f"/api/v1/matches/{live_match['id']}/", json={"status": "finished"})
    board = api.get("/api/v1/scoreboard/").json()
    assert all(match["id"] != live_match["id"] for match in board)
