"""Тесты для src/services.py."""

import pytest

from src.services import (
    profitable_cashback_categories,
    search_phone_numbers,
    search_transactions,
    search_transfers_to_individuals,
)


def test_search_transactions_case_insensitive(sample_transactions):
    """Поиск нечувствителен к регистру."""
    result_lower = search_transactions(sample_transactions, "мтс")
    result_upper = search_transactions(sample_transactions, "МТС")
    assert len(result_lower) == len(result_upper)
    assert len(result_lower) > 0


def test_search_transactions_substring(sample_transactions):
    """Поиск по подстроке в описании или категории."""
    result = search_transactions(sample_transactions, "колхоз")
    assert all(
        "колхоз" in tx["description"].lower() or "колхоз" in tx["category"].lower()
        for tx in result
    )


def test_search_transactions_empty_query(sample_transactions):
    """Пустой запрос — пустой список."""
    assert search_transactions(sample_transactions, "") == []


def test_search_phone_numbers(sample_transactions):
    """Находит телефоны в обоих форматах."""
    result = search_phone_numbers(sample_transactions)
    assert len(result) >= 1
    assert any("+7 995 555-55-55" in tx["description"] for tx in result)


@pytest.mark.parametrize(
    "description, should_find",
    [
        ("+7 (900) 000-00-00", True),
        ("89000000000", True),
        ("+7 921 11-22-33", True),
        ("8 900 000 00 00", True),
        ("без номера", False),
    ],
)
def test_search_phone_numbers_formats(description, should_find):
    """Поддерживаются разные форматы номеров."""
    from datetime import datetime

    import pandas as pd

    df = pd.DataFrame(
        {
            "date": [datetime(2021, 12, 1)],
            "card": ["7197"],
            "amount": [-100.0],
            "cashback": [None],
            "category": ["Связь"],
            "description": [description],
            "status": ["OK"],
        }
    )
    result = search_phone_numbers(df)
    assert (len(result) == 1) == should_find


def test_search_transfers_to_individuals(sample_transactions):
    """Переводы физлицам: category == 'Переводы' и имя + первая буква фамилии."""
    result = search_transfers_to_individuals(sample_transactions)
    assert len(result) > 0
    for tx in result:
        assert tx["category"] == "Переводы"


def test_profitable_cashback_categories(sample_transactions):
    """Не менее 3 категорий, суммы целые."""
    result = profitable_cashback_categories(sample_transactions, 2021, 12)
    assert len(result) >= 1
    for cat, amount in result.items():
        assert isinstance(amount, int)


def test_profitable_cashback_categories_empty(sample_transactions):
    """Нет трат за месяц — пустой словарь."""
    result = profitable_cashback_categories(sample_transactions, 2000, 1)
    assert result == {}
