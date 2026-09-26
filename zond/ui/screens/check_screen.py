"""Экран подтверждения загруженного шаблона."""

from __future__ import annotations

import flet as ft

from zond.ui.colors import AppColors
from zond.ui.components.buttons import PrimaryButton, SecondaryButton
from zond.ui.components.cards import EmptyState, InfoRow, SectionCard
from zond.ui.components.headers import ScreenHeader
from zond.ui.components.layout import ActionBar, ScreenBody
from zond.ui.design import FontSize, Space
from zond.ui.icons import AppIcons
from zond.ui.screens.base_screen import AppScreen


class CheckScreen(AppScreen):
    """Показывает состав шаблона и собирает сведения о проверке."""

    def compose(self) -> ft.Control:
        template = self.app.state.template

        if template is None:
            return EmptyState(
                "Шаблон не загружен",
                "Вернитесь на стартовый экран и выберите CSV-файл.",
                icon=AppIcons.WARNING,
            )

        inspection = self.app.state.inspection

        self.object_input = ft.TextField(
            label="Объект (в протоколе)",
            hint_text="Наименование объекта или узла проверки",
            value=inspection.object_name if inspection else "",
            border_radius=12,
            filled=True,
            fill_color=AppColors.SURFACE,
            dense=True,
        )

        self.executor_input = ft.TextField(
            label="Исполнитель (в протоколе)",
            hint_text="ФИО и должность: приборист, слесарь КИПиА, инженер",
            value=inspection.executor if inspection else "",
            border_radius=12,
            filled=True,
            fill_color=AppColors.SURFACE,
            dense=True,
        )

        cards: list[ft.Control] = [
            SectionCard(
                InfoRow("Название", template.name),
                InfoRow("Полей", str(len(template.fields))),
                InfoRow("Групп", str(template.total_groups)),
                InfoRow(
                    "Обязательных",
                    str(len(template.required_fields)),
                    value_color=AppColors.PRIMARY if template.required_fields else AppColors.TEXT,
                ),
                title="Шаблон проверки",
                icon=AppIcons.LIST,
            )
        ]

        if template.warnings:
            cards.append(
                SectionCard(
                    *[
                        ft.Row(
                            spacing=Space.SM,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Icon(AppIcons.WARNING, size=18, color=AppColors.WARNING),
                                ft.Text(
                                    warning,
                                    size=FontSize.CAPTION,
                                    color=AppColors.TEXT,
                                    expand=True,
                                ),
                            ],
                        )
                        for warning in template.warnings
                    ],
                    title="Предупреждения при разборе",
                    subtitle="Шаблон загружен, но проверьте перечисленные места.",
                    icon=AppIcons.WARNING,
                )
            )

        cards.append(
            SectionCard(
                self.object_input,
                self.executor_input,
                title="Сведения о проверке",
                subtitle="Необязательно: попадут в протокол и название проверки.",
                icon=AppIcons.APP,
            )
        )

        cards.append(
            SectionCard(
                *[
                    InfoRow(group, f"{len(template.fields_in_group(group))} пол.")
                    for group in template.groups
                ],
                title="Группы полей",
                icon=AppIcons.LIST,
            )
        )

        return ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ScreenHeader(
                    "Шаблон загружен",
                    description=template.name,
                    on_back=self._go_back,
                ),
                ScreenBody(*cards, top=Space.XS),
                ActionBar(
                    SecondaryButton(
                        "Назад",
                        icon=AppIcons.BACK,
                        on_click=self._go_back,
                        expand=True,
                    ),
                    PrimaryButton(
                        "Начать проверку",
                        icon=AppIcons.PLAY,
                        on_click=self._start,
                        expand=True,
                    ),
                ),
            ],
        )

    # ------------------------------------------------------------- обработчики

    def _go_back(self, event) -> None:
        self.app.navigator.back()

    def _start(self, event) -> None:
        self.app.start_inspection(
            object_name=(self.object_input.value or "").strip(),
            executor=(self.executor_input.value or "").strip(),
        )
