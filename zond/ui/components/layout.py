"""Каркас экрана: прокручиваемая область контента и панель действий.

Отступы задаются в одном месте, иначе поля и карточки на разных экранах
прилипают к краям окна по-разному.
"""

from __future__ import annotations

import flet as ft

from zond.ui.design import Space


class ScreenBody(ft.Container):
    """Прокручиваемая область контента с боковыми отступами.

    Содержимое растягивается по ширине (``STRETCH``), поэтому карточки и
    поля ввода занимают всю доступную ширину, а длинные подписи переносятся
    на следующую строку, а не обрезаются.
    """

    def __init__(
        self,
        *controls: ft.Control,
        spacing: int = Space.MD,
        horizontal_padding: int = Space.MD,
        top: int = 0,
        bottom: int = Space.MD,
    ) -> None:
        super().__init__(
            expand=True,
            padding=ft.Padding(
                left=horizontal_padding,
                right=horizontal_padding,
                top=top,
                bottom=bottom,
            ),
            content=ft.Column(
                controls=list(controls),
                expand=True,
                spacing=spacing,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )


class ActionBar(ft.Container):
    """Нижняя панель с кнопками, закреплённая под областью контента."""

    def __init__(self, *controls: ft.Control, spacing: int = Space.SM) -> None:
        super().__init__(
            padding=ft.Padding(
                left=Space.MD,
                right=Space.MD,
                top=Space.SM,
                bottom=Space.MD,
            ),
            content=ft.Row(controls=list(controls), spacing=spacing),
        )
