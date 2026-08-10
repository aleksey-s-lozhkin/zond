from dataclasses import dataclass, field

from .field import Field


@dataclass(slots=True)
class Template:
    """ Шаблон проверки. """

    name: str

    version: str = "1.0"

    fields: list[Field] = field(default_factory=list)