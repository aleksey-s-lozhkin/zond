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

    #: Значение из предыдущей проверки того же объекта. Заполняется только при
    #: повторной проверке и только если в прошлый раз поле было заполнено:
    #: ``None`` означает, что переносить было нечего.
    previous_value: object | None = None

    #: Состояние замечания, выявленного в прошлый раз: устранено, не устранено
    #: или не проверялось. Пусто у полей, которые замечаниями не были.
    resolution: str = ""

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

    @property
    def has_previous(self) -> bool:
        """Было ли что переносить из предыдущей проверки.

        Пустая строка значением не считается: переносить из неё нечего.
        Для флажка значение ``False`` — это ответ, а не пустота.
        """

        if self.previous_value is None:
            return False

        if isinstance(self.previous_value, bool):
            return True

        return str(self.previous_value).strip() != ""

    @property
    def needs_resolution(self) -> bool:
        """Ждёт ли замечание решения проверяющего."""

        return self.has_previous and not self.resolution

    def to_dict(self) -> dict:
        payload = {
            "field": self.field.name,
            "value": self.value,
            "comment": self.comment,
            "is_checked": self.is_checked,
        }

        # Ключи повторной проверки пишем только когда они есть: файлы обычных
        # проверок не должны обрастать полями с пустыми значениями.
        if self.previous_value is not None:
            payload["previous_value"] = self.previous_value

        if self.resolution:
            payload["resolution"] = self.resolution

        return payload

    @classmethod
    def from_dict(cls, data: dict, field: Field) -> InspectionItem:
        return cls(
            field=field,
            value=_coerce(field, data.get("value")),
            comment=str(data.get("comment") or ""),
            is_checked=bool(data.get("is_checked", False)),
            previous_value=_coerce(field, data.get("previous_value")),
            resolution=str(data.get("resolution") or ""),
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


def _coerce(field: Field, value: object) -> object | None:
    """Привести значение из JSON к типу поля.

    JSON не различает типы строго, поэтому для флажка значение приводится к
    ``bool``, а для остальных типов — к строке.
    """

    if value is None:
        return None

    if field.type.value == "checkbox":
        return bool(value)

    return str(value)
