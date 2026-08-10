from dataclasses import dataclass, field, asdict
from datetime import datetime

from .inspection_item import InspectionItem
from .template import Template


@dataclass(slots=True)
class Inspection:
    """ Конкретная проверка оборудования. """

    template: Template

    object_name: str = ""

    inspector: str = ""

    started_at: datetime = field(default_factory=datetime.now)

    finished_at: datetime | None = None

    items: list[InspectionItem] = field(default_factory=list)

    def get_item(self, field_name: str) -> InspectionItem | None:
        """Возвращает результат проверки по имени поля."""

        for item in self.items:
            if item.field.name == field_name:
                return item

        return None

    def to_dict(self) -> dict:
        """Преобразовать проверку в словарь."""

        return asdict(self)
