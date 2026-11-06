# ПР №2.16.3 — API табло турніру за контрактом openapi.yaml

Реалізовано `serializers.py`, `views.py`, `urls.py` для застосунку `scoreboard`.
Моделі не змінювались.

## Запуск (готовий проєкт, свого проєкту не потрібно)
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations scoreboard
python manage.py migrate
python manage.py seed_tournament
python manage.py runserver
```
В іншому терміналі (з активованим venv):
```bash
cd tests && pip install -r requirements.txt && pytest     # очікується 38 passed
```

## Розбіжності з контрактом у першій версії

Три місця, де перша версія не відповідала `openapi.yaml`, і що саме я в них неправильно припустив:

1. **Переходи стану віддавали 400 замість 409.** Я вважав, що правило «з finished не можна в live» — це
   валідація, тому клав його в `validate()` серіалізатора. Але `ValidationError` завжди дає 400, а контракт
   вимагає 409: дані правильні, неправильний момент. Тепер перевірка в `partial_update` в'юхи.
2. **У відповіді 201 не було `Location`.** Я вважав, що DRF ставить його сам. Він робить це лише тоді,
   коли в даних серіалізатора є поле `url`. Тепер заголовок додається в `create()` через `reverse("match-detail", ...)`.
3. **Помилка валідації замість конфлікту при події в матчі, що не триває (400 замість 409).** Я вважав, що
   порядок перевірок неістотний, і спершу валідував тіло. Контракт вимагає 404 → 409 → 400, тому стан матчу
   перевіряється до `is_valid()`.

## Колекція
`collection/` — експорт із Postman/Insomnium, імпортований з `openapi.yaml`.