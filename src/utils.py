"""Утилиты: чтение данных, настроек, API-запросы и логирование."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения из .env (ключ API_KEY)
load_dotenv()

# ----- Константы -----
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OPERATIONS_FILE = DATA_DIR / "operations.xlsx"
SETTINGS_FILE = Path(__file__).resolve().parent.parent / "user_settings.json"

# Соответствие русских колонок Excel английским именам
COLUMN_MAPPING = {
    "Дата операции": "date",
    "Номер карты": "card",
    "Сумма платежа": "amount",
    "Кэшбэк": "cashback",
    "Категория": "category",
    "Описание": "description",
    "Статус": "status",
}

KEEP_COLUMNS = ["date", "card", "amount", "cashback", "category", "description", "status"]

# Базовые URL APILayer
CURRENCY_URL = "https://api.apilayer.com/exchangerates_data/latest"
STOCK_URL = "https://api.apilayer.com/stock_data/price"


# ----- Логирование -----
def setup_logging(name: str = "app", level: int = logging.INFO) -> logging.Logger:
    """Настраивает и возвращает логгер с единым форматом."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging(__name__)


# ----- Чтение данных -----
def load_transactions(file_path: Optional[Path] = None) -> pd.DataFrame:
    """..."""
    path = file_path or OPERATIONS_FILE

    try:
        df = pd.read_excel(path, sheet_name=0)
    except FileNotFoundError:
        logger.error("Файл с транзакциями не найден: %s", path)
        raise
    except Exception as e:
        logger.error("Ошибка чтения Excel: %s", e)
        raise

    # Переименовываем только те колонки, которые есть
    df = df.rename(columns={k: v for k, v in COLUMN_MAPPING.items() if k in df.columns})

    # Оставляем только нужные колонки (7 штук)
    df = df[[c for c in KEEP_COLUMNS if c in df.columns]].copy()

    # Приводим дату к datetime с явным форматом dd.mm.yyyy HH:MM:SS
    if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y %H:%M:%S", errors="coerce")

    # Оставляем только успешные операции
    if "status" in df.columns:
        df = df[df["status"] == "OK"].copy()

    # Чистим номер карты: "*7197" -> "7197", пустые -> None
    if "card" in df.columns:
        df["card"] = df["card"].astype(str).str.replace(r"\D", "", regex=True)
        df["card"] = df["card"].replace("", None)

    logger.info("Загружено %d транзакций из %s", len(df), path)
    return df


def load_user_settings(file_path: Optional[Path] = None) -> dict[str, Any]:
    """
    Загружает user_settings.json со списками валют и акций.

    :param file_path: путь к файлу (по умолчанию user_settings.json в корне)
    :return: словарь с ключами user_currencies и user_stocks
    """
    path = file_path or SETTINGS_FILE

    with open(path, "r", encoding="utf-8") as f:
        settings = json.load(f)

    logger.info("Загружены настройки: валюты=%s, акции=%s",
                settings.get("user_currencies"),
                settings.get("user_stocks"))
    return settings


# ----- Парсинг даты -----
def parse_datetime(date_str: str) -> datetime:
    """
    Парсит строку вида 'YYYY-MM-DD HH:MM:SS' в datetime.

    :param date_str: строка с датой и временем
    :return: объект datetime
    """
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")


# ----- API-запросы -----
def _get_api_key() -> Optional[str]:
    """Возвращает API_KEY из .env или None, если ключ не задан."""
    key = os.getenv("API_KEY")
    if not key:
        logger.warning("API_KEY не найден в .env — запросы к API будут пропущены")
    return key


def fetch_currency_rates(currencies: list[str]) -> list[dict[str, Any]]:
    """
    Получает курсы валют к RUB через APILayer.

    :param currencies: список кодов валют (например, ['USD', 'EUR'])
    :return: список словарей [{'currency': 'USD', 'rate': 73.21}, ...]
             при ошибке — пустой список
    """
    api_key = _get_api_key()
    if not api_key or not currencies:
        return []

    headers = {"apikey": api_key}
    params = {"base": "RUB", "symbols": ",".join(currencies)}
    result: list[dict[str, Any]] = []

    try:
        response = requests.get(CURRENCY_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        rates = data.get("rates", {})
        for currency in currencies:
            rate = rates.get(currency)
            if rate is not None:
                result.append({"currency": currency, "rate": float(rate)})

    except requests.exceptions.RequestException as e:
        logger.error("Ошибка запроса курсов валют: %s", e)
    except (ValueError, TypeError) as e:
        logger.error("Ошибка обработки ответа курсов валют: %s", e)

    logger.info("Получены курсы валют: %s", result)
    return result


def fetch_stock_prices(stocks: list[str]) -> list[dict[str, Any]]:
    """
    Получает цены акций S&P 500 через APILayer.

    :param stocks: список тикеров (например, ['AAPL', 'AMZN'])
    :return: список словарей [{'stock': 'AAPL', 'price': 150.12}, ...]
             при ошибке — пустой список
    """
    api_key = _get_api_key()
    if not api_key or not stocks:
        return []

    headers = {"apikey": api_key}
    result: list[dict[str, Any]] = []

    for stock in stocks:
        try:
            response = requests.get(
                STOCK_URL,
                headers=headers,
                params={"symbol": stock},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            price = data.get("price")

            if price is not None:
                result.append({"stock": stock, "price": float(price)})

        except requests.exceptions.RequestException as e:
            logger.error("Ошибка запроса цены акции %s: %s", stock, e)
        except (ValueError, TypeError) as e:
            logger.error("Ошибка обработки цены акции %s: %s", stock, e)

    logger.info("Получены цены акций: %s", result)
    return result