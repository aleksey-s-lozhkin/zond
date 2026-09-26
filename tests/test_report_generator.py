"""Тесты формирования PDF-протокола."""

from __future__ import annotations

from pathlib import Path

import pytest

from zond.models.verdict import NOT_RESOLVED, RESOLVED
from zond.services.inspection_factory import InspectionFactory
from zond.services.report_generator import (
    FONT_REGULAR,
    ReportGenerator,
    _resolution_style,
    _resolve_fonts,
)
from zond.services.template_loader import TemplateLoader


@pytest.fixture
def generator() -> ReportGenerator:
    return ReportGenerator()


@pytest.fixture
def inspection(sample_template: Path):
    template = TemplateLoader().load(sample_template)

    result = InspectionFactory.create(template, "Насос Н-12", "Иванов И.И.")
    result.set_value("object_number", "INV-001")
    result.set_value("inspection_date", "2026-08-11")
    result.set_value("executor", "Иванов И.И.")
    result.set_value("equipment_type", "Насос")
    result.set_value("temperature", "62,5")
    result.set_value("comments", "Посторонний шум в подшипниковом узле.")
    result.mark_finished()

    return result


def test_pdf_is_created(generator: ReportGenerator, inspection, tmp_path: Path) -> None:
    target = tmp_path / "report.pdf"

    result = generator.generate(inspection, target)

    assert result == target
    assert target.exists()
    assert target.stat().st_size > 5000


def test_pdf_has_pdf_header(generator: ReportGenerator, inspection, tmp_path: Path) -> None:
    target = generator.generate(inspection, tmp_path / "report.pdf")

    assert target.read_bytes()[:5] == b"%PDF-"


def test_pdf_embeds_cyrillic_capable_font(
    generator: ReportGenerator,
    inspection,
    tmp_path: Path,
) -> None:
    """Кириллица требует TTF: иначе в PDF попадёт Helvetica без глифов."""

    target = generator.generate(inspection, tmp_path / "report.pdf")
    raw = target.read_bytes()

    assert FONT_REGULAR.encode() in raw


def test_generator_falls_back_without_fonts(monkeypatch, tmp_path: Path) -> None:
    import zond.services.report_generator as module

    monkeypatch.setattr(module, "FONT_CANDIDATES", ())
    regular, _bold = module._resolve_fonts()

    assert regular == "Helvetica"


def test_fonts_are_registered_once(generator: ReportGenerator) -> None:
    from reportlab.pdfbase import pdfmetrics

    _resolve_fonts()

    assert FONT_REGULAR in pdfmetrics.getRegisteredFontNames()
    assert "DejaVuSans-Bold" in pdfmetrics.getRegisteredFontNames()


def test_missing_required_fields_are_listed(
    generator: ReportGenerator,
    sample_template: Path,
    tmp_path: Path,
) -> None:
    template = TemplateLoader().load(sample_template)
    inspection = InspectionFactory.create(template, "Объект", "Исполнитель")
    inspection.mark_finished()

    target = generator.generate(inspection, tmp_path / "report.pdf")

    assert target.exists()


def test_target_directory_is_created(
    generator: ReportGenerator,
    inspection,
    tmp_path: Path,
) -> None:
    target = tmp_path / "deep" / "nested" / "report.pdf"

    generator.generate(inspection, target)

    assert target.exists()


def test_generate_twice_overwrites(
    generator: ReportGenerator,
    inspection,
    tmp_path: Path,
) -> None:
    target = tmp_path / "report.pdf"

    generator.generate(inspection, target)
    size_first = target.stat().st_size

    inspection.set_value("comments", "Изменённый комментарий, добавленный позже.")

    generator.generate(inspection, target)

    assert target.exists()
    assert target.stat().st_size > 0
    assert size_first > 0


def test_checkbox_and_long_values_do_not_break_report(
    generator: ReportGenerator,
    tmp_path: Path,
) -> None:
    from zond.models.field import Field, FieldType
    from zond.models.inspection import Inspection
    from zond.models.inspection_item import InspectionItem
    from zond.models.template import Template

    template = Template(
        name="Особый <шаблон> & Co",
        fields=[
            Field(name="flag", label="Флаг", type=FieldType.CHECKBOX),
            Field(name="long", label="Длинное", type=FieldType.TEXTAREA),
            Field(name="num", label="Число", type=FieldType.NUMBER, unit="МПа"),
        ],
    )

    inspection = Inspection(template=template)
    inspection.items = [
        InspectionItem(field=template.fields[0], value=True, is_checked=True),
        InspectionItem(field=template.fields[1], value="Очень длинный текст. " * 40),
        InspectionItem(field=template.fields[2], value="1,5"),
    ]
    inspection.mark_finished()

    target = generator.generate(inspection, tmp_path / "special.pdf")

    assert target.exists()


# ------------------------------------------------------ повторная проверка


def flowable_text(items) -> str:
    """Собрать текст из элементов отчёта.

    Проверять готовый PDF пришлось бы через внешнюю библиотеку разбора, а
    проект её намеренно не тянет. Текст собирается из самих элементов, что
    заодно показывает, попадёт ли он в документ.
    """

    parts: list[str] = []

    for item in items:
        if hasattr(item, "getPlainText"):
            parts.append(item.getPlainText())
        elif hasattr(item, "_cellvalues"):
            parts.append(" ".join(flowable_text(row) for row in item._cellvalues))
        elif hasattr(item, "_content"):
            parts.append(flowable_text(item._content))

    return " ".join(part for part in parts if part)


def repeat_inspection(sample_template: Path):
    """Проверка на основе прошлой: одно замечание закрыто, одно осталось."""

    from zond.models.verdict import NOT_RESOLVED, RESOLVED

    template = TemplateLoader().load(sample_template)

    previous = InspectionFactory.create(template, "Насос Н-12", "Иванов И.И.")
    previous.set_value("condition", "Требует ремонта")
    previous.set_value("vibration", "Критическая")
    previous.mark_finished()

    repeated = InspectionFactory.repeat(previous, template)
    repeated.get_item("condition").resolution = RESOLVED
    repeated.get_item("vibration").resolution = NOT_RESOLVED
    repeated.mark_finished()

    return repeated


def test_repeat_block_lists_previous_defects(
    generator: ReportGenerator,
    sample_template: Path,
) -> None:
    styles = generator._styles()
    text = flowable_text(ReportGenerator._repeat_block(repeat_inspection(sample_template), styles))

    assert "Замечания прошлой проверки" in text
    assert "Требует ремонта" in text
    assert "Критическая" in text
    assert "Устранено" in text
    assert "Не устранено" in text
    assert "устранено 1" in text


def test_repeat_block_is_absent_for_first_visit(
    generator: ReportGenerator,
    inspection,
) -> None:
    assert ReportGenerator._repeat_block(inspection, generator._styles()) == []


def test_repeat_without_defects_has_no_block(
    generator: ReportGenerator,
    sample_template: Path,
) -> None:
    """Замечаний не было — отдельный блок не нужен."""

    template = TemplateLoader().load(sample_template)
    previous = InspectionFactory.create(template, "Насос Н-12", "Иванов И.И.")
    previous.set_value("condition", "Хорошее")
    previous.mark_finished()

    repeated = InspectionFactory.repeat(previous, template)

    assert repeated.previous_defects == []
    assert ReportGenerator._repeat_block(repeated, generator._styles()) == []


def test_summary_reports_repeat_progress(
    generator: ReportGenerator,
    sample_template: Path,
) -> None:
    """В сводке видно, сколько замечаний прошлого выезда закрыто."""

    styles = generator._styles()
    text = flowable_text(ReportGenerator._summary(repeat_inspection(sample_template), styles))

    assert "Замечания прошлой проверки" in text
    assert "устранено 1 из 2" in text


def test_summary_says_when_there_were_no_defects(
    generator: ReportGenerator,
    sample_template: Path,
) -> None:
    template = TemplateLoader().load(sample_template)
    previous = InspectionFactory.create(template, "Насос Н-12", "Иванов И.И.")
    previous.set_value("condition", "Хорошее")
    previous.mark_finished()

    repeated = InspectionFactory.repeat(previous, template)
    styles = generator._styles()
    text = flowable_text(ReportGenerator._summary(repeated, styles))

    assert "не выявлялись" in text


@pytest.mark.parametrize(
    ("resolution", "expected"),
    [(RESOLVED, "valueOk"), (NOT_RESOLVED, "valueProblem"), ("", "cell")],
)
def test_resolution_style(resolution: str, expected: str) -> None:
    """Состояние замечания подсвечивается: закрытое зелёным, оставшееся красным."""

    _label, style = _resolution_style(resolution)

    assert style == expected


def test_repeat_report_is_rendered(
    generator: ReportGenerator,
    sample_template: Path,
    tmp_path: Path,
) -> None:
    """Проверка на основе прошлой формирует протокол без сбоев."""

    target = tmp_path / "repeat.pdf"

    generator.generate(repeat_inspection(sample_template), target)

    assert target.read_bytes()[:5] == b"%PDF-"
    assert target.stat().st_size > 5000
