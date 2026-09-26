"""Заголовок экрана."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from zond.ui.colors import AppColors
from zond.ui.design import FontSize, Space


class ScreenHeader(ft.Container):
    """Верхняя панель экрана: кнопка «назад», заголовок, действия.

    Заголовок занимает всё свободное место (``expand``), поэтому элементы
    ``actions`` прижимаются к правому краю.
    """

    def __init__(
        self,
        title: str,
        description: str | None = None,
        on_back: Callable | None = None,
        actions: list[ft.Control] | None = None,
    ) -> None:
        controls: list[ft.Control] = []

        if on_back is not None:
            controls.append(
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=AppColors.TEXT,
                    tooltip="Назад",
                    on_click=on_back,
                )
            )

        title_column: list[ft.Control] = [
            ft.Text(
                title,
                size=FontSize.TITLE,
                weight=ft.FontWeight.BOLD,
                color=AppColors.TEXT,
            )
        ]

        if description:
            title_column.append(
                ft.Text(
                    description,
                    size=FontSize.BODY,
                    color=AppColors.TEXT_SECONDARY,
                )
            )

        controls.append(ft.Column(controls=title_column, spacing=2, expand=True, tight=True))

        if actions:
            controls.extend(actions)

        super().__init__(
            padding=ft.Padding(
                left=Space.MD,
                right=Space.MD,
                top=Space.MD,
                bottom=Space.SM,
            ),
            content=ft.Row(
                controls=controls,
                spacing=Space.SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
