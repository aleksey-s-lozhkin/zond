"""Настройка логирования.

Отладочный вывод идёт через :mod:`logging`, а не ``print``: уровень
управляется переменной окружения ``ZOND_LOG_LEVEL``, а сообщения можно
направить в файл или в консоль.
"""

from __future__ import annotations

import logging
import os

DEFAULT_LEVEL = "WARNING"

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure_logging(level: str | None = None) -> None:
    """Настроить корневой логгер приложения.

    Args:
        level: имя уровня (``DEBUG``, ``INFO``, …). По умолчанию берётся из
            переменной окружения ``ZOND_LOG_LEVEL``, иначе ``WARNING``.
    """

    resolved = (level or os.environ.get("ZOND_LOG_LEVEL") or DEFAULT_LEVEL).upper()
    logging.basicConfig(level=getattr(logging, resolved, logging.WARNING), format=_FORMAT)


def get_logger(name: str) -> logging.Logger:
    """Логгер с общим префиксом приложения."""

    return logging.getLogger(f"zond.{name}" if not name.startswith("zond") else name)
