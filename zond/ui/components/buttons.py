"""Кнопки приложения.

Подпись передаётся через ``content``: параметра ``text`` у кнопок Flet 0.86
нет. Базовый класс — :class:`flet.Button`; ``ElevatedButton`` объявлен
устаревшим с версии 0.80. Все кнопки проекта строятся здесь, чтобы стиль не
расползался по экранам.
"""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from zond.ui.colors import AppColors
from zond.ui.design import ControlSize, FontSize, Radius


class PrimaryButton(ft.Button):
    """Основное действие экрана."""

    _bgcolor = AppColors.PRIMARY
    _foreground = AppColors.WHITE

    def __init__(
        self,
        text: str,
        on_click: Callable | None = None,
        icon=None,
        expand: bool = False,
        width: int | None = None,
        disabled: bool = False,
        tooltip: str | None = None,
    ) -> None:
        super().__init__(
            content=ft.Text(text, size=FontSize.BUTTON, weight=ft.FontWeight.W_600),
            icon=icon,
            expand=expand,
            width=width,
            disabled=disabled,
            tooltip=tooltip,
            height=ControlSize.BUTTON_HEIGHT,
            on_click=on_click,
            style=ft.ButtonStyle(
                bgcolor=self._bgcolor,
                color=self._foreground,
                elevation=0,
                shape=ft.RoundedRectangleBorder(radius=Radius.MD),
            ),
        )


class SuccessButton(PrimaryButton):
    """Подтверждающее действие (сохранение, завершение)."""

    _bgcolor = AppColors.SUCCESS


class DangerButton(PrimaryButton):
    """Необратимое действие (удаление)."""

    _bgcolor = AppColors.ERROR


class SecondaryButton(ft.OutlinedButton):
    """Второстепенное действие."""

    def __init__(
        self,
        text: str,
        on_click: Callable | None = None,
        icon=None,
        expand: bool = False,
        width: int | None = None,
        disabled: bool = False,
        tooltip: str | None = None,
    ) -> None:
        super().__init__(
            content=ft.Text(text, size=FontSize.BUTTON, weight=ft.FontWeight.W_500),
            icon=icon,
            expand=expand,
            width=width,
            disabled=disabled,
            tooltip=tooltip,
            height=ControlSize.BUTTON_HEIGHT,
            on_click=on_click,
            style=ft.ButtonStyle(
                color=AppColors.TEXT,
                side=ft.BorderSide(1, AppColors.BORDER_STRONG),
                shape=ft.RoundedRectangleBorder(radius=Radius.MD),
            ),
        )


class GhostButton(ft.TextButton):
    """Действие без визуального акцента (ссылки, «Ещё»)."""

    def __init__(
        self,
        text: str,
        on_click: Callable | None = None,
        icon=None,
        disabled: bool = False,
        tooltip: str | None = None,
    ) -> None:
        super().__init__(
            content=ft.Text(text, size=FontSize.BODY, weight=ft.FontWeight.W_500),
            icon=icon,
            disabled=disabled,
            tooltip=tooltip,
            on_click=on_click,
            style=ft.ButtonStyle(color=AppColors.PRIMARY),
        )
