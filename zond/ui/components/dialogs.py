"""Модальные диалоги: ошибки, подтверждения, информация.

Единая точка показа диалогов. Раньше ошибки уходили в ``print``, и
пользователь не понимал, почему ничего не произошло.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Sequence

import flet as ft

from zond.services.sample_templates import sample_subtitle, sample_title
from zond.ui.colors import AppColors
from zond.ui.design import FontSize, Radius, Space
from zond.ui.icons import AppIcons


def _dialog_title(text: str, icon, color: str) -> ft.Control:
    return ft.Row(
        spacing=Space.SM,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Icon(icon, color=color, size=24),
            ft.Text(
                text,
                size=FontSize.SUBTITLE,
                weight=ft.FontWeight.W_600,
                color=AppColors.TEXT,
            ),
        ],
    )


def _close(page: ft.Page) -> None:
    page.pop_dialog()


def show_error(page: ft.Page, title: str, message: str) -> None:
    """Показать ошибку. ``message`` может быть многострочным списком проблем."""

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=Radius.LG),
            title=_dialog_title(title, AppIcons.ERROR, AppColors.ERROR),
            content=ft.Container(
                width=460,
                content=ft.Text(
                    message,
                    size=FontSize.BODY,
                    color=AppColors.TEXT,
                    selectable=True,
                ),
            ),
            actions=[ft.TextButton("Понятно", on_click=lambda e: _close(page))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
    )


def show_info(page: ft.Page, title: str, message: str) -> None:
    """Показать нейтральное сообщение."""

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=Radius.LG),
            title=_dialog_title(title, AppIcons.INFO, AppColors.PRIMARY),
            content=ft.Container(
                width=460,
                content=ft.Text(
                    message,
                    size=FontSize.BODY,
                    color=AppColors.TEXT,
                    selectable=True,
                ),
            ),
            actions=[ft.TextButton("Закрыть", on_click=lambda e: _close(page))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
    )


def _choice_row(
    page: ft.Page,
    label: str,
    description: str,
    callback: Callable,
) -> ft.Control:
    """Строка списка выбора: заголовок, пояснение и обработчик."""

    def handler() -> Callable:
        async def _selected(event) -> None:
            _close(page)
            result = callback(event)

            if inspect.isawaitable(result):
                await result

        return _selected

    rows: list[ft.Control] = [
        ft.Text(
            label,
            size=FontSize.BODY,
            weight=ft.FontWeight.W_600,
            color=AppColors.TEXT,
        )
    ]

    if description:
        rows.append(
            ft.Text(
                description,
                size=FontSize.CAPTION,
                color=AppColors.TEXT_SECONDARY,
            )
        )

    return ft.Container(
        padding=ft.Padding(
            left=Space.MD,
            top=Space.SM,
            right=Space.MD,
            bottom=Space.SM,
        ),
        border_radius=Radius.SM,
        bgcolor=AppColors.SURFACE_ALT,
        on_click=handler(),
        content=ft.Column(controls=rows, spacing=2, tight=True),
    )


def _choice_dialog(
    page: ft.Page,
    title: str,
    message: str,
    items: Sequence[ft.Control],
    icon=None,
) -> None:
    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=Radius.LG),
            title=_dialog_title(title, icon or AppIcons.LIST, AppColors.PRIMARY),
            content=ft.Container(
                width=460,
                content=ft.Column(controls=list(items), spacing=Space.SM, tight=True),
            ),
            actions=[ft.TextButton("Отмена", on_click=lambda e: _close(page))],
            actions_alignment=ft.MainAxisAlignment.END,
            data=message,
        )
    )


def _group_title(text: str) -> ft.Control:
    return ft.Text(
        text,
        size=FontSize.CAPTION,
        weight=ft.FontWeight.W_600,
        color=AppColors.TEXT_SECONDARY,
    )


def show_choice(
    page: ft.Page,
    title: str,
    message: str,
    options: Sequence[tuple[str, str, Callable]],
) -> None:
    """Показать список вариантов на выбор.

    ``options`` — последовательность троек «заголовок, пояснение, обработчик».
    Обработчик вызывается после закрытия диалога и может быть как обычной,
    так и асинхронной функцией.
    """

    items = [
        _choice_row(page, label, description, callback) for label, description, callback in options
    ]

    _choice_dialog(page, title, message, items)


def show_template_choice(
    page: ft.Page,
    on_file: Callable,
    samples: Sequence,
    on_sample: Callable,
) -> None:
    """Выбор источника шаблона: свой файл или готовый пример.

    Действие одно — загрузить шаблон, — а источников два. Держать их двумя
    пунктами стартового экрана значит выдавать одно действие за два и
    наводить на мысль, что шаблон «устанавливается» в приложение: отсюда и
    вопросы про удаление старых шаблонов.
    """

    items: list[ft.Control] = [
        _choice_row(
            page,
            "Файл из памяти устройства",
            "CSV-файл, сохранённый на телефоне или переданный по USB",
            lambda event: on_file(),
        )
    ]

    if samples:
        items.append(ft.Container(height=Space.XS))
        items.append(_group_title("Примеры"))
        items.append(_group_title("Готовые чек-листы, чтобы посмотреть, как всё устроено."))

        for path in samples:
            items.append(
                _choice_row(
                    page,
                    sample_title(path),
                    sample_subtitle(path),
                    lambda event, item=path: on_sample(item),
                )
            )

    _choice_dialog(
        page,
        "Выбрать шаблон проверки",
        "Свой шаблон или готовый пример.",
        items,
        icon=AppIcons.TEMPLATE,
    )


def show_confirm(
    page: ft.Page,
    title: str,
    message: str,
    on_confirm: Callable | None,
    confirm_text: str = "Продолжить",
    cancel_text: str = "Отмена",
    danger: bool = False,
) -> None:
    """Спросить подтверждение действия.

    ``on_confirm`` вызывается только после подтверждения и может быть как
    обычной, так и асинхронной функцией.
    """

    async def _confirmed(event) -> None:
        _close(page)

        if on_confirm is None:
            return

        result = on_confirm(event)

        if inspect.isawaitable(result):
            await result

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            scrollable=True,
            shape=ft.RoundedRectangleBorder(radius=Radius.LG),
            title=_dialog_title(
                title,
                AppIcons.WARNING,
                AppColors.ERROR if danger else AppColors.WARNING,
            ),
            content=ft.Container(
                width=440,
                content=ft.Text(message, size=FontSize.BODY, color=AppColors.TEXT),
            ),
            actions=[
                ft.TextButton(cancel_text, on_click=lambda e: _close(page)),
                ft.TextButton(
                    confirm_text,
                    on_click=_confirmed,
                    style=ft.ButtonStyle(color=AppColors.ERROR if danger else AppColors.PRIMARY),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
    )
