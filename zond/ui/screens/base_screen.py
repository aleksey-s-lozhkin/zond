from abc import ABC, abstractmethod

import flet as ft


class BaseScreen(ABC):

    def __init__(self, app):
        self.app = app
        self.page = app.page

    @abstractmethod
    def build(self) -> ft.Control:
        """Возвращает корневой элемент экрана."""
        raise NotImplementedError