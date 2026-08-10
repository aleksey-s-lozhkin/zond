import flet as ft

from zond.ui.colors import AppColors
from zond.ui.design import Space, FontSize


class ScreenHeader(ft.Container):

    def __init__(
        self,
        title: str,
        subtitle: str | None = None,
        on_back=None,
        actions: list[ft.Control] | None = None,
    ):

        left = []

        if on_back:

            left.append(
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=on_back,
                    icon_color=AppColors.TEXT,
                )
            )

        left.append(

            ft.Column(
                controls=[

                    ft.Text(
                        title,
                        size=FontSize.TITLE,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT,
                    ),

                ],
                spacing=2,
            )

        )

        if subtitle:

            left[-1].controls.append(

                ft.Text(
                    subtitle,
                    size=FontSize.BODY,
                    color=AppColors.TEXT_SECONDARY,
                )

            )

        row = ft.Row(
            controls=[
                ft.Row(
                    controls=left,
                    spacing=Space.SM,
                    expand=True,
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        if actions:

            row.controls.extend(actions)

        super().__init__(

            padding=ft.padding.symmetric(
                horizontal=Space.LG,
                vertical=Space.MD,
            ),

            bgcolor=AppColors.BACKGROUND,

            content=row,
        )