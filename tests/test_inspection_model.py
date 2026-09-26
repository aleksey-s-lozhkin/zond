"""Тесты модели проверки и сериализации."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from zond.models.field import Field, FieldType
from zond.models.inspection import FORMAT_VERSION, Inspection, format_datetime
from zond.models.template import Template
from zond.services.errors import StorageError
from zond.services.inspection_factory import InspectionFactory
from zond.services.template_loader import TemplateLoader


@pytest.fixture
def inspection(sample_template: Path) -> Inspection:
    template = TemplateLoader().load(sample_template)
    return InspectionFactory.create(template, "Насос Н-12", "Иванов И.И.")


def test_factory_creates_item_per_field(inspection: Inspection) -> None:
    assert inspection.total_items == len(inspection.template.fields)
    assert inspection.answered_count == 0
    assert not inspection.is_finished


def test_set_value_marks_checked(inspection: Inspection) -> None:
    item = inspection.set_value("object_number", "INV-001")

    assert item is not None
    assert item.value == "INV-001"
    assert item.is_checked is True
    assert inspection.answered_count == 1


def test_field_value_helper(inspection: Inspection) -> None:
    inspection.set_value("object_number", "INV-001")

    assert inspection.field_value("object_number") == "INV-001"
    assert inspection.field_value("unknown") is None


def test_missing_required_tracks_empty_required_fields(inspection: Inspection) -> None:
    assert len(inspection.missing_required) == 5
    assert not inspection.is_ready

    for item in list(inspection.missing_required):
        inspection.set_value(item.field.name, "x")

    assert inspection.is_ready


def test_progress_ratio(inspection: Inspection) -> None:
    assert inspection.progress == 0.0

    inspection.set_value("object_number", "A")
    inspection.set_value("executor", "B")

    assert inspection.progress == pytest.approx(2 / inspection.total_items)


def test_title_prefers_object_name(inspection: Inspection) -> None:
    assert inspection.title == "Насос Н-12"


def test_title_falls_back_to_template(inspection: Inspection) -> None:
    inspection.object_name = ""

    assert inspection.title == inspection.template.name


def test_title_falls_back_to_object_number_field(inspection: Inspection) -> None:
    inspection.object_name = ""
    inspection.set_value("object_number", "INV-777")

    assert inspection.title == "INV-777"


def test_mark_finished_sets_timestamp(inspection: Inspection) -> None:
    inspection.mark_finished()

    assert inspection.is_finished
    assert inspection.finished_at is not None
    assert inspection.finished_at.tzinfo is not None


def test_round_trip_is_lossless(inspection: Inspection) -> None:
    inspection.set_value("object_number", "INV-001")
    inspection.set_value("equipment_type", "Насос")
    inspection.set_value("temperature", "62,5")
    inspection.mark_finished()

    restored = Inspection.from_dict(inspection.to_dict())

    assert restored.to_dict() == inspection.to_dict()


def test_payload_is_self_describing(inspection: Inspection) -> None:
    payload = inspection.to_dict()

    assert payload["format_version"] == FORMAT_VERSION
    assert payload["template"]["name"] == "sample"

    fields = {item["name"]: item for item in payload["template"]["fields"]}

    assert fields["equipment_type"]["options"] == [
        "Насос",
        "Компрессор",
        "Вентилятор",
        "Трансформатор",
        "Электродвигатель",
    ]
    assert fields["temperature"]["unit"] == "°C"
    assert fields["inspection_date"]["type"] == "date"


def test_resume_restores_form_without_csv(inspection: Inspection) -> None:
    """Проверка восстанавливается по JSON, даже если шаблона нет рядом."""

    inspection.set_value("object_number", "INV-001")
    payload = inspection.to_dict()

    restored = Inspection.from_dict(payload)

    assert [item.field.name for item in restored.items] == [
        item.field.name for item in inspection.items
    ]
    assert restored.get_item("object_number").value == "INV-001"
    assert restored.get_item("temperature").field.unit == "°C"


def test_from_dict_fills_missing_items() -> None:
    template = Template(
        name="t",
        fields=[
            Field(name="a", label="A"),
            Field(name="b", label="B"),
        ],
    )

    payload = {
        "format_version": FORMAT_VERSION,
        "template": template.to_dict(),
        "items": [{"field": "a", "value": "1", "is_checked": True}],
    }

    restored = Inspection.from_dict(payload)

    assert len(restored.items) == 2
    assert restored.get_item("b") is not None
    assert restored.get_item("b").is_empty


def test_unknown_item_field_is_ignored() -> None:
    template = Template(name="t", fields=[Field(name="a", label="A")])

    payload = {
        "format_version": FORMAT_VERSION,
        "template": template.to_dict(),
        "items": [
            {"field": "a", "value": "1"},
            {"field": "ghost", "value": "?"},
        ],
    }

    restored = Inspection.from_dict(payload)

    assert len(restored.items) == 1


def test_newer_format_is_rejected() -> None:
    with pytest.raises(StorageError, match="более новой версией"):
        Inspection.from_dict({"format_version": FORMAT_VERSION + 1, "items": []})


def test_v1_payload_is_migrated() -> None:
    """Файлы первой версии читаются: поля восстанавливаются по именам."""

    payload = {
        "format_version": 1,
        "template": "sample",
        "started_at": "2026-08-11T07:17:07.206313",
        "items": [
            {"field": "object_number", "value": "INV-1", "is_checked": True},
            {"field": "inspector", "value": None},
        ],
    }

    restored = Inspection.from_dict(payload)

    assert restored.template.name == "sample"
    assert [item.field.name for item in restored.items] == ["object_number", "inspector"]
    assert restored.get_item("object_number").value == "INV-1"
    assert restored.started_at.tzinfo is not None
    assert any("миграцией" in warning for warning in restored.template.warnings)


def test_payload_uses_executor_key(inspection: Inspection) -> None:
    """Исполнителем может быть приборист или слесарь КИПиА, а не только
    инспектор, поэтому ключ называется executor."""

    payload = inspection.to_dict()

    assert payload["executor"] == "Иванов И.И."
    assert "inspector" not in payload


def test_v2_payload_with_inspector_key_is_migrated() -> None:
    """До формата 3 исполнитель хранился в ключе inspector."""

    payload = {
        "format_version": 2,
        "template": Template(name="sample", fields=[Field(name="a", label="A")]).to_dict(),
        "items": [{"field": "a", "value": "1", "is_checked": True}],
        "inspector": "Петров П.П., приборист",
    }

    restored = Inspection.from_dict(payload)

    assert restored.executor == "Петров П.П., приборист"
    # Перенос ключа без потерь, поэтому предупреждений быть не должно.
    assert restored.template.warnings == []


def test_v3_payload_with_executor_key() -> None:
    payload = {
        "format_version": 3,
        "template": Template(name="sample", fields=[Field(name="a", label="A")]).to_dict(),
        "items": [],
        "executor": "Сидоров С.С., слесарь КИПиА",
    }

    assert Inspection.from_dict(payload).executor == "Сидоров С.С., слесарь КИПиА"


def test_v1_without_items_is_rejected() -> None:
    with pytest.raises(StorageError, match="нет ни описания полей"):
        Inspection.from_dict({"format_version": 1, "template": "x", "items": []})


def test_naive_datetime_is_treated_as_utc() -> None:
    payload = {
        "format_version": FORMAT_VERSION,
        "template": Template(name="t", fields=[Field(name="a")]).to_dict(),
        "items": [],
        "started_at": "2026-08-11T07:17:07",
    }

    restored = Inspection.from_dict(payload)

    assert restored.started_at == datetime(2026, 8, 11, 7, 17, 7, tzinfo=UTC)


def test_checkbox_value_is_boolean() -> None:
    template = Template(
        name="t",
        fields=[Field(name="flag", label="Флаг", type=FieldType.CHECKBOX)],
    )

    payload = {
        "format_version": FORMAT_VERSION,
        "template": template.to_dict(),
        "items": [{"field": "flag", "value": 1, "is_checked": True}],
    }

    restored = Inspection.from_dict(payload)

    assert restored.get_item("flag").value is True


def test_checkbox_false_counts_as_empty() -> None:
    template = Template(
        name="t",
        fields=[Field(name="flag", label="Флаг", type=FieldType.CHECKBOX, required=True)],
    )
    inspection = Inspection(template=template, items=[])

    from zond.models.inspection_item import InspectionItem

    inspection.items = [InspectionItem(field=template.fields[0], value=False)]

    assert inspection.get_item("flag").is_empty
    assert inspection.missing_required


def test_display_value_formats_date_and_time() -> None:
    template = Template(
        name="t",
        fields=[
            Field(name="d", label="Дата", type=FieldType.DATE),
            Field(name="t", label="Время", type=FieldType.TIME),
            Field(name="c", label="Флаг", type=FieldType.CHECKBOX),
            Field(name="x", label="Текст"),
        ],
    )

    inspection = InspectionFactory.create(template)
    inspection.set_value("d", "2026-08-11")
    inspection.set_value("t", "09:05")
    inspection.set_value("c", True)

    assert inspection.get_item("d").display_value() == "11.08.2026"
    assert inspection.get_item("t").display_value() == "09:05"
    assert inspection.get_item("c").display_value() == "Да"
    assert inspection.get_item("x").display_value() == "—"


def test_format_datetime_handles_none() -> None:
    assert format_datetime(None) == "—"


def test_template_groups_and_helpers(sample_template: Path) -> None:
    template = TemplateLoader().load(sample_template)

    assert template.total_groups == 4
    assert len(template.fields_in_group("Паспортные данные")) == 3
    assert template.fields_in_group("Нет такой группы") == []
