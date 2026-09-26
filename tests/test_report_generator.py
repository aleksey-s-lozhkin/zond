"""Тесты формирования PDF-протокола."""

from __future__ import annotations

from pathlib import Path

import pytest

from zond.services.inspection_factory import InspectionFactory
from zond.services.report_generator import FONT_REGULAR, ReportGenerator, _resolve_fonts
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
    result.set_value("inspector", "Иванов И.И.")
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
    inspection = InspectionFactory.create(template, "Объект", "Инспектор")
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
