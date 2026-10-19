"""Слой представления: JSON-ответы для Главной и Событий."""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from src.utils import (
    fetch_currency_rates,
    fetch_stock_prices,
    logger,
    parse_datetime,
)

# ----- Константы -----
TOP_TRANSACTIONS_COUNT = 5
TOP_CATEGORIES_COUNT = 7
TRANSFERS_CATEGORY = "Переводы"
CASH_CATEGORY = "Наличные"
OTHER_CATEGORY = "Остальное"


def get_greeting(dt: datetime) -> str:
    """Возвращает приветствие в зависимости от часа."""
    hour = dt.hour
    if 6 <= hour <= 11:
        return "Доброе утро"
    if 12 <= hour <= 17:
        return "Добрый день"
    if 18 <= hour <= 22:
        return "Добрый вечер"
    return "Доброй ночи"


def _filter_by_range(
    df: pd.DataFrame, end_dt: datetime, range_type: str
) -> pd.DataFrame:
    """Фильтрует транзакции по диапазону относительно end_dt."""
    if range_type == "W":
        start_dt = end_dt - timedelta(days=end_dt.weekday())
    elif range_type == "M":
        start_dt = end_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif range_type == "Y":
        start_dt = end_dt.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    elif range_type == "ALL":
        start_dt = df["date"].min() if not df.empty else end_dt
    else:
        raise ValueError(f"Неизвестный диапазон: {range_type}")

    mask = (df["date"] >= start_dt) & (df["date"] <= end_dt)
    return df.loc[mask].copy()


def _cards_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Суммирует расходы и кешбэк по каждой карте."""
    expenses = df[(df["amount"] < 0) & (df["card"].notna())]
    if expenses.empty:
        return []

    result: list[dict[str, Any]] = []
    for card, group in expenses.groupby("card"):
        total_spent = round(abs(group["amount"].sum()), 2)
        cashback = round(total_spent / 100, 2)
        result.append(
            {
                "last_digits": str(card)[-4:],
                "total_spent": total_spent,
                "cashback": cashback,
            }
        )
    return result


def _top_transactions(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Возвращает топ-5 транзакций по убыванию суммы."""
    if df.empty:
        return []

    top = df.reindex(df["amount"].abs().sort_values(ascending=False).index)
    top = top.head(TOP_TRANSACTIONS_COUNT)

    result: list[dict[str, Any]] = []
    for _, row in top.iterrows():
        result.append(
            {
                "date": row["date"].strftime("%d.%m.%Y"),
                "amount": float(row["amount"]),
                "category": row["category"],
                "description": row["description"],
            }
        )
    return result


def _group_expenses(df: pd.DataFrame) -> dict[str, Any]:
    """Группирует расходы: топ-7 категорий + Остальное, переводы/наличные отдельно."""
    expenses = df[df["amount"] < 0].copy()
    if expenses.empty:
        return {"total_amount": 0, "main": [], "transfers_and_cash": []}

    expenses["abs_amount"] = expenses["amount"].abs()

    transfers = expenses[expenses["category"].isin([TRANSFERS_CATEGORY, CASH_CATEGORY])]
    main_df = expenses[~expenses["category"].isin([TRANSFERS_CATEGORY, CASH_CATEGORY])]

    grouped = main_df.groupby("category")["abs_amount"].sum().sort_values(ascending=False)

    main_list: list[dict[str, Any]] = []
    if len(grouped) > TOP_CATEGORIES_COUNT:
        top = grouped.head(TOP_CATEGORIES_COUNT)
        other_sum = grouped.iloc[TOP_CATEGORIES_COUNT:].sum()
        for cat, amount in top.items():
            main_list.append({"category": cat, "amount": int(round(amount))})
        main_list.append({"category": OTHER_CATEGORY, "amount": int(round(other_sum))})
    else:
        for cat, amount in grouped.items():
            main_list.append({"category": cat, "amount": int(round(amount))})

    transfers_list: list[dict[str, Any]] = []
    if not transfers.empty:
        t_grouped = (
            transfers.groupby("category")["abs_amount"]
            .sum()
            .sort_values(ascending=False)
        )
        for cat, amount in t_grouped.items():
            transfers_list.append({"category": cat, "amount": int(round(amount))})

    return {
        "total_amount": int(round(expenses["abs_amount"].sum())),
        "main": main_list,
        "transfers_and_cash": transfers_list,
    }


def _group_income(df: pd.DataFrame) -> dict[str, Any]:
    """Группирует поступления по категориям."""
    income = df[df["amount"] > 0]
    if income.empty:
        return {"total_amount": 0, "main": []}

    grouped = income.groupby("category")["amount"].sum().sort_values(ascending=False)
    main_list = [{"category": cat, "amount": int(round(amt))} for cat, amt in grouped.items()]

    return {"total_amount": int(round(income["amount"].sum())), "main": main_list}


def _api_data(
    settings: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Возвращает курсы валют и цены акций из API."""
    currencies = settings.get("user_currencies", [])
    stocks = settings.get("user_stocks", [])
    return fetch_currency_rates(currencies), fetch_stock_prices(stocks)


def main_page(
    date_str: str,
    transactions: pd.DataFrame,
    settings: dict[str, Any],
) -> dict[str, Any]:
    """Формирует JSON-ответ для Главной страницы."""
    dt = parse_datetime(date_str)
    month_start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mask = (transactions["date"] >= month_start) & (transactions["date"] <= dt)
    df = transactions.loc[mask].copy()

    currency_rates, stock_prices = _api_data(settings)

    response = {
        "greeting": get_greeting(dt),
        "cards": _cards_summary(df),
        "top_transactions": _top_transactions(df),
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }
    logger.info("Сформирован ответ Главной страницы на %s", date_str)
    return response


def events_page(
    date_str: str,
    transactions: pd.DataFrame,
    settings: dict[str, Any],
    range_type: str = "M",
) -> dict[str, Any]:
    """Формирует JSON-ответ для страницы Событий."""
    dt = parse_datetime(date_str)
    df = _filter_by_range(transactions, dt, range_type)

    currency_rates, stock_prices = _api_data(settings)

    response = {
        "expenses": _group_expenses(df),
        "income": _group_income(df),
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }
    logger.info("Сформирован ответ Событий на %s (диапазон %s)", date_str, range_type)
    return response