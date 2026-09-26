"""Точка входа приложения «ЗОНД: ECTS».

Запуск:

    python -m zond.ects
"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from zond.app.app import ZondApp
from zond.utils.logging_setup import configure_logging

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"


async def main(page: ft.Page) -> None:
    """Собрать приложение и показать стартовый экран.

    Асинхронная, потому что до первого экрана нужно определить каталог данных:
    на мобильных платформах он отличается от настольного.
    """

    configure_logging()

    app = ZondApp(page)
    await app.prepare()
    app.start()


def run() -> None:
    """Запустить настольное приложение (точка входа консольной команды)."""

    ft.run(main, assets_dir=str(ASSETS_DIR))


if __name__ == "__main__":
    run()
