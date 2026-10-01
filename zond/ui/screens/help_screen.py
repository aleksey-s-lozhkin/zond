"""Экран справки.

Короткая инструкция, а не документация: пользователь открывает её с рабочего
экрана в момент, когда что-то непонятно, и не станет читать длинный текст.
Поэтому только то, что отвечает на три вопроса: с чего начать, откуда взять
шаблон и где искать протокол.
"""

from __future__ import annotations

import flet as ft

from zond.ui.colors import AppColors
from zond.ui.components.cards import SectionCard
from zond.ui.components.headers import ScreenHeader
from zond.ui.components.layout import ScreenBody
from zond.ui.design import FontSize, Space
from zond.ui.icons import AppIcons
from zond.ui.screens.base_screen import AppScreen

#: Шаги первого запуска.
STEPS = (
    "Выберите шаблон проверки: готовый из приложения или свой CSV-файл.",
    "Заполните форму по шагам. Поля со звёздочкой обязательны.",
    "Нажмите «Завершить» и сформируйте протокол PDF.",
)

#: Способы получить шаблон.
TEMPLATE_SOURCES = (
    "Готовые шаблоны уже внутри приложения: КИП кранового узла, "
    "электроустановки, технические средства охраны.",
    "Свой шаблон — это файл CSV. Скачайте его из почты или облака на телефон "
    "и выберите «Свой шаблон из файла».",
    "Изменить готовый шаблон удобнее на компьютере: возьмите файл из папки "
    "templates, поправьте в Excel (разделитель — точка с запятой) и перенесите "
    "на телефон.",
)


def _paragraph(text: str) -> ft.Text:
    return ft.Text(text, size=FontSize.BODY, color=AppColors.TEXT)


def _bullet(text: str) -> ft.Row:
    return ft.Row(
        spacing=Space.SM,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Container(
                width=18,
                padding=ft.Padding(left=0, top=3, right=0, bottom=0),
                content=ft.Icon(AppIcons.CHEVRON, size=14, color=AppColors.PRIMARY),
            ),
            ft.Text(text, size=FontSize.BODY, color=AppColors.TEXT, expand=True),
        ],
    )


class HelpScreen(AppScreen):
    """Краткая справка по работе с приложением."""

    def compose(self) -> ft.Control:
        return ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ScreenHeader(
                    "Справка",
                    "Как пользоваться приложением",
                    on_back=self._go_back,
                ),
                ScreenBody(
                    self._steps_card(),
                    self._templates_card(),
                    self._storage_card(),
                    self._legend_card(),
                    bottom=Space.XL,
                ),
            ],
        )

    # ------------------------------------------------------------- разделы

    def _steps_card(self) -> ft.Control:
        controls: list[ft.Control] = []

        for number, step in enumerate(STEPS, start=1):
            controls.append(
                ft.Row(
                    spacing=Space.MD,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(
                            width=26,
                            height=26,
                            bgcolor=AppColors.PRIMARY_SOFT,
                            border_radius=13,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Text(
                                str(number),
                                size=FontSize.BODY,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.PRIMARY,
                            ),
                        ),
                        ft.Text(
                            step,
                            size=FontSize.BODY,
                            color=AppColors.TEXT,
                            expand=True,
                        ),
                    ],
                )
            )

        return SectionCard(*controls, title="С чего начать", icon=AppIcons.PLAY)

    def _templates_card(self) -> ft.Control:
        controls: list[ft.Control] = [_bullet(text) for text in TEMPLATE_SOURCES]

        return SectionCard(
            *controls,
            title="Откуда взять шаблон",
            icon=AppIcons.TEMPLATE,
        )

    def _storage_card(self) -> ft.Control:
        return SectionCard(
            _paragraph("Готовые протоколы:"),
            self._path_row(self.app.export_hint(), self.app.storage.pdf_dir),
            ft.Container(height=Space.XS),
            _paragraph("Данные проверок:"),
            self._path_row(str(self.app.storage.root), self.app.storage.root),
            ft.Container(height=Space.SM),
            _paragraph(
                "Кнопка «Отправить PDF» на экране итогов открывает системное меню: "
                "оттуда протокол отправляют почтой, в мессенджер или сохраняют. "
                "Android не разрешает приложению открыть файл чужими средствами, "
                "поэтому открывают его из меню или прямо из папки с протоколами."
            ),
            title="Куда сохраняются протоколы",
            icon=AppIcons.STORAGE,
        )

    def _legend_card(self) -> ft.Control:
        return SectionCard(
            self._legend_row(
                "*",
                "обязательное поле — без него не перейти к следующему шагу",
                AppColors.PRIMARY,
            ),
            self._legend_row(
                "зелёный",
                "в протоколе: требование выполнено",
                AppColors.SUCCESS,
            ),
            self._legend_row(
                "красный",
                "в протоколе: выявлено несоответствие",
                AppColors.ERROR,
            ),
            title="Обозначения",
            icon=AppIcons.INFO,
        )

    # -------------------------------------------------------------- детали

    def _path_row(self, label: str, full: object) -> ft.Control:
        return ft.Container(
            padding=ft.Padding(
                left=Space.SM,
                top=Space.SM,
                right=Space.SM,
                bottom=Space.SM,
            ),
            bgcolor=AppColors.SURFACE_ALT,
            border_radius=8,
            content=ft.Text(
                label,
                size=FontSize.BODY,
                color=AppColors.TEXT,
                selectable=True,
                tooltip=str(full),
            ),
        )

    def _legend_row(self, mark: str, description: str, color: str) -> ft.Control:
        return ft.Row(
            spacing=Space.MD,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    width=70,
                    content=ft.Text(
                        mark,
                        size=FontSize.BODY,
                        weight=ft.FontWeight.BOLD,
                        color=color,
                    ),
                ),
                ft.Text(
                    description,
                    size=FontSize.BODY,
                    color=AppColors.TEXT,
                    expand=True,
                ),
            ],
        )

    # ---------------------------------------------------------- обработчики

    def _go_back(self, event) -> None:
        self.app.navigator.back()
