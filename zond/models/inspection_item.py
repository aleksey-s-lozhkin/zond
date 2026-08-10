from dataclasses import dataclass

from .field import Field


@dataclass(slots=True)
class InspectionItem:
    """ Результат проверки одного поля. """

    field: Field

    value: object | None = None

    comment: str = ""

    is_checked: bool = False