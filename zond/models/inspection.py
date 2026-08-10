from dataclasses import dataclass, field
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

        return {
            "format_version": 1,
            "template": self.template.name,
            "object_name": self.object_name,
            "inspector": self.inspector,
            "started_at": self.started_at.isoformat(),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at
                else None
            ),
            "items": [
                {
                    "field": item.field.name,
                    "value": item.value,
                    "comment": item.comment,
                    "is_checked": item.is_checked,
                }
                for item in self.items
            ],
        }
