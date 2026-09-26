"""Карточки и вспомогательные блоки контента."""

from __future__ import annotations

import flet as ft

from zond.ui.colors import AppColors
from zond.ui.design import FontSize, Radius, Space, StrokeWidth


class SectionCard(ft.Container):
    """Карточка-секция с необязательным заголовком.

    Пример:
        >>> SectionCard(ft.Text("содержимое"), title="Сводка", icon=ft.Icons.INFO)
    """

    def __init__(
        self,
        *controls: ft.Control,
        title: str | None = None,
        subtitle: str | None = None,
        icon=None,
        expand: bool = False,
        padding: int = Space.LG,
        bgcolor: str = AppColors.SURFACE,
        border: bool = True,
    ) -> None:
        content: list[ft.Control] = []

        if title:
            header: list[ft.Control] = []

            if icon is not None:
                header.append(ft.Icon(icon, size=20, color=AppColors.PRIMARY))

            header.append(
                ft.Text(
                    title,
                    size=FontSize.SUBTITLE,
                    weight=ft.FontWeight.W_600,
                    color=AppColors.TEXT,
                )
            )

            content.append(ft.Row(controls=header, spacing=Space.SM, tight=True))

        if subtitle:
            content.append(ft.Text(subtitle, size=FontSize.CAPTION, color=AppColors.TEXT_SECONDARY))

        if content and controls:
            content.append(ft.Divider(height=1, color=AppColors.BORDER))

        content.extend(controls)

        super().__init__(
            expand=expand,
            bgcolor=bgcolor,
            border_radius=Radius.LG,
            padding=padding,
            border=(ft.Border.all(StrokeWidth.HAIRLINE, AppColors.BORDER) if border else None),
            content=ft.Column(controls=content, spacing=Space.MD, tight=True),
        )


class InfoRow(ft.Row):
    """Строка «подпись — значение»."""

    def __init__(
        self,
        label: str,
        value: str,
        label_width: int = 150,
        value_color: str = AppColors.TEXT,
        emphasize: bool = False,
    ) -> None:
        super().__init__(
            spacing=Space.MD,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    width=label_width,
                    content=ft.Text(
                        label,
                        size=FontSize.BODY,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ),
                ft.Text(
                    value,
                    size=FontSize.BODY,
                    color=value_color,
                    weight=ft.FontWeight.W_600 if emphasize else ft.FontWeight.NORMAL,
                    expand=True,
                    selectable=True,
                ),
            ],
        )


class Badge(ft.Container):
    """Компактная цветная метка (статус, количество)."""

    def __init__(
        self,
        text: str,
        color: str = AppColors.PRIMARY,
        background: str = AppColors.PRIMARY_SOFT,
    ) -> None:
        super().__init__(
            padding=ft.Padding(left=Space.SM, top=2, right=Space.SM, bottom=2),
            bgcolor=background,
            border_radius=Radius.SM,
            content=ft.Text(
                text,
                size=FontSize.CAPTION,
                color=color,
                weight=ft.FontWeight.W_600,
            ),
        )


class EmptyState(ft.Column):
    """Заглушка для пустых списков."""

    def __init__(
        self,
        title: str,
        description: str = "",
        icon=ft.Icons.INBOX_OUTLINED,
    ) -> None:
        controls: list[ft.Control] = [
            ft.Icon(icon, size=48, color=AppColors.TEXT_DISABLED),
            ft.Text(
                title,
                size=FontSize.SUBTITLE,
                weight=ft.FontWeight.W_600,
                color=AppColors.TEXT,
                text_align=ft.TextAlign.CENTER,
            ),
        ]

        if description:
            controls.append(
                ft.Text(
                    description,
                    size=FontSize.BODY,
                    color=AppColors.TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER,
                )
            )

        super().__init__(
            controls=controls,
            spacing=Space.SM,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
