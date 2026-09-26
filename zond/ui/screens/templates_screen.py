"""Библиотека шаблонов: список, добавление и удаление.

Шаблоны лежат обычными файлами в папке приложения, и всё, что в списке есть,
пользователь может удалить — включая примеры, разложенные при первом запуске.
Приложение не должно показывать неизменяемый набор: оно рабочий инструмент, и
база шаблонов собирается постепенно под конкретную работу.

Отдельный экран вместо диалога выбран потому, что у строки появилось действие
(удаление), а список растёт.
"""

from __future__ import annotations

import logging
from datetime import datetime

import flet as ft

from zond.services.template_library import LibraryEntry
from zond.services.template_loader import TemplateLoader
from zond.ui.colors import AppColors
from zond.ui.components.buttons import PrimaryButton, SecondaryButton
from zond.ui.components.cards import EmptyState
from zond.ui.components.dialogs import show_error
from zond.ui.components.headers import ScreenHeader
from zond.ui.components.layout import ActionBar, ScreenBody
from zond.ui.design import FontSize, Radius, Space, StrokeWidth
from zond.ui.icons import AppIcons
from zond.ui.screens.base_screen import AppScreen

logger = logging.getLogger(__name__)


def _modified(path) -> str:
    """Дата изменения файла в привычном виде."""

    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%d.%m.%Y")
    except OSError:
        return ""


def _describe(path) -> str:
    """Краткое описание шаблона: сколько в нём полей и групп."""

    try:
        template = TemplateLoader().load(path)
    except Exception:
        logger.exception("Не удалось прочитать шаблон %s", path)
        return "файл не читается"

    return f"{len(template.fields)} полей · {template.total_groups} групп"


class TemplatesScreen(AppScreen):
    """Список шаблонов проверок с добавлением и удалением."""

    def compose(self) -> ft.Control:
        self.app.library.ensure()

        entries = self.app.library.list_entries()

        rows: list[ft.Control] = [self._add_card()]

        if entries:
            rows.append(ft.Container(height=Space.XS))
            rows.extend(self._row(entry) for entry in entries)

            missing = self.app.library.missing_examples()

            if missing:
                rows.append(ft.Container(height=Space.SM))
                rows.append(self._restore_button(len(missing)))
        else:
            rows.append(
                EmptyState(
                    "Шаблонов пока нет",
                    "Добавьте CSV-файл из памяти устройства.",
                    icon=AppIcons.TEMPLATE,
                )
            )

        return ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ScreenHeader(
                    "Шаблоны",
                    self._subtitle(entries),
                    on_back=self._go_back,
                ),
                ScreenBody(*rows, bottom=Space.XL),
                self._action_bar(),
            ],
        )

    # --------------------------------------------------------------- блоки

    def _subtitle(self, entries: list[LibraryEntry]) -> str:
        if not entries:
            return "Библиотека пуста"

        word = "шаблон" if len(entries) == 1 else "шаблонов"

        return f"{len(entries)} {word} · папка приложения"

    def _add_card(self) -> ft.Control:
        return ft.Container(
            padding=ft.Padding(
                left=Space.MD,
                top=Space.MD,
                right=Space.MD,
                bottom=Space.MD,
            ),
            bgcolor=AppColors.PRIMARY_SOFT,
            border=ft.Border.all(StrokeWidth.HAIRLINE, AppColors.PRIMARY_BORDER),
            border_radius=Radius.MD,
            ink=True,
            on_click=self._add,
            content=ft.Row(
                spacing=Space.MD,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(AppIcons.ADD, size=24, color=AppColors.PRIMARY),
                    ft.Column(
                        spacing=2,
                        tight=True,
                        expand=True,
                        controls=[
                            ft.Text(
                                "Добавить шаблон из файла",
                                size=FontSize.SUBTITLE,
                                weight=ft.FontWeight.W_600,
                                color=AppColors.PRIMARY,
                            ),
                            ft.Text(
                                "CSV-файл из памяти устройства — он останется в библиотеке",
                                size=FontSize.CAPTION,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _row(self, entry: LibraryEntry) -> ft.Control:
        return ft.Container(
            padding=ft.Padding(
                left=Space.MD,
                top=Space.SM,
                right=Space.SM,
                bottom=Space.SM,
            ),
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(StrokeWidth.HAIRLINE, AppColors.BORDER),
            border_radius=Radius.MD,
            content=ft.Row(
                spacing=Space.SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        expand=True,
                        ink=True,
                        on_click=self._open_handler(entry),
                        content=ft.Row(
                            spacing=Space.MD,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(
                                    AppIcons.TEMPLATE,
                                    size=24,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                                ft.Column(
                                    spacing=2,
                                    tight=True,
                                    expand=True,
                                    controls=[
                                        ft.Text(
                                            entry.name,
                                            size=FontSize.SUBTITLE,
                                            weight=ft.FontWeight.W_600,
                                            color=AppColors.TEXT,
                                            max_lines=2,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                        ft.Text(
                                            f"{_describe(entry.path)} · {_modified(entry.path)}",
                                            size=FontSize.CAPTION,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    ft.IconButton(
                        icon=AppIcons.DELETE,
                        icon_color=AppColors.TEXT_SECONDARY,
                        tooltip=f"Удалить «{entry.name}»",
                        on_click=lambda event, item=entry: self._confirm_delete(item),
                    ),
                ],
            ),
        )

    def _restore_button(self, count: int) -> ft.Control:
        """Вернуть примеры, удалённые из библиотеки.

        Кнопка появляется только когда чего-то не хватает: постоянно держать
        её на экране незачем.
        """

        return ft.TextButton(
            content=ft.Text(
                f"Вернуть примеры ({count})",
                size=FontSize.CAPTION,
                weight=ft.FontWeight.W_600,
            ),
            icon=AppIcons.HISTORY,
            on_click=self._restore,
        )

    def _action_bar(self) -> ft.Control:
        return ActionBar(
            SecondaryButton(
                "Назад",
                icon=AppIcons.BACK,
                on_click=self._go_back,
                expand=True,
            ),
            PrimaryButton(
                "Добавить из файла",
                icon=AppIcons.ADD,
                on_click=self._add,
                expand=True,
            ),
        )

    # ----------------------------------------------------------- обработчики

    def _go_back(self, event) -> None:
        self.app.navigator.back()

    async def _add(self, event) -> None:
        await self.app.import_template()

    def _open_handler(self, entry: LibraryEntry):
        """Открыть шаблон по нажатию на строку.

        Flet дожидается только настоящих корутин. Lambda, возвращающая
        корутину, не дожидается никем: нажатие проходит, а открытие не
        начинается. Поэтому обработчик — async-функция, а не lambda.
        """

        async def handler(event) -> None:
            await self.app.open_template(entry)

        return handler

    def _restore(self, event) -> None:
        restored = self.app.restore_examples()

        if not restored:
            show_error(
                self.app.page,
                "Нечего восстанавливать",
                "Все примеры поставки уже есть в библиотеке.",
            )

    def _confirm_delete(self, entry: LibraryEntry) -> None:
        from zond.ui.components.dialogs import show_confirm

        show_confirm(
            self.app.page,
            "Удалить шаблон?",
            f"Файл «{entry.name}.csv» будет удалён из библиотеки. "
            "Проверки, уже выполненные по нему, останутся.",
            on_confirm=lambda event, item=entry: self._delete(item),
            confirm_text="Удалить",
            danger=True,
        )

    def _delete(self, entry: LibraryEntry) -> None:
        if not self.app.delete_template(entry):
            show_error(
                self.app.page,
                "Не удалось удалить",
                f"Файл «{entry.name}.csv» не удалось удалить.",
            )
