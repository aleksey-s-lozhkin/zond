"""Модальные диалоги: ошибки, подтверждения, информация.

Единая точка показа диалогов. Раньше ошибки уходили в ``print``, и
пользователь не понимал, почему ничего не произошло.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable

import flet as ft

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
