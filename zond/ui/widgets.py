import flet as ft

from .colors import AppColors


class PrimaryButton(ft.ElevatedButton):

    def __init__(
        self,
        text: str,
        on_click=None,
        icon=None,
        width=260,
    ):

        super().__init__(
            text=text,
            icon=icon,
            width=width,
            height=52,
            on_click=on_click,

            style=ft.ButtonStyle(
                bgcolor=AppColors.PRIMARY,
                color=ft.Colors.WHITE,
                elevation=1,
                shape=ft.RoundedRectangleBorder(radius=12),
            )
        )

class SecondaryButton(ft.OutlinedButton):

    def __init__(
        self,
        text,
        on_click=None,
        icon=None,
        width=260,
    ):

        super().__init__(
            text=text,
            icon=icon,
            width=width,
            height=52,
            on_click=on_click,

            style=ft.ButtonStyle(
                side=ft.BorderSide(
                    1,
                    AppColors.BORDER,
                ),

                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )

class SectionCard(ft.Container):

    def __init__(self, *controls):

        super().__init__(

            bgcolor=AppColors.SURFACE,

            border_radius=16,

            padding=20,

            border=ft.border.all(
                1,
                AppColors.BORDER,
            ),

            content=ft.Column(
                controls=list(controls),
                spacing=12,
            )
        )

class ScreenHeader(ft.Column):

    def __init__(
        self,
        title,
        subtitle="",
    ):

        controls = [

            ft.Text(
                title,
                size=28,
                weight=ft.FontWeight.BOLD,
                color=AppColors.TEXT,
            )

        ]

        if subtitle:

            controls.append(

                ft.Text(
                    subtitle,
                    size=15,
                    color=AppColors.TEXT_SECONDARY,
                )

            )

        super().__init__(
            controls=controls,
            spacing=4,
        )
