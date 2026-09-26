"""Тесты повторной проверки: перенос значений и разбор прошлых замечаний.

Повторный выезд на тот же объект — основной сценарий эксплуатации: между
выездами шаблон мог измениться, а часть замечаний — остаться незакрытой.
Поэтому проверяется и перенос значений, и то, что замечания не теряются молча.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zond.models.field import Field, FieldType
from zond.models.inspection import FORMAT_VERSION, Inspection
from zond.models.inspection_item import InspectionItem
from zond.models.template import Template
from zond.models.verdict import NOT_RESOLVED, RESOLVED
from zond.services.inspection_factory import InspectionFactory
from zond.services.template_loader import TemplateLoader


@pytest.fixture
def template() -> Template:
    return TemplateLoader().load(Path("tests/data/sample.csv"))


@pytest.fixture
def previous(template: Template) -> Inspection:
    """Заполненная проверка с одним замечанием и чистым полем."""

    inspection = InspectionFactory.create(template, "Насос Н-12", "Иванов И.И.")

    inspection.set_value("object_number", "Н-12")
    inspection.set_value("equipment_type", "Насос")
    inspection.set_value("model", "К-100")
    inspection.set_value("condition", "Требует ремонта")
    inspection.set_value("temperature", "64")
    inspection.set_value("vibration", "Повышенная")
    inspection.set_value("comments", "Течь по сальнику")

    return inspection


# --------------------------------------------------------------- перенос


def test_values_are_carried_over(previous: Inspection, template: Template) -> None:
    """Незаполненные заново поля сохраняют прошлые ответы."""

    repeated = InspectionFactory.repeat(previous, template)

    assert repeated.get_item("model").value == "К-100"
    assert repeated.get_item("temperature").value == "64"
    assert repeated.object_name == "Насос Н-12"
    assert repeated.executor == "Иванов И.И."


def test_repeat_is_linked_to_previous(previous: Inspection, template: Template) -> None:
    repeated = InspectionFactory.repeat(previous, template)

    assert repeated.previous_inspection_id == previous.inspection_id
    assert repeated.is_repeat
    assert repeated.inspection_id != previous.inspection_id


def test_first_inspection_is_not_a_repeat(template: Template) -> None:
    fresh = InspectionFactory.create(template)

    assert not fresh.is_repeat
    assert fresh.previous_inspection_id == ""
    assert fresh.previous_defects == []


def test_empty_previous_values_are_not_carried(template: Template) -> None:
    """Пустое поле в прошлый раз — это не ответ, переносить нечего."""

    previous = InspectionFactory.create(template, "Объект", "Исполнитель")
    previous.set_value("model", "К-100")

    repeated = InspectionFactory.repeat(previous, template)

    assert repeated.get_item("model").value == "К-100"
    assert not repeated.get_item("serial_number").has_previous


def test_previous_value_is_recorded_for_changed_fields(
    previous: Inspection,
    template: Template,
) -> None:
    repeated = InspectionFactory.repeat(previous, template)
    repeated.set_value("condition", "Хорошее")

    changed = {item.field.name for item in repeated.changed_items}

    assert "condition" in changed
    assert "model" not in changed
    assert repeated.get_item("condition").previous_value == "Требует ремонта"


def test_explicit_object_overrides_previous(previous: Inspection, template: Template) -> None:
    repeated = InspectionFactory.repeat(previous, template, object_name="Насос Н-13")

    assert repeated.object_name == "Насос Н-13"


# ------------------------------------------------------- прошлые замечания


def test_previous_defects_are_found(previous: Inspection, template: Template) -> None:
    repeated = InspectionFactory.repeat(previous, template)

    titles = {item.field.name for item in repeated.previous_defects}

    # Поле «Замечания» — свободный текст, его ответ не классифицируется.
    # Значение переносится, но замечанием в смысле разбора не считается.
    assert titles == {"condition", "vibration"}


def test_defects_await_resolution(previous: Inspection, template: Template) -> None:
    """По каждому замечанию проверяющий принимает решение."""

    repeated = InspectionFactory.repeat(previous, template)

    assert len(repeated.pending_resolutions) == 2
    assert repeated.resolved_defects == []


def test_resolved_defect_leaves_pending(previous: Inspection, template: Template) -> None:
    repeated = InspectionFactory.repeat(previous, template)
    repeated.get_item("condition").resolution = RESOLVED
    repeated.get_item("vibration").resolution = NOT_RESOLVED

    assert repeated.pending_resolutions == []

    resolved = {item.field.name for item in repeated.resolved_defects}

    assert resolved == {"condition"}


def test_good_previous_answers_are_not_defects(
    previous: Inspection,
    template: Template,
) -> None:
    """Соответствие прошлого выезда замечанием не считается."""

    previous.set_value("condition", "Хорошее")
    previous.set_value("vibration", "Нормальная")
    previous.set_value("comments", "")

    repeated = InspectionFactory.repeat(previous, template)

    assert repeated.previous_defects == []


# --------------------------------------------- совместимость с новым шаблоном


def test_removed_field_is_skipped(previous: Inspection, template: Template) -> None:
    """Поля нет в новом шаблоне — переносить некуда."""

    shortened = Template(
        name="короткий",
        fields=[field for field in template.fields if field.name != "comments"],
    )

    repeated = InspectionFactory.repeat(previous, shortened)

    assert repeated.get_item("comments") is None


def test_removed_field_with_defect_is_reported(
    previous: Inspection,
    template: Template,
) -> None:
    """О потере замечания честнее сказать, чем молча его выбросить."""

    shortened = Template(
        name="короткий",
        fields=[field for field in template.fields if field.name != "condition"],
    )

    repeated = InspectionFactory.repeat(previous, shortened)

    assert any("Состояние" in warning for warning in repeated.template.warnings)


def test_incompatible_dropdown_value_is_not_substituted(
    previous: Inspection,
    template: Template,
) -> None:
    """Вариант переименовали — подставлять несуществующий нельзя."""

    renamed = Template(
        name="переименованный",
        fields=[
            Field(
                name="condition",
                label="Состояние",
                type=FieldType.DROPDOWN,
                group="Результаты осмотра",
                options=("Хорошее", "Плохое"),
            )
        ],
    )

    repeated = InspectionFactory.repeat(previous, renamed)
    item = repeated.get_item("condition")

    assert item.value is None
    assert item.previous_value == "Требует ремонта"


def test_number_only_carries_numeric_text(
    previous: Inspection,
    template: Template,
) -> None:
    previous.set_value("temperature", "не число")

    repeated = InspectionFactory.repeat(previous, template)

    assert repeated.get_item("temperature").value is None
    assert repeated.get_item("temperature").previous_value == "не число"


def test_checkbox_is_carried_as_boolean(template: Template) -> None:
    with_checkbox = Template(
        name="с флажком",
        fields=[
            Field(
                name="done",
                label="Работы выполнены",
                type=FieldType.CHECKBOX,
                group="Заключение",
            )
        ],
    )
    previous = InspectionFactory.create(with_checkbox)
    previous.set_value("done", True)

    repeated = InspectionFactory.repeat(previous, with_checkbox)

    assert repeated.get_item("done").value is True


# ---------------------------------------------------------- сериализация


def test_repeat_survives_json_round_trip(
    previous: Inspection,
    template: Template,
) -> None:
    repeated = InspectionFactory.repeat(previous, template)
    repeated.get_item("condition").resolution = RESOLVED

    restored = Inspection.from_dict(repeated.to_dict())

    assert restored.previous_inspection_id == previous.inspection_id
    assert restored.get_item("condition").previous_value == "Требует ремонта"
    assert restored.get_item("condition").resolution == RESOLVED
    assert len(restored.previous_defects) == 2


def test_plain_inspection_has_no_repeat_keys(template: Template) -> None:
    """Обычная проверка не обрастает полями повторной."""

    fresh = InspectionFactory.create(template)
    payload = fresh.to_dict()

    assert payload["previous_inspection_id"] == ""
    assert "previous_value" not in payload["items"][0]
    assert "resolution" not in payload["items"][0]


def test_format_three_file_loads_without_loss(previous: Inspection) -> None:
    """Формат 3 отличается только отсутствием ключей повторной проверки."""

    payload = previous.to_dict()
    payload["format_version"] = 3
    payload.pop("previous_inspection_id")
    for item in payload["items"]:
        item.pop("previous_value", None)
        item.pop("resolution", None)

    restored = Inspection.from_dict(payload)

    assert restored.object_name == "Насос Н-12"
    assert restored.previous_inspection_id == ""
    assert restored.template.warnings == []


def test_current_format_is_four() -> None:
    assert FORMAT_VERSION == 4


def test_item_without_previous_value_reports_no_previous() -> None:
    field = Field(name="x", label="X", type=FieldType.TEXT, group="Г")

    assert not InspectionItem(field=field).has_previous
    assert not InspectionItem(field=field, previous_value="", resolution="").has_previous
