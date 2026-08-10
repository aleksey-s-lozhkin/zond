from zond.models.inspection import Inspection
from zond.models.inspection_item import InspectionItem
from zond.models.template import Template


class InspectionFactory:
    """Создает новую проверку по шаблону."""

    @staticmethod
    def create(template: Template) -> Inspection:

        inspection = Inspection(
            template=template,
        )

        for field in template.fields:

            inspection.items.append(
                InspectionItem(
                    field=field,
                )
            )

        return inspection
