"""Стартовый экран: выбор шаблона, продолжение проверки, история."""

from __future__ import annotations

import flet as ft

from zond.services.sample_templates import available_samples
from zond.ui.colors import AppColors
from zond.ui.components.buttons import GhostButton, PrimaryButton, SecondaryButton
from zond.ui.design import ControlSize, FontSize, Space
from zond.ui.icons import AppIcons
from zond.ui.screens.base_screen import AppScreen

VERSION = "1.0.0"


class UploadScreen(AppScreen):
    """Экран запуска приложения."""

    def compose(self) -> ft.Control:
        stored = self.app.storage.list_stored()
        drafts = sum(1 for entry in stored if entry.is_draft)

        buttons: list[ft.Control] = [
            PrimaryButton(
                "Загрузить шаблон проверки",
                icon=AppIcons.UPLOAD,
                on_click=self._pick_template,
                width=300,
            ),
            SecondaryButton(
                "Открыть сохранённую проверку",
                icon=AppIcons.OPEN,
                on_click=self._pick_inspection,
                width=300,
            ),
        ]

        samples = available_samples()

        if samples:
            buttons.append(
                GhostButton(
                    f"Загрузить образец ({len(samples)})",
                    icon=AppIcons.LIST,
                    on_click=self._choose_sample,
                )
            )

        if stored:
            label = f"История проверок ({len(stored)})"
            if drafts:
                label += f" · черновиков: {drafts}"

            buttons.append(GhostButton(label, icon=AppIcons.HISTORY, on_click=self._open_history))

        content = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=Space.MD,
            controls=[
                ft.Image(
                    src="images/logo.png",
                    width=ControlSize.LOGO,
                    height=ControlSize.LOGO,
                    fit=ft.BoxFit.CONTAIN,
                ),
                ft.Container(height=Space.SM),
                ft.Text(
                    "ЗОНД: ECTS",
                    size=FontSize.HERO,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT,
                ),
                ft.Text(
                    "Система проверки оборудования",
                    size=FontSize.SUBTITLE,
                    color=AppColors.TEXT_SECONDARY,
                ),
                ft.Container(height=Space.LG),
                *buttons,
                ft.Container(height=Space.SM),
                ft.Text(
                    "Шаблон проверки — файл CSV",
                    size=FontSize.CAPTION,
                    color=AppColors.TEXT_SECONDARY,
                ),
            ],
        )

        return ft.Stack(
            expand=True,
            controls=[
                ft.Container(content=content, expand=True, alignment=ft.Alignment(0, 0)),
                ft.Container(
                    content=ft.Text(
                        f"Версия {VERSION}",
                        size=FontSize.CAPTION,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    padding=ft.Padding(left=0, top=0, right=0, bottom=Space.MD),
                    alignment=ft.Alignment(0, 1),
                    ignore_interactions=True,
                ),
            ],
        )

    # ------------------------------------------------------------- обработчики

    async def _pick_template(self, event) -> None:
        await self.app.pick_template()

    async def _pick_inspection(self, event) -> None:
        await self.app.pick_inspection()

    def _choose_sample(self, event) -> None:
        self.app.choose_sample()

    def _open_history(self, event) -> None:
        self.app.open_history()
