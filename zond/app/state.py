from dataclasses import dataclass, field

from zond.models.field import Field
from zond.models.inspection import Inspection
from zond.models.template import Template


@dataclass(slots=True)
class ZondState:
    """ Состояние текущего сеанса приложения. """

    template: Template | None = None

    inspection: Inspection | None = None

    current_group_index: int = 0

    current_field_index: int = 0

    answers: dict[str, object] = field(default_factory=dict)

    is_modified: bool = False

    @property
    def has_template(self) -> bool:
        return self.template is not None


    @property
    def has_inspection(self) -> bool:
        return self.inspection is not None


    @property
    def total_groups(self) -> int:
        """ Количество групп полей в текущем шаблоне. """

        if not self.template:
            return 0

        groups = {
            field.group
            for field in self.template.fields
        }

        return len(groups)

    @property
    def groups(self) -> list[str]:
        """Список групп полей текущего шаблона."""

        if not self.template:
            return []

        return list(
            dict.fromkeys(
                field.group
                for field in self.template.fields
            )
        )


    def next_group(self) -> bool:
        """ Переход к следующей группе. """

        if self.current_group_index < self.total_groups - 1:
            self.current_group_index += 1
            return True
        return False


    def previous_group(self) -> None:
        """ Возврат к предыдущей группе. """

        if self.current_group_index > 0:
            self.current_group_index -= 1


    def reset(self) -> None:
        """ Полный сброс состояния. """

        self.template = None
        self.inspection = None
        self.current_group_index = 0
        #self.current_field_index = 0
        self.answers.clear()
        self.is_modified = False

    @property
    def current_group(self) -> str | None:

        if not self.groups:
            return None

        return self.groups[
            self.current_group_index
        ]

    @property
    def current_fields(self) -> list[Field]:

        if not self.template:
            return []

        group = self.current_group

        return [
            field
            for field in self.template.fields
            if field.group == group
        ]

    @property
    def current_field(self):

        fields = self.current_fields

        if self.current_field_index >= len(fields):
            return None

        return fields[self.current_field_index]

    def set_answer(
            self,
            name: str,
            value: object
    ):
        self.answers[name] = value
        self.is_modified = True
