"""Результат проверки одного поля."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from zond.models.field import Field, FieldType


@dataclass(slots=True)
class InspectionItem:
    """Значение и служебные пометки для одного поля проверки."""

    field: Field
    value: object | None = None
    comment: str = ""
    is_checked: bool = False

    @property
    def is_empty(self) -> bool:
        """Считается ли поле незаполненным.

        Для флажка «пусто» — это ``False``, для остальных типов — ``None``
        или пустая строка.
        """

        if isinstance(self.value, bool):
            return not self.value

        return self.value is None or str(self.value).strip() == ""

    @property
    def missing_required(self) -> bool:
        return self.field.required and self.is_empty

    def display_value(self) -> str:
        """Значение в виде строки для отчёта и списков.

        Даты и время показываются в привычном виде, хотя внутри хранятся в
        ISO-формате.
        """

        if self.is_empty:
            return "—"

        if isinstance(self.value, bool):
            return "Да" if self.value else "Нет"

        text = str(self.value)

        if self.field.type in (FieldType.DATE, FieldType.TIME):
            return _humanize_temporal(self.field.type, text)

        return text

    def to_dict(self) -> dict:
        return {
            "field": self.field.name,
            "value": self.value,
            "comment": self.comment,
            "is_checked": self.is_checked,
        }

    @classmethod
    def from_dict(cls, data: dict, field: Field) -> InspectionItem:
        value = data.get("value")

        # JSON не различает типы строго, поэтому для флажка приводим значение
        # к bool, а для остальных типов — к строке.
        if field.type.value == "checkbox":
            value = bool(value)
        elif value is not None:
            value = str(value)

        return cls(
            field=field,
            value=value,
            comment=str(data.get("comment") or ""),
            is_checked=bool(data.get("is_checked", False)),
        )


def _humanize_temporal(field_type: FieldType, text: str) -> str:
    """Показать ISO-дату/время в привычном формате, если получится."""

    try:
        if field_type is FieldType.DATE:
            return datetime.strptime(text, "%Y-%m-%d").strftime("%d.%m.%Y")

        if field_type is FieldType.TIME:
            return datetime.strptime(text, "%H:%M").strftime("%H:%M")
    except ValueError:
        return text

    return text
