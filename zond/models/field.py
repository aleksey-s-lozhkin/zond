from dataclasses import dataclass, field
from enum import StrEnum


class FieldType(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    TEXTAREA = "textarea"


@dataclass(slots=True, frozen=True)
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
