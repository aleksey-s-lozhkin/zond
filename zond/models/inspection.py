"""Модель проверки оборудования."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from zond.models.inspection_item import InspectionItem
from zond.models.template import Template
from zond.services.errors import StorageError

#: Текущая версия формата файла проверки.
FORMAT_VERSION = 2

#: Группа, в которую попадают поля при миграции файлов версии 1.
LEGACY_GROUP = "Без группы"


def utcnow() -> datetime:
    """Текущее время в UTC с таймзоной.

    Протокол проверки — документ, поэтому время хранится timezone-aware:
    наивные метки не позволяют доказать, в каком часовом поясе проводилась
    проверка.
    """

    return datetime.now(UTC)


def parse_datetime(raw: object) -> datetime | None:
    """Разобрать ISO-метку времени; наивные значения считаем UTC."""

    if not raw:
        return None

    try:
        parsed = datetime.fromisoformat(str(raw))
    except ValueError as error:
        raise StorageError(f"Некорректная метка времени: {raw!r}") from error

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed


def format_datetime(value: datetime | None, fmt: str = "%d.%m.%Y %H:%M") -> str:
    """Локальное представление времени для интерфейса и отчёта."""

    if value is None:
        return "—"

    if value.tzinfo is not None:
        value = value.astimezone()

    return value.strftime(fmt)


@dataclass(slots=True)
class Inspection:
    """Конкретная проверка оборудования."""

    template: Template
    inspection_id: str = field(default_factory=lambda: uuid4().hex)
    object_name: str = ""
    inspector: str = ""
    started_at: datetime = field(default_factory=utcnow)
    finished_at: datetime | None = None
    items: list[InspectionItem] = field(default_factory=list)

    # ------------------------------------------------------------------ поиск

    def get_item(self, field_name: str) -> InspectionItem | None:
        """Возвращает результат проверки по машинному имени поля."""

        for item in self.items:
            if item.field.name == field_name:
                return item

        return None

    def field_value(self, field_name: str) -> object | None:
        """Значение поля по имени (``None``, если поля нет)."""

        item = self.get_item(field_name)
        return None if item is None else item.value

    def set_value(self, field_name: str, value: object) -> InspectionItem | None:
        """Записать значение поля и отметить его как проверенное."""

        item = self.get_item(field_name)

        if item is None:
            return None

        item.value = value
        item.is_checked = not item.is_empty

        return item

    # --------------------------------------------------------------- сводки

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def answered_count(self) -> int:
        return sum(1 for item in self.items if not item.is_empty)

    @property
    def missing_required(self) -> list[InspectionItem]:
        return [item for item in self.items if item.missing_required]

    @property
    def is_ready(self) -> bool:
        """Все ли обязательные поля заполнены."""

        return not self.missing_required

    @property
    def progress(self) -> float:
        if not self.items:
            return 0.0

        return self.answered_count / len(self.items)

    @property
    def is_finished(self) -> bool:
        return self.finished_at is not None

    @property
    def title(self) -> str:
        """Название проверки для списков и отчёта."""

        if self.object_name:
            return self.object_name

        object_item = self.get_item("object_number")

        if object_item is not None and not object_item.is_empty:
            return object_item.display_value()

        return self.template.name

    def items_in_group(self, group: str) -> list[InspectionItem]:
        return [item for item in self.items if item.field.group == group]

    def mark_finished(self, moment: datetime | None = None) -> None:
        """Зафиксировать завершение проверки."""

        self.finished_at = moment or utcnow()

    # ----------------------------------------------------------- сериализация

    def to_dict(self) -> dict:
        """Полный снимок проверки.

        Формат самодостаточен: помимо результатов сохраняется снимок полей
        шаблона (тип, группа, подпись, варианты), поэтому отчёт и продолжение
        проверки возможны без исходного CSV.
        """

        return {
            "format_version": FORMAT_VERSION,
            "inspection_id": self.inspection_id,
            "object_name": self.object_name,
            "inspector": self.inspector,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "template": self.template.to_dict(),
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Inspection:
        """Восстановить проверку из словаря, при необходимости мигрируя формат."""

        if not isinstance(data, dict):
            raise StorageError("Ожидался объект JSON с описанием проверки")

        version = int(data.get("format_version") or 1)

        if version > FORMAT_VERSION:
            raise StorageError(
                f"Файл создан более новой версией приложения "
                f"(формат {version}, поддерживается до {FORMAT_VERSION})"
            )

        template = _template_from_payload(data, version)
        fields_by_name = {item.name: item for item in template.fields}

        items: list[InspectionItem] = []

        for raw_item in data.get("items") or []:
            if not isinstance(raw_item, dict):
                continue

            field_name = str(raw_item.get("field") or "")
            field = fields_by_name.get(field_name)

            if field is None:
                continue

            items.append(InspectionItem.from_dict(raw_item, field))

        # Поля из снимка шаблона, для которых не нашлось результата, добавляем
        # пустыми — иначе пользователь потеряет часть формы при возобновлении.
        known = {item.field.name for item in items}
        for field in template.fields:
            if field.name not in known:
                items.append(InspectionItem(field=field))

        inspection = cls(
            template=template,
            inspection_id=str(data.get("inspection_id") or uuid4().hex),
            object_name=str(data.get("object_name") or ""),
            inspector=str(data.get("inspector") or ""),
            started_at=parse_datetime(data.get("started_at")) or utcnow(),
            finished_at=parse_datetime(data.get("finished_at")),
            items=items,
        )

        if version < FORMAT_VERSION:
            inspection.template.warnings.append(
                f"Файл формата {version} загружен с миграцией до {FORMAT_VERSION}: "
                "названия полей и группировка восстановлены приблизительно."
            )

        return inspection


def _template_from_payload(data: dict, version: int) -> Template:
    """Собрать шаблон из полезной нагрузки, поддерживая формат версии 1."""

    raw_template = data.get("template")

    if version >= 2 and isinstance(raw_template, dict):
        return Template.from_dict(raw_template)

    # ---- формат 1: template — строка, снимка полей нет -------------------
    name = raw_template if isinstance(raw_template, str) and raw_template else "Без названия"

    field_names: list[str] = []
    for raw_item in data.get("items") or []:
        if isinstance(raw_item, dict) and raw_item.get("field"):
            field_name = str(raw_item["field"])
            if field_name not in field_names:
                field_names.append(field_name)

    if not field_names:
        raise StorageError("В файле нет ни описания полей, ни результатов проверки")

    # Импорт внутри функции: Field нужен только для миграции.
    from zond.models.field import Field, FieldType

    fields = [
        Field(
            order=index * 10,
            name=field_name,
            label=field_name,
            type=FieldType.TEXT,
            group=LEGACY_GROUP,
        )
        for index, field_name in enumerate(field_names)
    ]

    return Template(name=name, version="1.0", fields=fields)
