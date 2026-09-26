"""Индикатор прогресса заполнения проверки."""

from __future__ import annotations

import contextlib

import flet as ft

from zond.ui.colors import AppColors
from zond.ui.design import ControlSize, FontSize, Radius, Space


class ProgressWidget(ft.Container):
    """Заголовок с числом шагов и полоса прогресса.

    Полоса обновляется через :meth:`set_progress` без пересборки экрана —
    иначе ввод терял бы фокус на каждом нажатии клавиши.
    """

    def __init__(
        self,
        title: str,
        current: int,
        total: int,
        subtitle: str | None = None,
        caption: str | None = None,
    ) -> None:
        self._current = current
        self._total = total

        self._counter = ft.Text(
            self._format_counter(),
            size=FontSize.BODY,
            color=AppColors.TEXT_SECONDARY,
        )

        heading: list[ft.Control] = [
            ft.Text(
                title,
                size=FontSize.SUBTITLE,
                weight=ft.FontWeight.W_600,
                color=AppColors.TEXT,
            ),
            ft.Container(expand=True),
            self._counter,
        ]

        controls: list[ft.Control] = [ft.Row(controls=heading, spacing=Space.SM)]

        if subtitle:
            controls.append(
                ft.Text(subtitle, size=FontSize.CAPTION, color=AppColors.TEXT_SECONDARY)
            )

        self._bar = ft.ProgressBar(
            value=self._format_ratio(),
            bar_height=ControlSize.PROGRESS_BAR,
            color=AppColors.PRIMARY,
            bgcolor=AppColors.BORDER,
            border_radius=Radius.XL,
        )
        controls.append(self._bar)

        self._caption: ft.Text | None = None
        if caption:
            self._caption = ft.Text(
                caption,
                size=FontSize.CAPTION,
                color=AppColors.TEXT_SECONDARY,
            )
            controls.append(self._caption)

        super().__init__(
            padding=ft.Padding(
                left=Space.LG,
                right=Space.LG,
                top=0,
                bottom=Space.MD,
            ),
            content=ft.Column(controls=controls, spacing=Space.SM, tight=True),
        )

    # ------------------------------------------------------------- обновление

    def set_progress(self, current: int, total: int, caption: str | None = None) -> None:
        """Обновить значение прогресса без перерисовки всего экрана."""

        self._current = current
        self._total = total

        self._bar.value = self._format_ratio()
        self._counter.value = self._format_counter()

        if caption is not None and self._caption is not None:
            self._caption.value = caption

        for control in (self._bar, self._counter, self._caption):
            if control is not None:
                _safe_update(control)

    # -------------------------------------------------------------- служебное

    def _format_ratio(self) -> float:
        if self._total <= 0:
            return 0.0

        return max(0.0, min(1.0, self._current / self._total))

    def _format_counter(self) -> str:
        return f"{self._current}/{self._total}"


def _safe_update(control: ft.Control) -> None:
    """Обновить контрол, если он смонтирован (в тестах страницы нет)."""

    with contextlib.suppress(RuntimeError):
        control.update()
