"""Базовый экран приложения.

Все экраны имеют один контракт — ``Screen(app)`` — и получают доступ к
состоянию, хранилищу и навигатору через объект приложения. Раньше каждый экран
принимал свой набор аргументов, из-за чего, например, экран проверки не мог
вернуться назад.

.. warning::
   Метод сборки содержимого называется :meth:`AppScreen.compose`, а не
   ``build``: у :class:`flet.BaseControl` уже есть метод ``build``, который
   Flet вызывает сам при согласовании (reconciliation) контролов — до того,
   как экран получит ссылку на приложение.
"""

from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import flet as ft

from zond.ui.colors import AppColors

if TYPE_CHECKING:  # pragma: no cover - только для аннотаций
    from zond.app.app import ZondApp


class AppScreen(ft.Container, ABC):
    """Общая основа экранов."""

    def __init__(self, app: ZondApp) -> None:
        super().__init__(expand=True, bgcolor=AppColors.BACKGROUND, padding=0)
        self.app = app
        self.mount()

    def mount(self) -> None:
        """Собрать содержимое экрана.

        Содержимое оборачивается в :class:`flet.SafeArea`: на телефоне иначе
        часть интерфейса уходит под системную строку состояния и «бровь».
        На настольных платформах safe area ничего не меняет.
        """

        self.content = ft.SafeArea(content=self.compose(), expand=True)

    @abstractmethod
    def compose(self) -> ft.Control:
        """Вернуть корневой элемент экрана."""

        raise NotImplementedError

    def on_enter(self) -> None:
        """Хук, вызываемый навигатором после показа экрана."""

    def refresh(self) -> None:
        """Перерисовать экран."""

        self.mount()
        self.safe_update()

    def safe_update(self) -> None:
        """Обновить контрол, если он смонтирован.

        В тестах экраны собираются без реальной страницы Flet, и вызов
        ``update()`` бросил бы ``RuntimeError``.
        """

        with contextlib.suppress(RuntimeError):
            self.update()
