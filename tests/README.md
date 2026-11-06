# Тести ПР №2.16.3

Black-box набір: тести не імпортують ваш проєкт і нічого не знають про назви
моделей, в'юх і додатків. Є лише базова адреса і HTTP — тому той самий набір
перевіряє будь-яку реалізацію контракту `openapi.yaml`.

## Запуск

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# в іншому терміналі має бути піднятий сервер зі сидованими даними:
#   python manage.py seed_tournament
#   python manage.py runserver

pytest                                    # http://127.0.0.1:8000
pytest --base-url http://localhost:8001   # інший порт
pytest test_events.py -k conflict         # одна група перевірок
```

Якщо сервер не піднятий або сид не виконано — прогін зупиняється одним
зрозумілим рядком, а не сотнею `ConnectionError`.

## Як читати падіння

Кожне `assert` має пояснення українською: воно каже не «очікувалось 409»,
а **чому** саме 409. Читайте повідомлення, а не лише `assert 400 == 409`.

Рекомендований порядок роботи:

1. `pytest test_tournaments.py` — ReadOnlyModelViewSet, `lookup_field`, пагінація
2. `pytest test_matches.py -k shape or score` — серіалізатор і рахунок
3. `pytest test_matches.py` — створення, `Location`, переходи стану
4. `pytest test_events.py` — `@action` і порядок перевірок
5. `pytest test_scoreboard.py` — `@api_view`
6. `pytest` — усе разом

## Чому тести не перевіряють абсолютних кількостей

Контракт забороняє видаляти матч, який уже почався, тому тести не можуть
прибрати за собою все, що створили. Жодна перевірка не спирається на
загальну кількість матчів — лише на власні створені об'єкти і на сидований
турнір. Для чистого стану: `python manage.py seed_tournament --flush`.
