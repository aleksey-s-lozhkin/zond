import flet as ft

from zond.ui.colors import AppColors
from zond.ui.design import Radius, Space


class SectionCard(ft.Container):
    """
    Базовая карточка приложения.

    Может содержать:
        • заголовок
        • подзаголовок
        • произвольный список элементов
    """

    def __init__(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        icon=None,
        expand: bool = False,
        content: list[ft.Control] | None = None,
    ):

        controls = []

        # ---------- Header ----------

        if title:

            header = []

            if icon:
                header.append(
                    ft.Icon(
                        icon,
                        size=22,
                        color=AppColors.PRIMARY,
                    )
                )

            header.append(
                ft.Text(
                    title,
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT,
                )
            )

            controls.append(
                ft.Row(
                    controls=header,
                    spacing=10,
                )
            )

        if subtitle:

            controls.append(
                ft.Text(
                    subtitle,
                    size=14,
                    color=AppColors.TEXT_SECONDARY,
                )
            )

        if title or subtitle:
            controls.append(
                ft.Divider(height=1)
            )

        # ---------- Content ----------

        if content:
            controls.extend(content)

        super().__init__(
            expand=expand,
            bgcolor=AppColors.SURFACE,
            border_radius=Radius.LG,
            padding=Space.LG,
            border=ft.border.all(
                1,
                AppColors.BORDER,
            ),
            content=ft.Column(
                controls=controls,
                spacing=Space.MD,
            ),
        )