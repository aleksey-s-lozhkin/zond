"""Общая проверка обработчиков: Flet дожидается только настоящих корутин.

Обработчик, который возвращает корутину, но сам корутиной не является — это
lambda или обычная функция, — не дожидается никем. Нажатие проходит, действие
не начинается, и никакой ошибки при этом не возникает: ни исключения, ни
записи в журнале. Именно так перестали открываться шаблоны.

Ошибка этого класса уже случалась в проекте дважды, поэтому проверка общая:
обходятся все экраны, а не только тот, где её нашли.
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

import flet as ft
import pytest

from zond.app.app import ZondApp

#: Атрибуты, через которые контролы ссылаются друг на друга.
CHILD_ATTRIBUTES = (
    "controls",
    "content",
    "actions",
    "title",
    "subtitle",
    "leading",
    "trailing",
    "label",
    "content_control",
)

#: Обработчики, которые вызывает Flet.
HANDLER_ATTRIBUTES = (
    "on_click",
    "on_select",
    "on_change",
    "on_confirm",
    "on_submit",
    "on_dismiss",
)


class DummyEvent:
    """Событие-заглушка: обработчикам нужен хотя бы один аргумент."""

    control = None
    data = None
    page = None


def walk(control, seen: set[int] | None = None):
    """Обойти дерево контролов, не зацикливаясь на повторах."""

    seen = set() if seen is None else seen

    if id(control) in seen or not isinstance(control, ft.Control):
        return

    seen.add(id(control))
    yield control

    for attribute in CHILD_ATTRIBUTES:
        child = getattr(control, attribute, None)

        if isinstance(child, ft.Control):
            yield from walk(child, seen)
        elif isinstance(child, (list, tuple)):
            for item in child:
                yield from walk(item, seen)


def dropped_coroutines(screen) -> list[str]:
    """Обработчики экрана, которые возвращают корутину, не будучи корутинами."""

    problems: list[str] = []

    for control in walk(screen.content):
        for attribute in HANDLER_ATTRIBUTES:
            handler = getattr(control, attribute, None)

            if not callable(handler) or inspect.iscoroutinefunction(handler):
                continue

            try:
                result = handler(DummyEvent())
            except Exception:
                continue

            if inspect.isawaitable(result):
                problems.append(f"{type(control).__name__}.{attribute}")

                if inspect.iscoroutine(result):
                    result.close()

    return problems


def check(app: ZondApp, screen=None) -> None:
    """Проверить текущий экран приложения."""

    target = screen if screen is not None else app.navigator.current

    assert target is not None, "экран не построен"

    problems = dropped_coroutines(target)

    assert not problems, (
        f"обработчики возвращают корутину, но сами ею не являются — Flet их не дождётся: {problems}"
    )


# ------------------------------------------------------------------ экраны


def test_start_screen_handlers(app: ZondApp) -> None:
    app.start()

    check(app)


def test_templates_screen_handlers(app: ZondApp) -> None:
    """Открытие шаблона по нажатию на строку — тот самый случай."""

    app.library.ensure()
    app.start()
    app.open_templates()

    check(app)


def test_help_screen_handlers(app: ZondApp) -> None:
    from zond.ui.screens.help_screen import HelpScreen

    app.start()
    app.navigator.push(HelpScreen(app))

    check(app)


def test_history_screen_handlers(app: ZondApp) -> None:
    app.start()
    app.open_history()

    check(app)


def test_check_screen_handlers(app: ZondApp, sample_template: Path, choose_file) -> None:
    """Экран шаблона: на нём живёт выбор прошлой проверки."""

    choose_file(sample_template)
    asyncio.run(app.pick_template())
    app.start()

    check(app)


def test_opening_template_from_the_screen(app: ZondApp) -> None:
    """Нажатие на строку шаблона действительно открывает шаблон.

    Проверка идёт через обработчик контрола, а не через метод приложения:
    ошибка была именно в связке обработчика с Flet, и вызов метода напрямую
    её не видит.
    """

    from zond.ui.screens.templates_screen import TemplatesScreen

    app.library.ensure()
    app.start()
    app.open_templates()

    screen = app.navigator.current
    assert isinstance(screen, TemplatesScreen)

    entry = app.library.list_entries()[0]

    asyncio.run(screen._open_handler(entry)(DummyEvent()))

    assert app.state.template is not None
    assert app.state.template.name == entry.name


def test_restore_button_handler(app: ZondApp) -> None:
    """Кнопка возврата примеров также должна работать."""

    app.library.ensure()
    app.start()
    app.open_templates()

    screen = app.navigator.current
    entry = next(item for item in app.library.list_entries() if item.name.startswith("КИП"))
    app.delete_template(entry)

    labels = [control for control in walk(screen.content) if isinstance(control, ft.TextButton)]

    assert labels, "кнопка возврата примеров не найдена"

    labels[0].on_click(DummyEvent())

    assert any(item.name.startswith("КИП") for item in app.library.list_entries())


@pytest.mark.parametrize("platform", ["android", "macos"])
def test_handlers_do_not_depend_on_platform(app: ZondApp, platform: str) -> None:
    """Проверка не должна зависеть от платформы: ошибка была не в ней."""

    app.page.platform = platform
    app.start()

    check(app)
