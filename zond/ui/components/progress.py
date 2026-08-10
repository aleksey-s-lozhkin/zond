import flet as ft

from zond.ui.colors import AppColors
from zond.ui.design import Space, FontSize


class ProgressWidget(ft.Container):
    """ Отображает прогресс заполнения проверки. """

    def __init__(
        self,
        title: str,
        current: int,
        total: int,
    ):

        progress = 0 if total == 0 else current / total

        super().__init__(

            padding=ft.padding.symmetric(
                horizontal=Space.LG,
                vertical=Space.MD,
            ),

            content=ft.Column(

                spacing=Space.SM,

                controls=[

                    ft.Row(

                        controls=[

                            ft.Text(
                                title,
                                size=FontSize.SUBTITLE,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT,
                            ),

                            ft.Container(expand=True),

                            ft.Text(
                                f"{current}/{total}",
                                size=FontSize.BODY,
                                color=AppColors.TEXT_SECONDARY,
                            ),

                        ]
                    ),

                    ft.ProgressBar(
                        value=progress,
                        height=6,
                        color=AppColors.PRIMARY,
                        bgcolor=AppColors.BORDER,
                        border_radius=20,
                    ),

                ]
            )
        )