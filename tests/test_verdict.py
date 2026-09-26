"""Тесты оценки ответов и цветовой разметки протокола."""

from __future__ import annotations

from pathlib import Path

import pytest

from zond.models.field import Field, FieldType
from zond.models.inspection import Inspection
from zond.models.inspection_item import InspectionItem
from zond.models.template import Template
from zond.models.verdict import Verdict, classify, is_ok, is_problem
from zond.services.inspection_factory import InspectionFactory
from zond.services.report_generator import ReportGenerator, _value_style
from zond.services.template_loader import TemplateLoader

# ------------------------------------------------------------------ разбор


@pytest.mark.parametrize(
    "answer",
    [
        "Соответствует",
        "соответствует",
        "Соответствует.",
        "Исправно",
        "Выполнено",
        "В наличии",
        "Да",
        "Работоспособно",
        "Удовлетворительно",
        "Нормальная",
        "Герметично",
        "Допускается",
    ],
)
def test_positive_answers(answer: str) -> None:
    assert classify(answer) is Verdict.OK


@pytest.mark.parametrize(
    "answer",
    [
        "Не соответствует",
        "Неисправно",
        "Не выполнено",
        "Отсутствует",
        "Нет",
        "Неудовлетворительно",
        "Ограниченно работоспособно",
        "Требует ремонта",
        "Аварийное",
        "Повышенная",
        "Не герметично",
        "Частично",
        "Допускается с ограничениями",
    ],
)
def test_negative_answers(answer: str) -> None:
    assert classify(answer) is Verdict.PROBLEM


@pytest.mark.parametrize("answer", ["Не применимо", "Не требуется", "—", "-", "", None])
def test_neutral_answers(answer: object) -> None:
    assert classify(answer) is Verdict.NEUTRAL


def test_negative_prefix_is_treated_as_problem() -> None:
    """Незнакомая формулировка с отрицанием — это несоответствие."""

    assert classify("Не соответствует проекту") is Verdict.PROBLEM
    assert classify("не отвечает требованиям") is Verdict.PROBLEM


def test_number_and_free_text_are_neutral() -> None:
    assert classify("62,5") is Verdict.NEUTRAL
    assert classify("PT-1401, зав. № 114502") is Verdict.NEUTRAL
    assert classify("2026-08-11") is Verdict.NEUTRAL


def test_boolean_values() -> None:
    assert classify(True) is Verdict.OK
    assert classify(False) is Verdict.PROBLEM


def test_helpers() -> None:
    assert is_ok("Соответствует")
    assert not is_ok("Не соответствует")
    assert is_problem("Неисправно")
    assert not is_problem("Исправно")


def test_neutral_beats_negative_prefix() -> None:
    """«Не применимо» начинается с «Не», но нарушением не является."""

    assert classify("Не применимо") is Verdict.NEUTRAL
    assert classify("Не требуется") is Verdict.NEUTRAL


# ------------------------------------------------------- модель проверки


def make_inspection(*pairs: tuple[str, object]) -> Inspection:
    template = Template(
        name="t",
        fields=[Field(name=name, label=name, group="Группа") for name, _ in pairs],
    )
    inspection = Inspection(template=template)
    inspection.items = [InspectionItem(field=field) for field in template.fields]

    for name, value in pairs:
        inspection.set_value(name, value)

    return inspection


def test_inspection_separates_problems_and_conformities() -> None:
    inspection = make_inspection(
        ("a", "Соответствует"),
        ("b", "Не соответствует"),
        ("c", "Не применимо"),
        ("d", "62,5"),
        ("e", "Исправно"),
    )

    assert [item.field.name for item in inspection.problems] == ["b"]
    assert [item.field.name for item in inspection.conformities] == ["a", "e"]


def test_empty_items_are_not_problems() -> None:
    """Пустое поле — это не несоответствие, а незаполненное поле."""

    inspection = make_inspection(("a", "Не соответствует"), ("b", None))

    assert [item.field.name for item in inspection.problems] == ["a"]


def test_problems_by_group() -> None:
    inspection = make_inspection(("a", "Не соответствует"), ("b", "Неисправно"))

    assert list(inspection.problems_by_group) == ["Группа"]
    assert len(inspection.problems_by_group["Группа"]) == 2


def test_sample_template_has_conformities() -> None:
    template = TemplateLoader().load(Path("templates/kip_kranovyy_uzel_mg.csv"))
    inspection = InspectionFactory.create(template)

    for item in inspection.items:
        if item.field.type is FieldType.DROPDOWN:
            inspection.set_value(item.field.name, "Соответствует")

    assert len(inspection.conformities) > 50
    assert inspection.problems == []


# --------------------------------------------------- разметка протокола


def test_value_style_colours_answers() -> None:
    template = Template(
        name="t",
        fields=[
            Field(name="ok", label="В норме"),
            Field(name="bad", label="Нарушение"),
            Field(name="neutral", label="Замер"),
        ],
    )
    inspection = Inspection(template=template)
    inspection.items = [InspectionItem(field=field) for field in template.fields]
    inspection.set_value("ok", "Соответствует")
    inspection.set_value("bad", "Не соответствует")
    inspection.set_value("neutral", "62,5")

    styles = {item.field.name: _value_style(item) for item in inspection.items}

    assert styles["ok"] == "cellOk"
    assert styles["bad"] == "cellProblem"
    assert styles["neutral"] == "cell"


def test_empty_value_is_muted() -> None:
    item = InspectionItem(field=Field(name="a", label="A"))

    assert _value_style(item) == "cellMuted"


def test_report_styles_have_colours() -> None:
    styles = ReportGenerator()._styles()

    assert styles["cellOk"].textColor is not None
    assert styles["cellProblem"].textColor is not None
    assert styles["cellOk"].textColor != styles["cellProblem"].textColor


# ------------------------------------------------- блок несоответствий


def test_problem_block_lists_problems() -> None:
    generator = ReportGenerator()
    styles = generator._styles()

    inspection = make_inspection(("a", "Не соответствует"), ("b", "Соответствует"))
    story = generator._problem_block(inspection, styles)

    heading = story[0]
    assert "Выявленные несоответствия" in heading.text
    assert "1" in heading.text


def test_problem_block_reports_absence_of_problems() -> None:
    generator = ReportGenerator()
    styles = generator._styles()

    inspection = make_inspection(("a", "Соответствует"))
    story = generator._problem_block(inspection, styles)

    assert "не выявлено" in story[0].text.lower()


def test_report_renders_with_and_without_problems(tmp_path: Path) -> None:
    generator = ReportGenerator()

    for name, answers in (
        ("clean", [("a", "Соответствует")]),
        ("dirty", [("a", "Не соответствует")]),
    ):
        inspection = make_inspection(*answers)
        inspection.mark_finished()

        target = generator.generate(inspection, tmp_path / f"{name}.pdf")

        assert target.exists()
        assert target.read_bytes()[:5] == b"%PDF-"
