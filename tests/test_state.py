"""Тесты состояния сеанса."""

from __future__ import annotations

from pathlib import Path

import pytest

from zond.app.state import ZondState
from zond.services.inspection_factory import InspectionFactory
from zond.services.template_loader import TemplateLoader


@pytest.fixture
def template(sample_template: Path):
    return TemplateLoader().load(sample_template)


@pytest.fixture
def inspection(template):
    return InspectionFactory.create(template)


def test_empty_state() -> None:
    state = ZondState()

    assert not state.has_template
    assert not state.has_inspection
    assert state.groups == []
    assert state.total_groups == 0
    assert state.current_group is None
    assert state.current_fields == []
    assert state.is_finished


def test_set_template_resets_previous_session(template, inspection) -> None:
    state = ZondState()
    state.set_inspection(inspection)
    state.next_group()

    state.set_template(template)

    assert state.has_template
    assert not state.has_inspection
    assert state.current_group_index == 0
    assert not state.is_modified


def test_groups_are_in_template_order(template) -> None:
    state = ZondState()
    state.set_template(template)

    assert state.groups == [
        "Общие сведения",
        "Паспортные данные",
        "Результаты осмотра",
        "Заключение",
    ]
    assert state.total_groups == 4


def test_current_fields_follow_group(template) -> None:
    state = ZondState()
    state.set_template(template)

    assert [field.name for field in state.current_fields] == [
        "object_number",
        "inspection_date",
        "inspector",
    ]

    state.next_group()

    assert [field.name for field in state.current_fields] == [
        "equipment_type",
        "model",
        "serial_number",
    ]


def test_next_group_walks_to_the_end(template) -> None:
    state = ZondState()
    state.set_template(template)
    state.set_inspection(InspectionFactory.create(template))

    assert state.next_group() is True
    assert state.next_group() is True
    assert state.next_group() is True
    assert state.next_group() is False

    assert state.is_finished
    assert state.current_group is None
    assert state.current_fields == []


def test_next_group_beyond_end_is_safe(template) -> None:
    state = ZondState()
    state.set_template(template)
    state.set_inspection(InspectionFactory.create(template))
    state.current_group_index = 99

    assert state.next_group() is False
    assert state.current_group is None


def test_previous_group(template) -> None:
    state = ZondState()
    state.set_template(template)
    state.set_inspection(InspectionFactory.create(template))

    assert state.is_first_group
    assert state.previous_group() is False

    state.next_group()

    assert state.previous_group() is True
    assert state.current_group_index == 0
    assert state.is_first_group


def test_last_group_flag(template) -> None:
    state = ZondState()
    state.set_template(template)
    state.set_inspection(InspectionFactory.create(template))

    assert not state.is_last_group

    state.current_group_index = 3

    assert state.is_last_group


def test_answered_and_total_fields(template) -> None:
    state = ZondState()
    state.set_template(template)
    inspection = InspectionFactory.create(template)
    state.set_inspection(inspection)

    assert (state.answered_fields, state.total_fields) == (0, 12)

    inspection.set_value("object_number", "X")

    assert state.answered_fields == 1


def test_goto_first_incomplete_prefers_missing_required(template) -> None:
    inspection = InspectionFactory.create(template)

    # Заполняем обязательные первой группы, но оставляем обязательное в третьей.
    inspection.set_value("object_number", "1")
    inspection.set_value("inspection_date", "2026-01-01")
    inspection.set_value("inspector", "Иванов")
    inspection.set_value("equipment_type", "Насос")

    state = ZondState()
    state.set_inspection(inspection)
    state.goto_first_incomplete_group()

    assert state.current_group == "Результаты осмотра"


def test_goto_first_incomplete_uses_first_empty_when_all_required_filled(template) -> None:
    inspection = InspectionFactory.create(template)

    for item in inspection.items:
        if item.field.required:
            inspection.set_value(item.field.name, "x")

    state = ZondState()
    state.set_inspection(inspection)
    state.goto_first_incomplete_group()

    # Все обязательные заполнены, значит ориентируемся на первое пустое поле.
    assert state.current_group == "Паспортные данные"


def test_goto_first_incomplete_on_empty_inspection(template) -> None:
    state = ZondState()
    state.set_inspection(InspectionFactory.create(template))
    state.goto_first_incomplete_group()

    assert state.current_group_index == 0


def test_goto_first_incomplete_without_inspection(template) -> None:
    state = ZondState()
    state.set_template(template)

    state.goto_first_incomplete_group()

    assert state.current_group_index == 0


def test_mark_modified_and_saved(template) -> None:
    state = ZondState()
    state.set_inspection(InspectionFactory.create(template))

    assert not state.is_modified

    state.mark_modified()
    assert state.is_modified

    state.mark_saved()
    assert not state.is_modified


def test_reset_clears_everything(template) -> None:
    state = ZondState()
    state.set_inspection(InspectionFactory.create(template))
    state.next_group()
    state.mark_modified()

    state.reset()

    assert not state.has_template
    assert not state.has_inspection
    assert state.current_group_index == 0
    assert not state.is_modified
