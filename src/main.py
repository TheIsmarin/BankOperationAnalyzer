"""Точка входа: демонстрация Главной и Событий на реальных данных."""

import json

from src.utils import load_transactions, load_user_settings, logger
from src.views import events_page, main_page

# ----- Константы -----
DEMO_DATE = "2021-12-31 16:44:00"
DEMO_RANGES = ["W", "M", "Y", "ALL"]


def _print_json(title: str, data: dict) -> None:
    """Печатает JSON с заголовком."""
    print(f"\n===== {title} =====")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    """Загружает данные, формирует ответы Главной и Событий, печатает JSON."""
    try:
        transactions = load_transactions()
        settings = load_user_settings()
    except Exception as e:  # noqa: BLE001
        logger.error("Не удалось загрузить данные: %s", e)
        return

    # Главная страница
    try:
        _print_json("ГЛАВНАЯ", main_page(DEMO_DATE, transactions, settings))
    except Exception as e:  # noqa: BLE001
        logger.error("Ошибка формирования Главной: %s", e)

    # События для всех диапазонов
    for range_type in DEMO_RANGES:
        try:
            _print_json(
                f"СОБЫТИЯ (диапазон {range_type})",
                events_page(DEMO_DATE, transactions, settings, range_type),
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Ошибка формирования Событий (%s): %s", range_type, e)


if __name__ == "__main__":
    main()