"""Создание новой проверки по шаблону."""

from __future__ import annotations

from zond.models.inspection import Inspection
from zond.models.inspection_item import InspectionItem
from zond.models.template import Template


class InspectionFactory:
    """Создаёт новую проверку по шаблону."""

    @staticmethod
    def create(
        template: Template,
        object_name: str = "",
        executor: str = "",
    ) -> Inspection:
        inspection = Inspection(
            template=template,
            object_name=object_name,
            executor=executor,
        )

        inspection.items = [InspectionItem(field=item) for item in template.fields]

        return inspection
