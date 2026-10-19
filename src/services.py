"""Сервисы анализа транзакций: поиск, телефоны, переводы, кешбэк."""

import re
from collections import Counter
from typing import Any

import pandas as pd

from src.utils import logger

# ----- Константы -----
CASHBACK_PERCENT = 0.01  # 1% кешбэка
TOP_CASHBACK_CATEGORIES = 3
TRANSFERS_CATEGORY = "Переводы"

# Регулярка для телефонов: +7 (900) 000-00-00, 89000000000, +7 921 11-22-33 и т.п.
PHONE_PATTERN = re.compile(
    r"(\+7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{2,3}[\s\-]*\d{2}[\s\-]*\d{2}",
    re.IGNORECASE,
)

# Регулярка для перевода физлицу: имя + первая буква фамилии с точкой ("Валерий А.")
INDIVIDUAL_PATTERN = re.compile(r"[А-ЯЁA-Z][а-яёa-z]+\s+[А-ЯЁA-Z]\.")


def _row_to_dict(row: pd.Series) -> dict[str, Any]:
    """Преобразует строку DataFrame в JSON-совместимый словарь."""
    return {
        "date": row["date"].strftime("%d.%m.%Y"),
        "amount": float(row["amount"]),
        "category": row["category"],
        "description": row["description"],
    }


def search_transactions(transactions: pd.DataFrame, query: str) -> list[dict[str, Any]]:
    """
    Ищет транзакции по подстроке в description или category (без учёта регистра).

    :param transactions: датафрейм транзакций
    :param query: строка поиска
    :return: список JSON-совместимых словарей
    """
    if not query:
        return []

    q = query.lower()
    mask = transactions["description"].astype(str).str.lower().str.contains(
        q, regex=False
    ) | transactions["category"].astype(str).str.lower().str.contains(q, regex=False)
    result = transactions.loc[mask]

    logger.info("Поиск '%s': найдено %d транзакций", query, len(result))
    return [_row_to_dict(row) for _, row in result.iterrows()]


def search_phone_numbers(transactions: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Ищет транзакции, в описании которых есть мобильный номер.

    Поддерживает форматы +7 (900) 000-00-00 и 89000000000.

    :param transactions: датафрейм транзакций
    :return: список JSON-совместимых словарей
    """
    mask = (
        transactions["description"]
        .astype(str)
        .apply(lambda d: bool(PHONE_PATTERN.search(d)))
    )
    result = transactions.loc[mask]

    logger.info("Найдено транзакций с телефоном: %d", len(result))
    return [_row_to_dict(row) for _, row in result.iterrows()]


def search_transfers_to_individuals(
    transactions: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    Ищет переводы физлицам: category == 'Переводы' и в описании имя + первая буква фамилии с точкой.

    :param transactions: датафрейм транзакций
    :return: список JSON-совместимых словарей
    """
    mask = (transactions["category"] == TRANSFERS_CATEGORY) & transactions[
        "description"
    ].astype(str).apply(lambda d: bool(INDIVIDUAL_PATTERN.search(d)))
    result = transactions.loc[mask]

    logger.info("Найдено переводов физлицам: %d", len(result))
    return [_row_to_dict(row) for _, row in result.iterrows()]


def profitable_cashback_categories(
    transactions: pd.DataFrame, year: int, month: int
) -> dict[str, int]:
    """
    Анализ выгодности категорий повышенного кешбэка за указанный месяц года.

    Для каждой категории считает 1% от суммы расходов (по модулю),
    возвращает топ-3 категории по убыванию кешбэка.

    :param transactions: датафрейм транзакций
    :param year: год
    :param month: месяц
    :return: словарь {категория: кешбэк}, округлённый до целых
    """
    mask = (
        (transactions["date"].dt.year == year)
        & (transactions["date"].dt.month == month)
        & (transactions["amount"] < 0)
    )
    expenses = transactions.loc[mask].copy()

    if expenses.empty:
        return {}

    expenses["abs_amount"] = expenses["amount"].abs()
    grouped = expenses.groupby("category")["abs_amount"].sum()

    cashback = {
        cat: int(round(amount * CASHBACK_PERCENT)) for cat, amount in grouped.items()
    }

    top = dict(Counter(cashback).most_common(TOP_CASHBACK_CATEGORIES))

    logger.info(
        "Топ-%d категорий кешбэка за %02d.%d: %s",
        TOP_CASHBACK_CATEGORIES,
        month,
        year,
        top,
    )
    return top
