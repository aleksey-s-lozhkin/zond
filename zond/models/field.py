"""Модель поля шаблона проверки."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FieldType(StrEnum):
    """Поддерживаемые типы полей."""

    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    TEXTAREA = "textarea"


#: Человекочитаемые названия типов — для сообщений об ошибках и отчёта.
FIELD_TYPE_TITLES: dict[FieldType, str] = {
    FieldType.TEXT: "текст",
    FieldType.NUMBER: "число",
    FieldType.DATE: "дата",
    FieldType.TIME: "время",
    FieldType.DROPDOWN: "список",
    FieldType.CHECKBOX: "флажок",
    FieldType.TEXTAREA: "многострочный текст",
}


@dataclass(frozen=True, slots=True)
class Field:
    """Описание одного поля шаблона проверки."""

    order: int = 0
    name: str = ""
    label: str = ""
    type: FieldType = FieldType.TEXT
    group: str = "Общие сведения"
    required: bool = False
    options: tuple[str, ...] = ()
    placeholder: str = ""
    description: str = ""
    unit: str = ""

    @property
    def title(self) -> str:
        """Подпись поля; если не задана — машинное имя."""

        return self.label or self.name

    @property
    def type_title(self) -> str:
        return FIELD_TYPE_TITLES.get(self.type, self.type.value)

    def to_dict(self) -> dict:
        """Снимок поля для самодостаточного JSON проверки."""

        return {
            "order": self.order,
            "name": self.name,
            "label": self.label,
            "type": self.type.value,
            "group": self.group,
            "required": self.required,
            "options": list(self.options),
            "placeholder": self.placeholder,
            "description": self.description,
            "unit": self.unit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Field:
        """Восстановить поле из снимка.

        Неизвестный тип поля не считается фатальным: данные важнее, поэтому
        поле деградирует до текстового.
        """

        raw_type = str(data.get("type", FieldType.TEXT.value)).strip().lower()

        try:
            field_type = FieldType(raw_type)
        except ValueError:
            field_type = FieldType.TEXT

        raw_options = data.get("options") or ()
        if isinstance(raw_options, str):
            raw_options = (raw_options,)

        return cls(
            order=int(data.get("order") or 0),
            name=str(data.get("name") or ""),
            label=str(data.get("label") or ""),
            type=field_type,
            group=str(data.get("group") or "Общие сведения"),
            required=bool(data.get("required", False)),
            options=tuple(str(option) for option in raw_options),
            placeholder=str(data.get("placeholder") or ""),
            description=str(data.get("description") or ""),
            unit=str(data.get("unit") or ""),
        )
