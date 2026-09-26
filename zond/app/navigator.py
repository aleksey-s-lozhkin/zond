"""Навигация между экранами.

Навигатор хранит стек экранов, поэтому «назад» возвращает именно туда, откуда
пользователь пришёл, а не на стартовый экран.
"""

from __future__ import annotations

import logging

import flet as ft

from zond.ui.screens.base_screen import AppScreen

logger = logging.getLogger(__name__)


class ZondNavigator:
    """Стек экранов поверх ``page.controls``."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self._stack: list[AppScreen] = []

    # ------------------------------------------------------------ свойства

    @property
    def current(self) -> AppScreen | None:
        return self._stack[-1] if self._stack else None

    @property
    def depth(self) -> int:
        return len(self._stack)

    @property
    def can_go_back(self) -> bool:
        return len(self._stack) > 1

    # ------------------------------------------------------------- переходы

    def show(self, screen: AppScreen) -> None:
        """Показать экран как корневой, очистив историю."""

        self._stack = [screen]
        self._render()

    def push(self, screen: AppScreen) -> None:
        """Открыть экран поверх текущего."""

        self._stack.append(screen)
        self._render()

    def replace(self, screen: AppScreen) -> None:
        """Заменить текущий экран, сохранив историю."""

        if self._stack:
            self._stack[-1] = screen
        else:
            self._stack = [screen]

        self._render()

    def back(self) -> bool:
        """Вернуться на предыдущий экран.

        Returns:
            ``True``, если переход выполнен; ``False``, если история пуста.
        """

        if not self.can_go_back:
            return False

        self._stack.pop()
        self._render()
        return True

    def _render(self) -> None:
        screen = self.current

        if screen is None:  # pragma: no cover - защита от пустого стека
            logger.warning("Попытка отрисовать пустой стек экранов")
            return

        self.page.clean()
        self.page.add(screen)
        screen.on_enter()
