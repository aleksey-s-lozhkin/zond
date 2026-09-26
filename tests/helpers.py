"""Вспомогательные функции тестов."""

from __future__ import annotations

import flet as ft

from zond.app.app import ZondApp
from zond.models.field import Field, FieldType
from zond.ui.screens.finish_screen import FinishScreen
from zond.ui.screens.inspection_screen import InspectionScreen


def sample_value(field: Field) -> object:
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


def fill_screen(app: ZondApp, screen: InspectionScreen) -> None:
    """Заполнить все поля текущего шага формы."""

    for control in screen.field_controls:
        control.set_value(sample_value(control.field))
        screen._field_changed(control)


def complete_inspection(app: ZondApp) -> FinishScreen:
    """Пройти все группы формы и завершить проверку."""

    guard = 0

    while True:
        guard += 1

        if guard > 50:  # pragma: no cover - защита от зацикливания
            raise AssertionError("Форма не завершилась за 50 шагов")

        screen = app.navigator.current

        if isinstance(screen, FinishScreen):
            return screen

        assert isinstance(screen, InspectionScreen), f"неожиданный экран: {screen!r}"

        fill_screen(app, screen)
        screen._go_next(None)


def find_control(control, control_type):
    """Найти первый контрол указанного типа в дереве.

    Экраны оборачивают содержимое в SafeArea и ScreenBody, поэтому прямые
    проверки ``screen.content`` хрупкие.
    """

    if isinstance(control, control_type):
        return control

    children: list = []

    content = getattr(control, "content", None)
    if content is not None:
        children.append(content)

    for attribute in ("controls", "actions"):
        value = getattr(control, attribute, None)
        if isinstance(value, (list, tuple)):
            children.extend(value)

    for child in children:
        found = find_control(child, control_type)

        if found is not None:
            return found

    return None


def collect_texts(control, found: list[str] | None = None) -> list[str]:
    """Собрать значения всех :class:`flet.Text` в дереве контролов.

    Обход идёт и по ``content``, и по ``controls``: экраны оборачивают
    содержимое в SafeArea и ScreenBody, поэтому одной ветки недостаточно.
    """

    if found is None:
        found = []

    if isinstance(control, ft.Text) and isinstance(control.value, str) and control.value:
        found.append(control.value)

    for attribute in ("content", "controls", "actions"):
        children = getattr(control, attribute, None)

        if isinstance(children, ft.Control):
            collect_texts(children, found)
        elif isinstance(children, (list, tuple)):
            for child in children:
                if isinstance(child, ft.Control):
                    collect_texts(child, found)

    return found
