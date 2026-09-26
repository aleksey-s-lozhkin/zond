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


def main(page: ft.Page) -> None:
    """Собрать приложение и показать стартовый экран.

    Функция синхронная намеренно, и интерфейс строится прямо здесь, а не в
    отложенной задаче: асинхронная точка входа требует, чтобы её кто-то
    дождался, а загрузчик собранного приложения этого не делает. Асинхронным
    остаётся только уточнение каталога данных — оно не мешает построению
    интерфейса.
    """

    configure_logging()

    app = ZondApp(page)
    app.start()

    page.run_task(app.prepare)


def run() -> None:
    """Запустить приложение.

    Единая точка входа для консольной команды ``zond-ects`` и для модуля
    ``main``, который импортирует загрузчик собранного приложения.
    """

    ft.run(main, assets_dir=str(ASSETS_DIR))


if __name__ == "__main__":
    run()
