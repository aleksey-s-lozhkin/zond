"""Вспомогательные функции тестов."""

from __future__ import annotations

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
