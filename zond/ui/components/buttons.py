import flet as ft

from zond.ui.colors import AppColors
from zond.ui.design import Radius, ControlSize


class PrimaryButton(ft.ElevatedButton):

    def __init__(
        self,
        text: str,
        on_click=None,
        icon=None,
        expand=False,
    ):

        super().__init__(
            text=text,
            icon=icon,
            expand=expand,
            height=ControlSize.BUTTON_HEIGHT,
            on_click=on_click,

            style=ft.ButtonStyle(
                bgcolor=AppColors.PRIMARY,
                color=ft.Colors.WHITE,
                elevation=0,
                shape=ft.RoundedRectangleBorder(
                    radius=Radius.MD
                ),
            )
        )

class SecondaryButton(ft.OutlinedButton):

    def __init__(
        self,
        text,
        on_click=None,
        icon=None,
    ):

        super().__init__(

            text=text,

            icon=icon,

            on_click=on_click,

            height=ControlSize.BUTTON_HEIGHT,

            style=ft.ButtonStyle(

                side=ft.BorderSide(
                    1,
                    AppColors.BORDER,
                ),

                shape=ft.RoundedRectangleBorder(
                    radius=Radius.MD
                ),

            ),
        )

class SuccessButton(PrimaryButton):

    def __init__(self, text, on_click=None):

        super().__init__(
            text=text,
            on_click=on_click,
        )

        self.style.bgcolor = AppColors.SUCCESS
        