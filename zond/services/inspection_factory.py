"""Создание новой проверки по шаблону."""

from __future__ import annotations

from zond.models.field import FieldType
from zond.models.inspection import Inspection
from zond.models.inspection_item import InspectionItem
from zond.models.template import Template
from zond.models.verdict import is_problem


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

    @staticmethod
    def repeat(
        previous: Inspection,
        template: Template,
        object_name: str = "",
        executor: str = "",
    ) -> Inspection:
        """Создать проверку на основе предыдущей.

        Значения переносятся по машинным именам полей: между выездами шаблон
        мог измениться. Поэтому поле, которого нет в новом шаблоне,
        пропускается, а несовместимое с новым типом значение не подставляется —
        но прежнее значение сохраняется в любом случае, чтобы проверяющий видел,
        что было в прошлый раз.
        """

        inspection = InspectionFactory.create(
            template,
            object_name or previous.object_name,
            executor or previous.executor,
        )

        inspection.previous_inspection_id = previous.inspection_id

        previous_by_name = {item.field.name: item for item in previous.items}

        for item in inspection.items:
            old = previous_by_name.get(item.field.name)

            if old is None or old.is_empty:
                continue

            item.previous_value = old.value

            if _accepts(item.field, old.value):
                item.value = old.value

            # Замечание прошлого выезда проверяющий закрывает отдельно:
            # значение могло остаться прежним, а неисправность — быть
            # устранённой.
            if is_problem(old.value):
                item.resolution = ""

        _note_missing_fields(inspection, previous_by_name)

        return inspection


def _note_missing_fields(
    inspection: Inspection,
    previous_by_name: dict[str, InspectionItem],
) -> None:
    """Предупредить, если замечания прошлого выезда некуда переносить.

    Поле могли убрать из шаблона. Тогда замечание не показать и не закрыть, и
    об этом честнее сказать сразу, чем молча его потерять.
    """

    current = {item.field.name for item in inspection.items}

    lost = [
        item
        for name, item in previous_by_name.items()
        if name not in current and is_problem(item.value)
    ]

    if not lost:
        return

    titles = ", ".join(item.field.title for item in lost[:5])
    tail = " и другие" if len(lost) > 5 else ""

    inspection.template.warnings.append(
        f"В шаблоне нет полей с замечаниями прошлой проверки: {titles}{tail}. Они не перенесены."
    )


def _accepts(field, value: object) -> bool:
    """Подходит ли прежнее значение полю с текущим типом.

    Шаблон между выездами могли поправить: вариант списка переименовали,
    числовое поле сделали текстовым. Подставлять значение, которого больше нет
    среди вариантов, нельзя — форма покажет пустое поле с чужой подписью.
    """

    if field.type is FieldType.CHECKBOX:
        return isinstance(value, bool)

    if field.type is FieldType.DROPDOWN:
        return str(value) in field.options

    if field.type is FieldType.NUMBER:
        return _is_number(value)

    return True


def _is_number(value: object) -> bool:
    """Похоже ли значение на число: принимает и запятую как разделитель."""

    try:
        float(str(value).replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        return False

    return True
