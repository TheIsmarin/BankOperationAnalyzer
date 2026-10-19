## Структура проекта

```
.
├── src/
│   ├── __init__.py
│   ├── utils.py          # чтение Excel, настроек, API-запросы, логирование
│   ├── views.py          # Главная и События (JSON-ответы)
│   ├── services.py       # поиск, телефоны, переводы, кешбэк
│   ├── reports.py        # отчёты + декоратор записи в файл
│   └── main.py           # демонстрационный запуск
├── tests/
│   ├── conftest.py       # фикстуры
│   ├── test_utils.py
│   ├── test_views.py
│   ├── test_services.py
│   └── test_reports.py
├── data/
│   └── operations.xlsx   # исходные транзакции
├── user_settings.json    # валюты и акции для отображения
├── .env_template         # шаблон переменных окружения
├── .flake8
├── pyproject.toml
└── README.md
```

## Установка

1. Установите [Poetry](https://python-poetry.org/docs/#installation).
2. Клонируйте репозиторий:

```bash
git clone https://github.com/TheIsmarin/BankOperationAnalyzer.git
cd BankOperationAnalyzer
```

3. Установите зависимости:

```bash
poetry install
```

4. Создайте `.env` из шаблона и укажите ключ APILayer:

   ```bash
   cp .env_template .env
   ```

   Внутри:

   ```
   API_KEY=ваш_ключ_apilayer
   ```

5. Положите файл `operations.xlsx` в папку `data/` (если его нет в репозитории).

## Запуск

```bash
poetry run python -m src.main
```

В консоль выведется JSON для Главной страницы и для Событий (диапазоны W, M, Y, ALL).

## Тесты

```bash
poetry run pytest -v
```

42 теста: приветствие по времени, карты, топ-5, структура JSON, диапазоны, топ-7 + Остальное, поиск, телефоны, переводы физлицам, кешбэк, декоратор отчётов. API в тестах подменяется через `Mock`/`patch` — реальный ключ не расходуется.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `API_KEY` | Ключ APILayer для курсов валют и цен акций |

## Примечание об API

Для реального получения курсов валют и цен акций нужен действующий ключ APILayer с подпиской на соответствующие эндпоинты. Без ключа (или при недоступности API) блоки `currency_rates` и `stock_prices` возвращаются пустыми, а ошибки логируются — программа не падает.

## Настройки

`user_settings.json`:

```json
{
  "user_currencies": ["USD", "EUR"],
  "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
}
```

## Линтеры

```bash
poetry run flake8 src tests
poetry run black --check src tests
poetry run isort --check src tests
poetry run mypy src
```

## Лицензия

Учебный проект.