"""Тесты для src/views.py."""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.views import events_page, get_greeting, main_page


@pytest.mark.parametrize(
    "hour, expected",
    [
        (6, "Доброе утро"),
        (11, "Доброе утро"),
        (12, "Добрый день"),
        (17, "Добрый день"),
        (18, "Добрый вечер"),
        (22, "Добрый вечер"),
        (23, "Доброй ночи"),
        (0, "Доброй ночи"),
        (5, "Доброй ночи"),
    ],
)
def test_get_greeting(hour, expected):
    """Приветствие соответствует временному интервалу."""
    dt = datetime(2021, 12, 31, hour, 0, 0)
    assert get_greeting(dt) == expected


def test_main_page_structure(sample_transactions, sample_settings):
    """Главная: все блоки на месте, топ-5 ровно 5, даты dd.mm.yyyy."""
    with patch("src.views.fetch_currency_rates", return_value=[{"currency": "USD", "rate": 73.21}]):
        with patch("src.views.fetch_stock_prices", return_value=[{"stock": "AAPL", "price": 150.12}]):
            result = main_page("2021-12-31 16:44:00", sample_transactions, sample_settings)

    assert "greeting" in result
    assert "cards" in result
    assert "top_transactions" in result
    assert "currency_rates" in result
    assert "stock_prices" in result

    assert len(result["top_transactions"]) == 5
    for tx in result["top_transactions"]:
        assert set(tx.keys()) == {"date", "amount", "category", "description"}
        datetime.strptime(tx["date"], "%d.%m.%Y")

    amounts = [abs(tx["amount"]) for tx in result["top_transactions"]]
    assert amounts == sorted(amounts, reverse=True)


def test_main_page_cards(sample_transactions, sample_settings):
    """Карты: last_digits, total_spent, cashback = total/100."""
    with patch("src.views.fetch_currency_rates", return_value=[]):
        with patch("src.views.fetch_stock_prices", return_value=[]):
            result = main_page("2021-12-31 16:44:00", sample_transactions, sample_settings)

    for card in result["cards"]:
        assert set(card.keys()) == {"last_digits", "total_spent", "cashback"}
        assert len(card["last_digits"]) <= 4
        assert card["total_spent"] >= 0
        assert card["cashback"] == pytest.approx(card["total_spent"] / 100, rel=1e-2)


@pytest.mark.parametrize("range_type", ["W", "M", "Y", "ALL"])
def test_events_page_structure(sample_transactions, sample_settings, range_type):
    """События: все блоки на месте, суммы целые, топ-7 + Остальное."""
    with patch("src.views.fetch_currency_rates", return_value=[]):
        with patch("src.views.fetch_stock_prices", return_value=[]):
            result = events_page("2021-12-31 16:44:00", sample_transactions, sample_settings, range_type)

    assert "expenses" in result
    assert "income" in result
    assert "currency_rates" in result
    assert "stock_prices" in result

    expenses = result["expenses"]
    assert set(expenses.keys()) == {"total_amount", "main", "transfers_and_cash"}
    assert isinstance(expenses["total_amount"], int)
    assert len(expenses["main"]) <= 8
    for item in expenses["main"]:
        assert isinstance(item["amount"], int)
    for item in expenses["transfers_and_cash"]:
        assert item["category"] in ("Переводы", "Наличные")

    income = result["income"]
    assert set(income.keys()) == {"total_amount", "main"}
    assert isinstance(income["total_amount"], int)


def test_events_page_invalid_range(sample_transactions, sample_settings):
    """Неизвестный диапазон — ValueError."""
    with pytest.raises(ValueError):
        events_page("2021-12-31 16:44:00", sample_transactions, sample_settings, "X")