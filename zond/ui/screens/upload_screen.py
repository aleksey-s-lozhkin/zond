"""Стартовый экран: начать проверку, продолжить прежнюю, справка.

Экран намеренно построен на карточках с пояснениями, а не на голых кнопках.
Название «Загрузить образец» само по себе не отвечает на вопрос, есть ли у
пользователя этот образец и откуда его взять, поэтому у каждого действия есть
вторая строка, а рядом — ссылка на справку.
"""

from __future__ import annotations

import flet as ft

from zond.services.sample_templates import available_samples
from zond.ui.colors import AppColors
from zond.ui.components.cards import ActionCard
from zond.ui.design import ControlSize, FontSize, Space
from zond.ui.icons import AppIcons
from zond.ui.screens.base_screen import AppScreen

VERSION = "1.0.0"

#: Пояснение к готовым шаблонам: главное — что их не нужно искать.
#: Перечислять шаблоны здесь не стоит: список растёт, а полный состав
#: всё равно виден в диалоге. Количество показано в заголовке карточки.
SAMPLES_HINT = "Готовые чек-листы уже в приложении — откроется список"


def _section_title(text: str) -> ft.Text:
    """Подпись группы действий."""

    return ft.Text(
        text,
        size=FontSize.CAPTION,
        weight=ft.FontWeight.W_600,
        color=AppColors.TEXT_SECONDARY,
    )


class UploadScreen(AppScreen):
    """Экран запуска приложения."""

    def compose(self) -> ft.Control:
        stored = self.app.storage.list_stored()
        drafts = sum(1 for entry in stored if entry.is_draft)
        samples = available_samples()

        start: list[ft.Control] = []

        if samples:
            start.append(
                ActionCard(
                    f"Готовые шаблоны ({len(samples)})",
                    SAMPLES_HINT,
                    icon=AppIcons.SAMPLES,
                    on_click=self._choose_sample,
                    primary=True,
                )
            )

        start.append(
            ActionCard(
                "Свой шаблон из файла",
                "CSV-файл, сохранённый в памяти устройства",
                icon=AppIcons.TEMPLATE,
                on_click=self._pick_template,
                primary=not samples,
            )
        )

        cont: list[ft.Control] = []

        if stored:
            finished = len(stored) - drafts

            # Конкретные числа вместо пояснений: что такое черновик, на этом
            # экране всё равно не объяснить, а список показывает статусы сам.
            hint = f"Завершённых: {finished}"

            if drafts:
                hint += f" · Незаконченных: {drafts}"

            cont.append(
                ActionCard(
                    f"История проверок ({len(stored)})",
                    hint,
                    icon=AppIcons.HISTORY,
                    on_click=self._open_history,
                )
            )

        cont.append(
            ActionCard(
                "Открыть проверку из файла",
                "JSON-файл, полученный с другого устройства",
                icon=AppIcons.OPEN,
                on_click=self._pick_inspection,
            )
        )

        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=0,
            controls=[
                self._title_block(),
                ft.Container(
                    padding=ft.Padding(
                        left=Space.LG,
                        right=Space.LG,
                        bottom=Space.LG,
                    ),
                    content=ft.Column(
                        spacing=Space.SM,
                        controls=[
                            _section_title("НАЧАТЬ ПРОВЕРКУ"),
                            *start,
                            ft.Container(height=Space.MD),
                            _section_title("ПРОДОЛЖИТЬ"),
                            *cont,
                        ],
                    ),
                ),
                self._footer(),
            ],
        )

    # -------------------------------------------------------------- блоки

    def _title_block(self) -> ft.Control:
        return ft.Container(
            padding=ft.Padding(
                left=Space.LG,
                top=Space.XL,
                right=Space.LG,
                bottom=Space.LG,
            ),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=Space.SM,
                controls=[
                    ft.Image(
                        src="images/logo.png",
                        width=ControlSize.LOGO,
                        height=ControlSize.LOGO,
                        fit=ft.BoxFit.CONTAIN,
                    ),
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
                ],
            ),
        )

    def _footer(self) -> ft.Control:
        return ft.Container(
            padding=ft.Padding(
                left=Space.LG,
                right=Space.LG,
                top=Space.SM,
                bottom=Space.LG,
            ),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=Space.XS,
                controls=[
                    ft.TextButton(
                        content=ft.Text(
                            "Справка",
                            size=FontSize.BODY,
                            weight=ft.FontWeight.W_600,
                        ),
                        icon=AppIcons.HELP,
                        on_click=self._open_help,
                    ),
                    ft.Text(
                        "Протоколы сохраняются в:",
                        size=FontSize.CAPTION,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    ft.Text(
                        self.app.export_hint(),
                        size=FontSize.CAPTION,
                        color=AppColors.TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER,
                        tooltip=str(self.app.storage.pdf_dir),
                    ),
                    ft.Container(height=Space.XS),
                    ft.Text(
                        f"Версия {VERSION}",
                        size=FontSize.CAPTION,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
            ),
        )

    # --------------------------------------------------------- обработчики

    async def _pick_template(self, event) -> None:
        await self.app.pick_template()

    async def _pick_inspection(self, event) -> None:
        await self.app.pick_inspection()

    def _choose_sample(self, event) -> None:
        self.app.choose_sample()

    def _open_history(self, event) -> None:
        self.app.open_history()

    def _open_help(self, event) -> None:
        self.app.open_help()
