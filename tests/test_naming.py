"""Тесты имён файлов проверок и протоколов.

Имя файла видит пользователь в списке файлов и в присоединённом письме.
Полное название шаблона давало имена длиной больше пятидесяти символов,
поэтому схема именования проверяется отдельно.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zond.services.inspection_factory import InspectionFactory
from zond.services.json_storage import JsonStorage
from zond.services.naming import file_stem, safe_name, template_code
from zond.services.template_loader import TemplateLoader

#: Где искать шаблон: учебный лежит в тестовых данных, рабочие — в поставке.
TEMPLATE_DIRS = (Path("templates"), Path("tests/data"))


def make_inspection(name: str = "sample"):
    for directory in TEMPLATE_DIRS:
        candidate = directory / f"{name}.csv"

        if candidate.exists():
            template = TemplateLoader().load(candidate)
            break
    else:  # pragma: no cover - защита от опечатки в тесте
        raise AssertionError(f"шаблон {name} не найден")

    return InspectionFactory.create(template, "Объект", "Исполнитель")


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("tehnicheskie_sredstva_ohrany", "TSO"),
        ("kip_kranovyy_uzel_mg", "KIP"),
        ("elektroustanovki", "EL"),
    ],
)
def test_known_templates_have_short_codes(template: str, expected: str) -> None:
    assert template_code(template) == expected


def test_unknown_template_is_cut_at_word_boundary() -> None:
    """Чужому шаблону аббревиатуру не придумывают — берут начало названия."""

    assert template_code("ventilyaciya_i_ kondicionirovanie") == "ventilyaciya"
    assert template_code("nasosy") == "nasosy"


def test_unknown_template_without_separators_is_cut_by_length() -> None:
    assert template_code("оченьдлинноеимяшаблона") == "оченьдлинное"


def test_empty_name_is_replaced() -> None:
    assert template_code("   ") == "check"
    assert safe_name("!!!") == "check"


def test_stem_has_date_code_and_id() -> None:
    inspection = make_inspection()
    stem = file_stem(inspection)

    parts = stem.split("_")

    assert len(parts) == 3
    assert len(parts[0]) == 10 and parts[0][4] == "-" and parts[0][7] == "-"
    assert parts[1] == "sample"
    assert parts[2] == inspection.inspection_id[:6]


def test_pdf_and_json_share_the_stem() -> None:
    storage = JsonStorage(Path("/tmp/zond-naming"))
    inspection = make_inspection()

    assert storage.pdf_path(inspection).stem == Path(storage.file_name(inspection)).stem


def test_real_template_name_stays_short() -> None:
    """Проверка на том шаблоне, из-за которого схема и менялась."""

    storage = JsonStorage(Path("/tmp/zond-naming"))
    inspection = make_inspection("tehnicheskie_sredstva_ohrany")

    name = storage.file_name(inspection)

    assert name.startswith("20")
    assert "_TSO_" in name
    assert len(name) <= 30, name
