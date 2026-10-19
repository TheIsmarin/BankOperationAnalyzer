"""Тесты для src/utils.py."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests

from src.utils import (
    fetch_currency_rates,
    fetch_stock_prices,
    load_transactions,
    load_user_settings,
    parse_datetime,
    setup_logging,
)


def test_parse_datetime():
    """Парсит строку в datetime."""
    dt = parse_datetime("2021-12-31 16:44:00")
    assert dt == datetime(2021, 12, 31, 16, 44, 0)


def test_parse_datetime_invalid():
    """Неверный формат — ValueError."""
    with pytest.raises(ValueError):
        parse_datetime("не дата")


def test_load_user_settings(tmp_path):
    """Загружает настройки из JSON."""
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        '{"user_currencies": ["USD"], "user_stocks": ["AAPL"]}', encoding="utf-8"
    )

    settings = load_user_settings(settings_file)
    assert settings["user_currencies"] == ["USD"]
    assert settings["user_stocks"] == ["AAPL"]


def test_load_transactions_real_file():
    """Реальный Excel читается, 7 колонок, все OK."""
    df = load_transactions()
    assert list(df.columns) == [
        "date",
        "card",
        "amount",
        "cashback",
        "category",
        "description",
        "status",
    ]
    assert (df["status"] == "OK").all()
    assert len(df) > 0


@patch("src.utils.requests.get")
def test_fetch_currency_rates_success(mock_get):
    """Курсы валют приходят, ключи currency/rate, float > 0."""
    mock_response = Mock()
    mock_response.json.return_value = {"rates": {"USD": 73.21, "EUR": 87.08}}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = fetch_currency_rates(["USD", "EUR"])
    assert len(result) == 2
    assert result[0]["currency"] == "USD"
    assert isinstance(result[0]["rate"], float)
    assert result[0]["rate"] > 0


@patch("src.utils.requests.get")
def test_fetch_currency_rates_error(mock_get):
    """Ошибка API — пустой список, не падает."""
    mock_get.side_effect = requests.exceptions.RequestException("timeout")
    result = fetch_currency_rates(["USD", "EUR"])
    assert result == []


@patch("src.utils.requests.get")
def test_fetch_stock_prices_success(mock_get):
    """Цены акций приходят, ключи stock/price, float > 0."""
    mock_response = Mock()
    mock_response.json.return_value = {"price": 150.12}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = fetch_stock_prices(["AAPL"])
    assert len(result) == 1
    assert result[0]["stock"] == "AAPL"
    assert isinstance(result[0]["price"], float)
    assert result[0]["price"] > 0


@patch("src.utils.requests.get")
def test_fetch_stock_prices_error(mock_get):
    """Ошибка API — пустой список, не падает."""
    mock_get.side_effect = requests.exceptions.RequestException("timeout")
    result = fetch_stock_prices(["AAPL"])
    assert result == []


def test_setup_logging():
    """Логгер настраивается и возвращается."""
    logger = setup_logging("test_logger")
    assert logger.name == "test_logger"
    assert logger.level == 20  # INFO
