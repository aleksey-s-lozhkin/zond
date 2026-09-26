"""Сборка CSV-шаблонов проверок из описания в коде.

Шаблоны держим генераторами, а не правкой CSV руками: структура видна в
diff, а проверки уникальности имён, наличия вариантов у списков и
допустимости символов выполняются автоматически.

Разделитель CSV — точка с запятой: в русских текстах часто встречаются
запятые, а варианты списков разделяются вертикальной чертой.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

#: Разделитель колонок CSV.
CSV_DELIMITER = ";"

#: Разделитель вариантов внутри колонки options.
OPTION_SEPARATOR = "|"

#: Порядок и состав колонок CSV.
CSV_COLUMNS = (
    "order",
    "name",
    "label",
    "type",
    "group",
    "required",
    "options",
    "placeholder",
    "description",
    "unit",
)

#: Шаг нумерации order — оставляет место для вставки полей.
ORDER_STEP = 10

#: Допустимые типы полей — должны совпадать с zond.models.field.FieldType.
FIELD_TYPES = ("text", "number", "date", "time", "dropdown", "checkbox", "textarea")

#: Символ, недопустимый в значениях при разделителе «;».
FORBIDDEN = ";"


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """Описание одного поля шаблона.

    Поля именованные: позиционные кортежи приводили к ошибкам при
    перестановке групп и добавлении новых колонок.
    """

    name: str
    label: str
    type: str
    group: str
    required: bool = False
    options: tuple[str, ...] = ()
    placeholder: str = ""
    description: str = ""
    unit: str = ""

    def validate(self) -> None:
        if self.type not in FIELD_TYPES:
            raise ValueError(f"{self.name!r}: неизвестный тип {self.type!r}")

        if not self.name:
            raise ValueError(f"{self.label!r}: не задано машинное имя поля")

        if self.type == "dropdown" and not self.options:
            raise ValueError(f"{self.name!r}: для списка не заданы варианты")

        if self.type != "dropdown" and self.options:
            raise ValueError(f"{self.name!r}: варианты заданы для типа {self.type!r}")

        joined = "".join((self.label, self.placeholder, self.description, self.unit, *self.options))

        if FORBIDDEN in joined:
            raise ValueError(
                f"{self.name!r}: символ {FORBIDDEN!r} недопустим в значениях "
                "(он разделяет колонки CSV)"
            )


def build_template(
    path: str | Path,
    groups: list[str],
    fields: list[FieldSpec],
) -> None:
    """Проверить описание и записать CSV-шаблон."""

    target = Path(path)

    seen_names: set[str] = set()
    known_groups = set(groups)

    for spec in fields:
        spec.validate()

        if spec.name in seen_names:
            raise ValueError(f"дублирующееся машинное имя поля: {spec.name!r}")

        seen_names.add(spec.name)

        if spec.group not in known_groups:
            raise ValueError(f"{spec.name!r}: группа {spec.group!r} не объявлена в GROUPS")

    counted = Counter(spec.group for spec in fields)
    empty_groups = [name for name in groups if not counted[name]]

    if empty_groups:
        raise ValueError(f"в группах нет полей: {', '.join(empty_groups)}")

    rows = [
        {
            "order": (index + 1) * ORDER_STEP,
            "name": spec.name,
            "label": spec.label,
            "type": spec.type,
            "group": spec.group,
            "required": "true" if spec.required else "false",
            "options": OPTION_SEPARATOR.join(spec.options),
            "placeholder": spec.placeholder,
            "description": spec.description,
            "unit": spec.unit,
        }
        for index, spec in enumerate(fields)
    ]

    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(CSV_COLUMNS),
            delimiter=CSV_DELIMITER,
            quoting=csv.QUOTE_MINIMAL,
            # В репозитории принят LF (.gitattributes), а csv.writer по
            # умолчанию пишет CRLF.
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    required = sum(1 for spec in fields if spec.required)

    print(f"Записано: {target}")
    print(f"Полей: {len(rows)}, обязательных: {required}, групп: {len(groups)}")
    for name in groups:
        print(f"  {counted[name]:3d}  {name}")
