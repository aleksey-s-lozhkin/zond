"""Состояние текущего сеанса приложения."""

from __future__ import annotations

from dataclasses import dataclass

from zond.models.field import Field
from zond.models.inspection import Inspection
from zond.models.template import Template


@dataclass(slots=True)
class ZondState:
    """Данные текущего сеанса: активный шаблон и проверка."""

    template: Template | None = None
    inspection: Inspection | None = None
    current_group_index: int = 0
    is_modified: bool = False

    # ------------------------------------------------------- признаки

    @property
    def has_template(self) -> bool:
        return self.template is not None

    @property
    def has_inspection(self) -> bool:
        return self.inspection is not None

    @property
    def groups(self) -> list[str]:
        """Группы полей текущего шаблона."""

        return self.template.groups if self.template else []

    @property
    def total_groups(self) -> int:
        return len(self.groups)

    @property
    def is_finished(self) -> bool:
        """Пройдены ли все группы."""

        return self.total_groups == 0 or self.current_group_index >= self.total_groups

    @property
    def is_first_group(self) -> bool:
        return self.current_group_index <= 0

    @property
    def is_last_group(self) -> bool:
        return self.total_groups > 0 and self.current_group_index >= self.total_groups - 1

    @property
    def current_group(self) -> str | None:
        if self.is_finished or not self.groups:
            return None

        return self.groups[self.current_group_index]

    @property
    def current_fields(self) -> list[Field]:
        """Поля текущей шага-группы."""

        if self.is_finished or self.template is None:
            return []

        group = self.current_group

        if group is None:
            return []

        return self.template.fields_in_group(group)

    # ---------------------------------------------------------- прогресс

    @property
    def answered_fields(self) -> int:
        return self.inspection.answered_count if self.inspection else 0

    @property
    def total_fields(self) -> int:
        return self.inspection.total_items if self.inspection else 0

    # ---------------------------------------------------------- действия

    def set_template(self, template: Template) -> None:
        """Назначить шаблон, сбросив прогресс предыдущего сеанса."""

        self.reset()
        self.template = template

    def set_inspection(self, inspection: Inspection) -> None:
        """Сделать проверку активной."""

        self.inspection = inspection
        self.template = inspection.template
        self.current_group_index = 0
        self.is_modified = False

    def goto_first_incomplete_group(self) -> None:
        """Перейти к первой группе, где есть незаполненные обязательные поля.

        Используется при возобновлении проверки, чтобы пользователь попал на
        то место, где остановился, а не в начало формы.
        """

        self.current_group_index = 0

        if self.inspection is None:
            return

        groups = self.groups

        for index, group in enumerate(groups):
            items = self.inspection.items_in_group(group)

            if any(item.missing_required for item in items):
                self.current_group_index = index
                return

        for index, group in enumerate(groups):
            items = self.inspection.items_in_group(group)

            if any(item.is_empty for item in items):
                self.current_group_index = index
                return

        self.current_group_index = 0

    def next_group(self) -> bool:
        """Перейти к следующей группе. ``False``, если групп больше нет."""

        if self.is_finished:
            return False

        self.current_group_index += 1
        return not self.is_finished

    def previous_group(self) -> bool:
        """Вернуться к предыдущей группе. ``False``, если это первая группа."""

        if self.is_first_group:
            return False

        self.current_group_index -= 1
        return True

    def mark_modified(self) -> None:
        """Отметить, что данные проверки изменились после последнего сохранения."""

        self.is_modified = True

    def mark_saved(self) -> None:
        self.is_modified = False

    def reset(self) -> None:
        """Полный сброс состояния сеанса."""

        self.template = None
        self.inspection = None
        self.current_group_index = 0
        self.is_modified = False
