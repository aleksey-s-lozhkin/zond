"""Тесты образцов шаблонов, поставляемых с приложением.

Образцы — часть поставки, поэтому они должны разбираться без ошибок и
предупреждений. Иначе пользователь, открыв пример, увидит предупреждения или
вообще не сможет загрузить файл.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zond.models.field import FieldType
from zond.services.csv_parser import CSVParser
from zond.services.template_loader import TemplateLoader

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

SAMPLE_TEMPLATES = sorted(TEMPLATES_DIR.glob("*.csv"))

KIP_TEMPLATE = TEMPLATES_DIR / "kip_kranovyy_uzel_mg.csv"

KIP_GROUPS = [
    "Общие сведения",
    "Документация и метрология",
    "Датчики и преобразователи",
    "Манометры",
    "Импульсные трубопроводы",
    "Соединительные коробки",
    "Трубные проводки",
    "Кабельные линии",
    "Заземление и взрывозащита",
    "Функциональная проверка",
    "Заключение",
]


def test_templates_directory_is_not_empty() -> None:
    assert SAMPLE_TEMPLATES, "в templates/ нет ни одного образца"


@pytest.mark.parametrize("path", SAMPLE_TEMPLATES, ids=lambda item: item.name)
def test_sample_template_parses_without_warnings(path: Path) -> None:
    result = CSVParser().parse_template(path)

    assert result.fields, f"{path.name}: не разобрано ни одного поля"
    assert result.warnings == [], f"{path.name}: {result.warnings}"


@pytest.mark.parametrize("path", SAMPLE_TEMPLATES, ids=lambda item: item.name)
def test_sample_template_field_names_are_unique(path: Path) -> None:
    template = TemplateLoader().load(path)
    names = [field.name for field in template.fields]

    assert len(names) == len(set(names))


@pytest.mark.parametrize("path", SAMPLE_TEMPLATES, ids=lambda item: item.name)
def test_sample_template_dropdowns_have_options(path: Path) -> None:
    template = TemplateLoader().load(path)

    for field in template.fields:
        if field.type is FieldType.DROPDOWN:
            assert field.options, f"{path.name}: список «{field.name}» без вариантов"


# ------------------------------------------------------ образец КИП кранового узла


def test_kip_template_exists() -> None:
    assert KIP_TEMPLATE.is_file()


def test_kip_template_structure() -> None:
    template = TemplateLoader().load(KIP_TEMPLATE)

    assert template.name == "kip_kranovyy_uzel_mg"
    assert template.groups == KIP_GROUPS
    assert len(template.fields) >= 100


def test_kip_template_covers_requested_equipment() -> None:
    """В шаблоне должны быть все группы оборудования из задания."""

    template = TemplateLoader().load(KIP_TEMPLATE)
    groups = " ".join(template.groups).lower()

    for expected in ("датчик", "манометр", "импульсн", "коробк", "трубн", "кабельн"):
        assert expected in groups, f"нет группы про «{expected}»"


@pytest.mark.parametrize(
    "group",
    ["Датчики и преобразователи", "Манометры", "Кабельные линии", "Соединительные коробки"],
)
def test_kip_template_groups_are_filled(group: str) -> None:
    template = TemplateLoader().load(KIP_TEMPLATE)

    assert len(template.fields_in_group(group)) >= 10


def test_kip_template_has_manageable_required_share() -> None:
    """Обязательных полей должно быть достаточно много, но шаг не должен
    превращаться в сплошную стену требований."""

    template = TemplateLoader().load(KIP_TEMPLATE)
    required = len(template.required_fields)

    assert required > 40
    assert required < len(template.fields)

    per_group = [
        len([f for f in template.fields_in_group(g) if f.required]) for g in template.groups
    ]

    assert max(per_group) <= 12, f"слишком много обязательных в одной группе: {per_group}"


def test_kip_template_uses_all_relevant_field_types() -> None:
    """Задействованы все типы, кроме флажка: оценочные проверки — списки."""

    template = TemplateLoader().load(KIP_TEMPLATE)
    used = {field.type for field in template.fields}

    assert used == set(FieldType) - {FieldType.CHECKBOX}


def test_kip_template_references_normative_documents() -> None:
    """Поле description должно ссылаться на нормативные документы."""

    template = TemplateLoader().load(KIP_TEMPLATE)
    descriptions = " ".join(field.description for field in template.fields)

    for document in ("ФНП", "ГОСТ", "ПУЭ", "ВРД 39-1.10-006-2000"):
        assert document in descriptions, f"нет ссылки на {document}"


def test_kip_template_manometer_requirements() -> None:
    """Ключевые требования ФНП № 536 к манометрам должны быть в шаблоне."""

    template = TemplateLoader().load(KIP_TEMPLATE)
    by_name = {field.name: field for field in template.fields}

    assert "класс точности не ниже 2,5" in by_name["manometer_accuracy"].label.lower()
    assert "второй трети" in by_name["manometer_scale"].label.lower()
    assert "красная черта" in by_name["manometer_red_mark"].label.lower()
    assert "6 месяцев" in by_name["manometer_control_period"].label.lower()
    assert by_name["manometer_control_period"].required


def test_kip_template_verdict_fields_are_dropdowns() -> None:
    """Оценочные поля не должны быть флажками: иначе нельзя зафиксировать
    несоответствие, не провалив проверку обязательного поля."""

    template = TemplateLoader().load(KIP_TEMPLATE)

    for field in template.required_fields:
        assert field.type is not FieldType.CHECKBOX, (
            f"обязательное поле «{field.name}» — флажок: несоответствие нельзя будет зафиксировать"
        )


def test_kip_template_has_no_checkbox_fields() -> None:
    """В образце КИП все проверки имеют вариант «Не соответствует»."""

    template = TemplateLoader().load(KIP_TEMPLATE)

    assert not [field for field in template.fields if field.type is FieldType.CHECKBOX]
