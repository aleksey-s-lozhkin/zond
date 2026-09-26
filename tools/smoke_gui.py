"""Дымовой прогон реального GUI.

Запускает приложение в настоящем Flet-сеансе со **скрытым** окном
(``AppView.FLET_APP_HIDDEN``) и проходит полный сценарий: загрузка шаблона,
заполнение формы, завершение, PDF, история, диалоги и нативный выбор даты.

Зачем это нужно, если есть pytest: тесты собирают контролы без страницы и
проверяют логику, но не проверяют реальную монтировку и вызовы ``update()``.
Этот сценарий закрывает именно данный пробел — его стоит запускать локально
на машине с графической сессией.

Запуск:

    python tools/smoke_gui.py

Код возврата 0 — сценарий прошёл, 1 — есть ошибки.

.. note::
   Требуется графическая сессия: Flet поднимает скрытое окно настольного
   клиента. В headless-окружении (CI, контейнер) клиент не стартует, и
   сценарий завершится по сторожевому таймауту с понятным сообщением.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import traceback
from pathlib import Path

import flet as ft

BASE_DIR = Path(__file__).resolve().parents[1]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from zond.app.app import ZondApp  # noqa: E402
from zond.models.field import FieldType  # noqa: E402
from zond.services.json_storage import JsonStorage  # noqa: E402
from zond.ui.components.dialogs import show_confirm, show_error  # noqa: E402
from zond.ui.components.progress import ProgressWidget  # noqa: E402
from zond.ui.screens.finish_screen import FinishScreen  # noqa: E402
from zond.ui.screens.history_screen import HistoryScreen  # noqa: E402
from zond.ui.screens.inspection_screen import InspectionScreen  # noqa: E402
from zond.utils.logging_setup import configure_logging  # noqa: E402

ASSETS_DIR = BASE_DIR / "assets"
SAMPLE_TEMPLATE = BASE_DIR / "tests" / "data" / "sample.csv"

#: Сколько секунд ждать подключения клиента Flet, прежде чем сдаться.
CLIENT_TIMEOUT = 45.0

#: Сколько секунд отводится на сам сценарий.
SCENARIO_TIMEOUT = 120.0

RESULTS: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"{'OK  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""), flush=True)


def check(name: str, condition: bool, detail: str = "") -> None:
    step(name, bool(condition), detail if not condition else "")


def value_for(field) -> object:
    """Правдоподобное значение для поля любого типа."""

    if field.type is FieldType.CHECKBOX:
        return True

    if field.type is FieldType.DROPDOWN:
        return field.options[0] if field.options else "значение"

    if field.type is FieldType.NUMBER:
        return "42"

    if field.type is FieldType.DATE:
        return "2026-08-11"

    if field.type is FieldType.TIME:
        return "10:30"

    return f"значение {field.name}"


async def exercise(page: ft.Page, app: ZondApp, storage: JsonStorage) -> None:
    """Пройти сценарий на реальной странице."""

    try:
        await asyncio.sleep(1.5)  # даём окну подняться

        check("стартовый экран показан", app.navigator.current is not None)
        check("FilePicker зарегистрирован", len(page.services) >= 1)

        # ---------------------------------------------------- выбор шаблона
        class PickedFile:
            def __init__(self, path: Path) -> None:
                self.path = str(path)
                self.name = path.name

        async def pick_files(**_kwargs):
            return [PickedFile(SAMPLE_TEMPLATE)]

        app.file_picker.pick_files = pick_files
        await app.pick_template()
        await asyncio.sleep(0.3)

        check("шаблон загружен", app.state.template is not None)
        check(
            "открыт экран проверки шаблона", type(app.navigator.current).__name__ == "CheckScreen"
        )

        # ---------------------------------------------------- начало проверки
        app.start_inspection("Насос Н-12", "Иванов И.И.")
        await asyncio.sleep(0.3)

        check("открыт экран заполнения", isinstance(app.navigator.current, InspectionScreen))
        check("черновик сохранён", len(list(storage.drafts_dir.glob("*.json"))) == 1)

        # ------------------------------------- проход по группам с update()
        guard = 0

        while guard < 10:
            guard += 1
            screen = app.navigator.current

            if isinstance(screen, FinishScreen):
                break

            if not isinstance(screen, InspectionScreen):
                raise AssertionError(f"неожиданный экран: {screen!r}")

            group = app.state.current_group

            for control in screen.field_controls:
                control.set_value(value_for(control.field))
                screen._field_changed(control)

            screen._go_next(None)
            await asyncio.sleep(0.25)

            check(f"шаг «{group}» пройден", app.navigator.current is not screen)

        check("открыт экран итогов", isinstance(app.navigator.current, FinishScreen))

        # --------------------------------------------------------------- PDF
        pdf = app.generate_pdf()
        check("PDF сформирован", pdf is not None and pdf.exists(), str(pdf))

        # ----------------------------------------------------------- история
        app.open_history()
        await asyncio.sleep(0.3)
        check("открыт экран истории", isinstance(app.navigator.current, HistoryScreen))

        entries = storage.list_stored()
        check("проверка попала в историю", len(entries) == 1 and not entries[0].is_draft)

        # ----------------------------------------------------------- диалоги
        show_error(page, "Проверка диалога", "Текст ошибки")
        await asyncio.sleep(0.3)
        page.pop_dialog()
        await asyncio.sleep(0.2)

        show_confirm(page, "Подтверждение", "Продолжить?", on_confirm=None)
        await asyncio.sleep(0.3)
        page.pop_dialog()
        await asyncio.sleep(0.2)
        check("диалоги открываются и закрываются", True)

        # ------------------------------------------- нативный выбор даты
        page.show_dialog(ft.DatePicker(help_text="Проверка", on_change=lambda e: None))
        await asyncio.sleep(0.4)
        page.pop_dialog()
        await asyncio.sleep(0.2)
        check("DatePicker открывается", True)

        # ------------------------------- прогресс на смонтированном контроле
        widget = ProgressWidget("Прогресс", 1, 4)
        page.add(widget)
        await asyncio.sleep(0.2)
        widget.set_progress(3, 4)
        await asyncio.sleep(0.2)
        check("set_progress на смонтированном контроле", widget._counter.value == "3/4")

    except Exception:
        step("сценарий выполнен без исключений", False, traceback.format_exc())
    finally:
        _report_and_exit()


def _report_and_exit() -> None:
    failed = [item for item in RESULTS if not item[1]]

    print("\n" + "=" * 70, flush=True)
    print(f"Шагов: {len(RESULTS)}, ошибок: {len(failed)}", flush=True)
    print("=" * 70, flush=True)

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if failed else 0)


def main(page: ft.Page) -> None:
    configure_logging("INFO")
    print("Flet-сеанс подключён, начинаю сценарий…", flush=True)

    storage = JsonStorage(Path(tempfile.mkdtemp(prefix="zond-smoke-")) / "reports")
    app = ZondApp(page, storage=storage)
    app.start()

    page.run_task(exercise, page, app, storage)


if __name__ == "__main__":
    # Сторожевой таймаут взводится до запуска Flet: если клиент не поднимется,
    # main() вообще не будет вызван и скрипт иначе завис бы навсегда.
    import threading

    def _watchdog() -> None:
        import time

        time.sleep(CLIENT_TIMEOUT)

        if not RESULTS:
            print(
                f"\nКлиент Flet не подключился за {CLIENT_TIMEOUT:.0f} с — "
                "вероятно, нет графической сессии.\n"
                "Запустите сценарий на рабочей машине или используйте pytest.\n",
                flush=True,
            )
            os._exit(1)

    threading.Thread(target=_watchdog, daemon=True).start()

    ft.run(main, assets_dir=str(ASSETS_DIR), view=ft.AppView.FLET_APP_HIDDEN)
