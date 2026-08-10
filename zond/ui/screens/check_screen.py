import flet as ft

from zond.app.state import ZondState
from zond.ui.colors import AppColors
from zond.ui.screens.inspection_screen import InspectionScreen


class CheckScreen(ft.Container):
    """Экран проверки оборудования."""

    def __init__(self, state: ZondState, navigator):

        self.state = state
        self.navigator = navigator


        super().__init__(
            expand=True,
            bgcolor=AppColors.BACKGROUND,
            content=self._build(),
        )

    def start_check(self, e):
        self.navigator.show(
            InspectionScreen(
                self.state
            )
        )


    def _build(self):

        template = self.state.template
        groups = self.state.groups

        if template is None:
            return ft.Text(
                "Шаблон не загружен"
            )


        return ft.Column(

            alignment=ft.MainAxisAlignment.CENTER,

            horizontal_alignment=ft.CrossAxisAlignment.CENTER,

            controls=[

                ft.Text(
                    "Шаблон загружен",
                    size=26,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Text(
                    f"{template.name}",
                    size=16,
                    color=AppColors.TEXT_SECONDARY,
                ),


                ft.Text(
                    f"Количество полей: {len(template.fields)}",
                    size=16,
                ),

                ft.Text(
                    "Группы:",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Text(
                    "\n".join(groups) if groups else "Группы не определены",
                    size=14,
                ),

                ft.ElevatedButton(
                    "Начать проверку",
                    icon=ft.Icons.PLAY_ARROW,
                    on_click=self.start_check,
                )

            ],

        )