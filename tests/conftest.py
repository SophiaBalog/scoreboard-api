"""Спільна обв'язка black-box тестів ПР №2.16.3.

Тести нічого не знають про проєкт студента: ні моделей, ні settings, ні
назв в'юх. Є лише базова адреса і HTTP. Тому той самий набір перевіряє
будь-яку реалізацію контракту.

    pytest                                   # http://127.0.0.1:8000
    pytest --base-url http://localhost:8001
    API_BASE_URL=http://localhost:8001 pytest
"""

import os

import pytest
import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
SEED_SLUG = "kubok-it21"
TIMEOUT = 5

# Матчі, які створюють тести, завжди починаються пізніше за сидовані —
# так сидовані лишаються на першій сторінці списку (ordering за starts_at).
FUTURE = "2030-01-01T18:00:00Z"


def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        action="store",
        default=None,
        help="Базова адреса API, напр. http://127.0.0.1:8000",
    )


class Api:
    """Тонка обгортка над requests: шлях замість повної адреси."""

    def __init__(self, base):
        self.base = base
        self.session = requests.Session()

    def url(self, path):
        return f"{self.base}{path}"

    def _call(self, method, path, **kwargs):
        kwargs.setdefault("timeout", TIMEOUT)
        return self.session.request(method, self.url(path), **kwargs)

    def get(self, path, **kwargs):
        return self._call("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self._call("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self._call("PUT", path, **kwargs)

    def patch(self, path, **kwargs):
        return self._call("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        return self._call("DELETE", path, **kwargs)


@pytest.fixture(scope="session")
def base_url(request):
    url = (
        request.config.getoption("--base-url")
        or os.environ.get("API_BASE_URL")
        or DEFAULT_BASE_URL
    )
    return url.rstrip("/")


@pytest.fixture(scope="session")
def api(base_url):
    return Api(base_url)


def items(body):
    """Елементи списку — байдуже, прийшли вони в конверті чи голим масивом.

    Обв'язка навмисно терпима до відсутності пагінації: про це має сказати
    окремий тест про конверт, а не глобальна перевірка, яка обриває прогін.
    """
    if isinstance(body, dict) and "results" in body:
        return body["results"]
    return body


@pytest.fixture(scope="session")
def tournament(api, base_url):
    """Сидований турнір, знайдений у списку. Без нього тестувати нічого.

    Турнір беремо саме зі списку, а не з адреси за слагом: якщо `lookup_field`
    ще не налаштований, має впасти один тест про слаг, а не весь прогін.
    """
    try:
        response = api.get("/api/v1/tournaments/")
    except requests.exceptions.ConnectionError:
        pytest.exit(
            f"Сервер на {base_url} не відповідає. Запустіть python manage.py runserver.",
            returncode=1,
        )
    if response.status_code != 200:
        pytest.exit(
            f"GET /api/v1/tournaments/ віддав {response.status_code}, очікувався 200. "
            "Контракт не виконується на найпростішому запиті.",
            returncode=1,
        )
    for tournament in items(response.json()):
        if tournament.get("slug") == SEED_SLUG:
            return tournament
    pytest.exit(
        f"Турніру {SEED_SLUG} немає у списку. Запустіть python manage.py seed_tournament.",
        returncode=1,
    )


@pytest.fixture(scope="session")
def seeded_matches(api, tournament):
    """Матчі сидованого турніру — по одному в кожному стані."""
    response = api.get("/api/v1/matches/")
    assert response.status_code == 200, response.text
    matches = [m for m in items(response.json()) if m.get("tournament") == tournament["id"]]
    if len(matches) < 3:
        pytest.exit(
            "На першій сторінці /api/v1/matches/ менше трьох сидованих матчів. "
            "Перезапустіть python manage.py seed_tournament --flush.",
            returncode=1,
        )
    return matches


@pytest.fixture(scope="session")
def finished_match(seeded_matches):
    for match in seeded_matches:
        if match["status"] == "finished":
            return match
    pytest.skip("Серед сидованих матчів немає завершеного.")


@pytest.fixture(scope="session")
def team_ids(seeded_matches):
    """Щонайменше три різні команди: дві для матчу і одна «чужа»."""
    ids = []
    for match in seeded_matches:
        for key in ("home", "away"):
            if match[key] not in ids:
                ids.append(match[key])
    if len(ids) < 3:
        pytest.skip("Для перевірки «чужої команди» потрібні щонайменше три команди.")
    return ids


@pytest.fixture
def new_match(api, tournament, team_ids):
    """Фабрика запланованих матчів. Прибирає за собою те, що ще можна видалити."""
    created = []

    def make(**overrides):
        payload = {
            "tournament": tournament["id"],
            "home": team_ids[0],
            "away": team_ids[1],
            "starts_at": FUTURE,
        }
        payload.update(overrides)
        response = api.post("/api/v1/matches/", json=payload)
        assert response.status_code == 201, (
            f"POST /api/v1/matches/ віддав {response.status_code}: {response.text[:300]}"
        )
        match = response.json()
        created.append(match["id"])
        return match

    yield make

    # Матч, переведений у live чи finished, видалити не можна за контрактом —
    # 409 тут очікуваний і не є помилкою прибирання.
    for match_id in created:
        api.delete(f"/api/v1/matches/{match_id}/")


@pytest.fixture
def live_match(api, new_match):
    """Матч у стані live — єдиний, до якого контракт дозволяє додавати події."""
    match = new_match()
    response = api.patch(f"/api/v1/matches/{match['id']}/", json={"status": "live"})
    assert response.status_code == 200, (
        f"PATCH scheduled → live віддав {response.status_code}: {response.text[:300]}"
    )
    return response.json()
