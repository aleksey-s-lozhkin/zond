"""Экран разбора замечаний, выявленных в прошлый раз.

На повторном выезде главное — не заполнить форму заново, а понять, что
изменилось с прошлого раза. Поэтому прежние замечания выносятся отдельным
шагом: по каждому проверяющий отмечает состояние, и это попадает в протокол.

Экран стоит перед формой намеренно. Если показать замечания где-то внутри
формы, их пропустят, а протокол потеряет связь с прошлым выездом.
"""

from __future__ import annotations

import flet as ft

from zond.models.verdict import RESOLUTION_OPTIONS
from zond.ui.colors import AppColors
from zond.ui.components.buttons import PrimaryButton, SecondaryButton
from zond.ui.components.cards import EmptyState, InfoRow, SectionCard
from zond.ui.components.headers import ScreenHeader
from zond.ui.components.layout import ActionBar, ScreenBody
from zond.ui.design import FontSize, Space
from zond.ui.icons import AppIcons
from zond.ui.screens.base_screen import AppScreen


class DefectsScreen(AppScreen):
    """Разбор замечаний прошлой проверки."""

    def __init__(self, app) -> None:
        self.selectors: dict[str, ft.Dropdown] = {}
        self.counter: ft.Text | None = None
        self.continue_button: PrimaryButton | None = None

        super().__init__(app)

    def compose(self) -> ft.Control:
        inspection = self.app.state.inspection

        if inspection is None:
            return EmptyState(
                "Проверка не начата",
                "Вернитесь на стартовый экран и выберите шаблон.",
                icon=AppIcons.WARNING,
            )

        defects = inspection.pending_resolutions

        if not defects:
            return EmptyState(
                "Замечаний нет",
                "В прошлый раз несоответствий не выявлялось.",
                icon=AppIcons.SUCCESS,
            )

        return ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ScreenHeader(
                    "Замечания прошлой проверки",
                    f"Выявлено в прошлый раз: {len(defects)}",
                    on_back=self._go_back,
                ),
                ScreenBody(
                    self._counter_text(),
                    *[self._defect_card(item) for item in defects],
                    bottom=Space.XL,
                ),
                self._action_bar(),
            ],
        )

    # --------------------------------------------------------------- блоки

    def _counter_text(self) -> ft.Control:
        self.counter = ft.Text(
            self._counter_label(),
            size=FontSize.CAPTION,
            color=AppColors.TEXT_SECONDARY,
        )

        return self.counter

    def _defect_card(self, item) -> ft.Control:
        selector = ft.Dropdown(
            label="Состояние сейчас",
            options=[ft.dropdown.Option(option) for option in RESOLUTION_OPTIONS],
            value=item.resolution or None,
            border_radius=12,
            filled=True,
            fill_color=AppColors.SURFACE,
            dense=True,
            on_select=lambda event, field=item.field.name: self._choose(field, event),
        )

        self.selectors[item.field.name] = selector

        return SectionCard(
            InfoRow(
                "В прошлый раз",
                item.display_previous(),
                value_color=AppColors.ERROR,
            ),
            selector,
            title=item.field.title,
            subtitle=f"Шаг: {item.field.group}",
            icon=AppIcons.WARNING,
        )

    def _action_bar(self) -> ft.Control:
        self.continue_button = PrimaryButton(
            "Продолжить",
            icon=AppIcons.NEXT,
            on_click=self._continue,
            expand=True,
            disabled=self._remaining() > 0,
        )

        return ActionBar(
            SecondaryButton(
                "Назад",
                icon=AppIcons.BACK,
                on_click=self._go_back,
                expand=True,
            ),
            self.continue_button,
        )

    # ----------------------------------------------------------- обработчики

    def _remaining(self) -> int:
        inspection = self.app.state.inspection

        if inspection is None:
            return 0

        return len(inspection.pending_resolutions)

    def _counter_label(self) -> str:
        remaining = self._remaining()

        if not remaining:
            return "Все замечания разобраны."

        return f"Осталось разобрать: {remaining}"

    def _choose(self, field_name: str, event) -> None:
        inspection = self.app.state.inspection

        if inspection is None:
            return

        item = inspection.get_item(field_name)

        if item is None:
            return

        item.resolution = str(event.control.value or "")

        if self.counter is not None:
            self.counter.value = self._counter_label()

        if self.continue_button is not None:
            self.continue_button.disabled = self._remaining() > 0

        self.safe_update()

    def _go_back(self, event) -> None:
        self.app.navigator.back()

    def _continue(self, event) -> None:
        self.app.finish_defect_review()
