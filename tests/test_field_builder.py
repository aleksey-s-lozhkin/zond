"""Тесты полей формы."""

from __future__ import annotations

import flet as ft
import pytest

from zond.models.field import Field, FieldType
from zond.ui.widgets.field_builder import FieldBuilder, FieldControl


def make(field_type: FieldType, **kwargs) -> Field:
    defaults = {"name": "f", "label": "Поле", "type": field_type}
    return Field(**{**defaults, **kwargs})


@pytest.mark.parametrize("field_type", list(FieldType))
def test_every_type_builds_a_control(field_type: FieldType) -> None:
    """Раньше типы date и time отдавали текст «Неизвестный тип»."""

    control = FieldControl(make(field_type))

    assert control.input is not None
    assert "Неизвестный тип" not in str(getattr(control.input, "value", ""))


def test_text_field_keeps_label_and_placeholder() -> None:
    control = FieldControl(make(FieldType.TEXT, placeholder="Введите", description="Подсказка"))

    assert control.input.hint_text == "Введите"
    assert any("Подсказка" in getattr(item, "value", "") for item in control.controls)


def test_required_marker_is_rendered() -> None:
    control = FieldControl(make(FieldType.TEXT, required=True))

    label = control.controls[0]

    assert isinstance(label, ft.Text)
    assert "".join(span.text for span in label.spans).endswith(" *")


def test_label_is_a_single_text_so_it_wraps() -> None:
    """Подпись должна переноситься, а не обрезаться на узком окне.

    Строка из отдельных контролов в Row не переносится: длинная подпись
    уезжает за край. Один Text со spans переносится по доступной ширине.
    """

    control = FieldControl(make(FieldType.TEXT, required=True, unit="МПа"))
    label = control.controls[0]

    assert isinstance(label, ft.Text)
    assert len(label.spans) == 3


def test_required_field_is_highlighted_with_colour() -> None:
    required = FieldControl(make(FieldType.TEXT, required=True))
    optional = FieldControl(make(FieldType.TEXT))

    assert required.input.fill_color != optional.input.fill_color
    assert required.input.border_color != optional.input.border_color


def test_required_checkbox_is_wrapped_in_tinted_container() -> None:
    required = FieldControl(make(FieldType.CHECKBOX, required=True))
    optional = FieldControl(make(FieldType.CHECKBOX))

    assert isinstance(required.controls[0], ft.Container)
    assert not isinstance(optional.controls[0], ft.Container)


def test_unit_is_rendered_as_suffix() -> None:
    control = FieldControl(make(FieldType.NUMBER, unit="°C"))

    assert control.input.suffix is not None


def test_textarea_is_multiline() -> None:
    assert FieldControl(make(FieldType.TEXTAREA)).input.multiline is True


def test_number_uses_numeric_keyboard() -> None:
    assert FieldControl(make(FieldType.NUMBER)).input.keyboard_type == ft.KeyboardType.NUMBER


def test_dropdown_options_are_copied() -> None:
    control = FieldControl(make(FieldType.DROPDOWN, options=("A", "B")))

    assert [option.key for option in control.input.options] == ["A", "B"]


def test_checkbox_uses_label_inline() -> None:
    control = FieldControl(make(FieldType.CHECKBOX))

    assert control.input.label == "Поле"
    # Отдельной строки-подписи у флажка нет.
    assert len(control.controls) == 1


# ------------------------------------------------------------------ значения


def test_text_value_is_trimmed() -> None:
    control = FieldControl(make(FieldType.TEXT), value="  да  ")

    assert control.value == "да"


def test_empty_text_becomes_none() -> None:
    assert FieldControl(make(FieldType.TEXT), value="   ").value is None


def test_date_display_and_iso_value() -> None:
    control = FieldControl(make(FieldType.DATE), value="2026-08-11")

    assert control.input.value == "11.08.2026"
    assert control.value == "2026-08-11"


def test_date_accepts_russian_format() -> None:
    control = FieldControl(make(FieldType.DATE), value="11.08.2026")

    assert control.value == "2026-08-11"


def test_time_value_is_normalized() -> None:
    control = FieldControl(make(FieldType.TIME), value="9:05")

    assert control.value == "09:05"


def test_checkbox_value_is_bool() -> None:
    assert FieldControl(make(FieldType.CHECKBOX)).value is False


def test_set_value_updates_input() -> None:
    control = FieldControl(make(FieldType.TEXT))
    control.set_value("новое")

    assert control.value == "новое"


def test_set_value_on_checkbox() -> None:
    control = FieldControl(make(FieldType.CHECKBOX))
    control.set_value(True)

    assert control.value is True


# ---------------------------------------------------------------- валидация


def test_required_empty_text_fails() -> None:
    assert FieldControl(make(FieldType.TEXT, required=True)).validate() == "Обязательное поле"


def test_optional_empty_text_passes() -> None:
    assert FieldControl(make(FieldType.TEXT)).validate() is None


def test_required_unchecked_checkbox_fails() -> None:
    control = FieldControl(make(FieldType.CHECKBOX, required=True))

    assert control.is_empty
    assert control.validate() == "Обязательное поле"


def test_checked_checkbox_passes() -> None:
    control = FieldControl(make(FieldType.CHECKBOX, required=True), value=True)

    assert not control.is_empty
    assert control.validate() is None


def test_number_rejects_garbage() -> None:
    control = FieldControl(make(FieldType.NUMBER), value="abc")

    assert control.validate() == "Введите число"


def test_number_accepts_decimal_comma() -> None:
    control = FieldControl(make(FieldType.NUMBER), value="62,5")

    assert control.validate() is None


def test_date_rejects_garbage() -> None:
    control = FieldControl(make(FieldType.DATE), value="32.13.2026")

    assert control.validate() == "Укажите дату в формате ДД.ММ.ГГГГ"


def test_time_rejects_garbage() -> None:
    control = FieldControl(make(FieldType.TIME), value="25:99")

    assert control.validate() == "Укажите время в формате ЧЧ:ММ"


# ------------------------------------------------------------------ ошибки


def test_show_error_sets_text_field_error() -> None:
    control = FieldControl(make(FieldType.TEXT))
    control.show_error("Проблема")

    assert control.input.error == "Проблема"

    control.show_error(None)

    assert control.input.error is None


def test_show_error_sets_dropdown_error() -> None:
    control = FieldControl(make(FieldType.DROPDOWN, options=("A",)))
    control.show_error("Проблема")

    assert control.input.error_text == "Проблема"


def test_show_error_sets_checkbox_error() -> None:
    control = FieldControl(make(FieldType.CHECKBOX))
    control.show_error("Проблема")

    assert control.input.error == "Проблема"


# ------------------------------------------------------------------ события


def test_change_callback_fires_on_set_value() -> None:
    seen: list[FieldControl] = []

    control = FieldControl(make(FieldType.TEXT), on_change=seen.append)
    control._emit_change()

    assert seen == [control]


def test_change_callback_clears_error() -> None:
    control = FieldControl(make(FieldType.TEXT), on_change=lambda item: None)
    control.show_error("Проблема")

    control._emit_change()

    assert control.input.error is None


def test_builder_returns_field_control() -> None:
    control = FieldBuilder.build(make(FieldType.TEXT), value="x")

    assert isinstance(control, FieldControl)
    assert control.value == "x"


def test_description_is_rendered() -> None:
    control = FieldControl(make(FieldType.TEXT, description="Пояснение"))

    assert any(getattr(item, "value", "") == "Пояснение" for item in control.controls)
