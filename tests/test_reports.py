"""Тесты для src/reports.py."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.reports import report_decorator, spending_by_category


def test_report_decorator_default_filename(tmp_path, monkeypatch):
    """Декоратор без параметра пишет файл в reports_output."""
    import src.reports as reports_module
    monkeypatch.setattr(reports_module, "REPORTS_DIR", tmp_path)

    @report_decorator
    def dummy_report(transactions: pd.DataFrame) -> pd.DataFrame:
        return transactions.head(1)

    df = pd.DataFrame({"date": [datetime(2021, 12, 1)], "amount": [-100.0]})
    result = dummy_report(df)

    assert isinstance(result, pd.DataFrame)
    files = list(tmp_path.glob("report_dummy_report_*.json"))
    assert len(files) == 1


def test_report_decorator_with_filename(tmp_path, monkeypatch):
    """Декоратор с параметром пишет файл с указанным именем."""
    import src.reports as reports_module
    monkeypatch.setattr(reports_module, "REPORTS_DIR", tmp_path)

    @report_decorator(filename="custom.json")
    def dummy_report(transactions: pd.DataFrame) -> pd.DataFrame:
        return transactions.head(1)

    df = pd.DataFrame({"date": [datetime(2021, 12, 1)], "amount": [-100.0]})
    dummy_report(df)

    assert (tmp_path / "custom.json").exists()


def test_spending_by_category(sample_transactions):
    """Траты по категории за 3 месяца от даты."""
    result = spending_by_category(sample_transactions, "Супермаркеты", "2021-12-31")
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["date", "amount", "category", "description"]
    assert (result["category"] == "Супермаркеты").all()
    assert (result["amount"] < 0).all()


def test_spending_by_category_empty(sample_transactions):
    """Нет трат — пустой DataFrame с колонками."""
    result = spending_by_category(sample_transactions, "Несуществующая", "2021-12-31")
    assert result.empty
    assert list(result.columns) == ["date", "amount", "category", "description"]


def test_spending_by_category_without_date(sample_transactions):
    """Без даты — берётся текущая (данные 2021 — пусто)."""
    result = spending_by_category(sample_transactions, "Супермаркеты")
    assert isinstance(result, pd.DataFrame)