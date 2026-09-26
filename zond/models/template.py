"""Модель шаблона проверки."""

from __future__ import annotations

from dataclasses import dataclass, field

from zond.models.field import Field


@dataclass(slots=True)
class Template:
    """Шаблон проверки: упорядоченный список полей с группировкой."""

    name: str
    version: str = "1.0"
    fields: list[Field] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def groups(self) -> list[str]:
        """Названия групп в порядке первого появления."""

        return list(dict.fromkeys(item.group for item in self.fields))

    @property
    def total_groups(self) -> int:
        return len(self.groups)

    @property
    def required_fields(self) -> list[Field]:
        return [item for item in self.fields if item.required]

    def fields_in_group(self, group: str) -> list[Field]:
        """Поля указанной группы в порядке следования в шаблоне."""

        return [item for item in self.fields if item.group == group]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "warnings": list(self.warnings),
            "fields": [item.to_dict() for item in self.fields],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Template:
        return cls(
            name=str(data.get("name") or "Без названия"),
            version=str(data.get("version") or "1.0"),
            warnings=[str(item) for item in (data.get("warnings") or [])],
            fields=[Field.from_dict(item) for item in (data.get("fields") or [])],
        )
