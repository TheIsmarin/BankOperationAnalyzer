"""Отчёты по тратам с декоратором записи в файл."""

import json
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, Union

import pandas as pd

from src.utils import logger

# ----- Константы -----
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports_output"
MONTHS_BACK = 3
EXPENSE_COLUMNS = ["date", "amount", "category", "description"]


def _default_filename(func_name: str) -> str:
    """Имя файла по умолчанию: report_<func>_<timestamp>.json."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"report_{func_name}_{timestamp}.json"


def _save_report(df: pd.DataFrame, filename: str) -> None:
    """Сохраняет DataFrame в JSON-файл (список записей)."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / filename

    # Даты приводим к строкам dd.mm.yyyy, чтобы JSON был читаемым
    data = df.copy()
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"]).dt.strftime("%d.%m.%Y")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    logger.info("Отчёт сохранён: %s", path)


def report_decorator(
    func: Optional[Callable[..., pd.DataFrame]] = None,
    *,
    filename: Optional[str] = None,
) -> Union[
    Callable[..., pd.DataFrame],
    Callable[[Callable[..., pd.DataFrame]], Callable[..., pd.DataFrame]],
]:
    """
    Декоратор для функций-отчётов: записывает результат (DataFrame) в JSON-файл.

    Использование:
        @report_decorator                      # имя файла по умолчанию
        @report_decorator(filename="out.json") # своё имя файла
    """

    def decorator(
        inner_func: Callable[..., pd.DataFrame]
    ) -> Callable[..., pd.DataFrame]:
        @wraps(inner_func)
        def wrapper(*args: Any, **kwargs: Any) -> pd.DataFrame:
            result = inner_func(*args, **kwargs)
            target_name = filename or _default_filename(inner_func.__name__)
            try:
                _save_report(result, target_name)
            except Exception as e:  # noqa: BLE001
                logger.error("Не удалось сохранить отчёт %s: %s", target_name, e)
            return result

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


@report_decorator
def spending_by_category(
    transactions: pd.DataFrame,
    category: str,
    date: Optional[Union[str, datetime]] = None,
) -> pd.DataFrame:
    """
    Траты по категории за последние 3 месяца от указанной даты.

    :param transactions: датафрейм транзакций
    :param category: название категории
    :param date: дата (строка YYYY-MM-DD или datetime); по умолчанию — текущая
    :return: DataFrame с колонками date, amount, category, description
    """
    end_dt = pd.to_datetime(date) if date is not None else pd.Timestamp(datetime.now())
    start_dt = end_dt - pd.DateOffset(months=MONTHS_BACK)

    mask = (
        (transactions["date"] >= start_dt)
        & (transactions["date"] <= end_dt)
        & (transactions["category"] == category)
        & (transactions["amount"] < 0)
    )
    result = transactions.loc[mask, EXPENSE_COLUMNS].copy()

    logger.info(
        "Траты по '%s' с %s по %s: %d строк",
        category,
        start_dt.date(),
        end_dt.date(),
        len(result),
    )
    return result
