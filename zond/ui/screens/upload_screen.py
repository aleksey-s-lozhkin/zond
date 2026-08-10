import flet as ft

from zond.ui.colors import AppColors


class UploadScreen(ft.Container):
    """ Стартовый экран приложения. """

    def __init__(self, on_upload=None):

        print("UploadScreen получил callback:", on_upload)

        self.on_upload = on_upload

        super().__init__(

            expand=True,

            alignment=ft.Alignment(0, 0),

            bgcolor=AppColors.BACKGROUND,

            content=self._build(),

        )

    async def _upload_click(self, e):
        print("BUTTON CLICK")

        await self.on_upload(e)

    def _main_content(self):
        return ft.Column(

            horizontal_alignment=ft.CrossAxisAlignment.CENTER,

            alignment=ft.MainAxisAlignment.CENTER,

            spacing=12,

            controls=[

                ft.Image(
                    src="images/logo.png",
                    width=110,
                    height=110,
                    fit=ft.BoxFit.CONTAIN,
                ),

                ft.Container(height=10),

                ft.Text(
                    "ЗОНД: ECTS",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT,
                ),

                ft.Text(
                    "Система проверки оборудования",
                    size=16,
                    color=AppColors.TEXT_SECONDARY,
                ),

                ft.Container(height=20),

                ft.ElevatedButton(
                    content=ft.Text(
                        "Загрузить шаблон",
                        size=16,
                    ),
                    icon=ft.Icons.UPLOAD,
                    on_click=self._upload_click,

                    style=ft.ButtonStyle(
                        bgcolor=AppColors.PRIMARY,
                        color=ft.Colors.WHITE,

                        padding=ft.Padding(
                            left=32,
                            right=32,
                            top=14,
                            bottom=14,
                        ),

                        shape=ft.RoundedRectangleBorder(
                            radius=12,
                        ),
                    ),
                ),

                ft.Text(
                    "Поддерживается CSV формат",
                    size=12,
                    color=AppColors.TEXT_SECONDARY,
                ),

            ],
        )

    def _build(self):
        return ft.Stack(

            controls=[

                ft.Container(
                    content=self._main_content(),
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                ),

                ft.Container(
                    content=ft.Text(
                        "Версия 1.0.0",
                        size=12,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    alignment=ft.Alignment(0, 1),
                    ignore_interactions=True,
                ),

            ],

            expand=True,

        )