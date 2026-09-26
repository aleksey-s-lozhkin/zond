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
ELECTRICAL_TEMPLATE = TEMPLATES_DIR / "elektroustanovki.csv"
SECURITY_TEMPLATE = TEMPLATES_DIR / "tehnicheskie_sredstva_ohrany.csv"

KIP_GROUPS = [
    "Общие сведения",
    "Документация и метрология",
    "Датчики и преобразователи",
    "Манометры",
    "Импульсные и трубные проводки",
    "Соединительные коробки",
    "Кабельные линии",
    "Заземление и взрывозащита",
    "Функциональная проверка",
    "Заключение",
]

ELECTRICAL_GROUPS = [
    "Общие сведения",
    "Документация и организация эксплуатации",
    "Заземление и защитные меры",
    "Кабельные линии и электропроводки",
    "Щиты и распределительные устройства",
    "Электродвигатели и приводы",
    "Освещение и розеточные сети",
    "Защита от перенапряжений и молниезащита",
    "Взрывозащищённое электрооборудование",
    "Безопасность работ",
    "Заключение",
]

SECURITY_GROUPS = [
    "Общие сведения",
    "Документация и организация",
    "Инженерно-техническая укреплённость",
    "Охранная и тревожная сигнализация",
    "Охранное телевидение",
    "Контроль и управление доступом",
    "Периметровые средства обнаружения",
    "Электропитание и линии связи",
    "Проверка работоспособности",
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
    [
        "Датчики и преобразователи",
        "Манометры",
        "Кабельные линии",
        "Соединительные коробки",
        "Импульсные и трубные проводки",
    ],
)
def test_kip_template_groups_are_filled(group: str) -> None:
    template = TemplateLoader().load(KIP_TEMPLATE)

    assert len(template.fields_in_group(group)) >= 10


def test_kip_impulse_and_tubing_groups_are_merged() -> None:
    """Импульсные трубопроводы и трубные проводки — это одно и то же,
    поэтому они сведены в один шаг без дублирующих проверок."""

    template = TemplateLoader().load(KIP_TEMPLATE)

    assert "Импульсные и трубные проводки" in template.groups
    assert "Импульсные трубопроводы" not in template.groups
    assert "Трубные проводки" not in template.groups

    merged = template.fields_in_group("Импульсные и трубные проводки")

    # После объединения дубли (материал, герметичность, опоры, уклоны,
    # дефекты) остались в одном экземпляре.
    names = [field.name for field in merged]
    assert len(names) == len(set(names))
    assert len(merged) < 26


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


# --------------------------------------------------- электроустановки и ТСО


def test_electrical_template_exists() -> None:
    assert ELECTRICAL_TEMPLATE.is_file()


def test_electrical_template_structure() -> None:
    template = TemplateLoader().load(ELECTRICAL_TEMPLATE)

    assert template.groups == ELECTRICAL_GROUPS
    assert len(template.fields) >= 100


def test_electrical_template_covers_required_areas() -> None:
    template = TemplateLoader().load(ELECTRICAL_TEMPLATE)
    joined = " ".join(template.groups).lower()

    for expected in ("заземлен", "кабельн", "щит", "электродвигател", "освещен", "молни"):
        assert expected in joined, f"нет группы про «{expected}»"


def test_electrical_template_references_normative_documents() -> None:
    template = TemplateLoader().load(ELECTRICAL_TEMPLATE)
    joined = " ".join(field.description for field in template.fields).lower()

    for document in ("пуэ", "приказ минэнерго", "приказ минтруда", "гост"):
        assert document in joined, f"нет ссылки на {document}"


def test_electrical_template_has_test_protocols() -> None:
    """Проверка электрики без измерений бессмысленна: должны быть поля
    для сопротивления изоляции, заземления и петли «фаза-нуль»."""

    template = TemplateLoader().load(ELECTRICAL_TEMPLATE)
    names = {field.name for field in template.fields}

    for field_name in (
        "insulation_value",
        "grounding_value",
        "loop_value",
        "insulation_norm",
        "grounding_norm",
    ):
        assert field_name in names, f"нет поля {field_name}"


def test_security_template_exists() -> None:
    assert SECURITY_TEMPLATE.is_file()


def test_security_template_structure() -> None:
    template = TemplateLoader().load(SECURITY_TEMPLATE)

    assert template.groups == SECURITY_GROUPS
    assert len(template.fields) >= 100


def test_security_template_covers_required_areas() -> None:
    template = TemplateLoader().load(SECURITY_TEMPLATE)
    joined = " ".join(template.groups).lower()

    for expected in ("укреплённ", "сигнализац", "телевидени", "доступ", "электропитание"):
        assert expected in joined, f"нет группы про «{expected}»"


def test_security_template_references_normative_documents() -> None:
    template = TemplateLoader().load(SECURITY_TEMPLATE)
    joined = " ".join(field.description for field in template.fields).lower()

    for document in ("256-фз", "458", "рд 78.36.003-2002", "гост р"):
        assert document in joined, f"нет ссылки на {document}"


def test_security_template_has_law_enforcement_passport() -> None:
    """Паспорт безопасности объекта ТЭК предусмотрен статьёй 8 ФЗ-256."""

    template = TemplateLoader().load(SECURITY_TEMPLATE)
    names = {field.name for field in template.fields}

    assert "safety_passport" in names


@pytest.mark.parametrize(
    "path",
    [KIP_TEMPLATE, ELECTRICAL_TEMPLATE, SECURITY_TEMPLATE],
    ids=lambda item: item.name,
)
def test_working_templates_have_no_required_checkboxes(path: Path) -> None:
    """Обязательный флажок не даёт зафиксировать несоответствие и завершить
    проверку, поэтому оценочные поля в рабочих шаблонах — списки."""

    template = TemplateLoader().load(path)

    for field in template.required_fields:
        assert field.type is not FieldType.CHECKBOX, f"{path.name}: «{field.name}» — флажок"


@pytest.mark.parametrize(
    "path",
    [KIP_TEMPLATE, ELECTRICAL_TEMPLATE, SECURITY_TEMPLATE],
    ids=lambda item: item.name,
)
def test_working_templates_use_verdict_options(path: Path) -> None:
    """Ответы должны позволять зафиксировать и соответствие, и нарушение."""

    template = TemplateLoader().load(path)
    dropdowns = [field for field in template.fields if field.type is FieldType.DROPDOWN]

    with_verdict = [
        field
        for field in dropdowns
        if "Не соответствует" in field.options or "Неисправно" in field.options
    ]

    assert len(with_verdict) >= len(dropdowns) * 0.5
