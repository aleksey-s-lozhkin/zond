import flet as ft


class ZondNavigator:
    """ Управляет переключением экранов. """

    def __init__(self, page: ft.Page):

        self.page = page


    def show(self, screen: ft.Control):

        self.page.clean()

        self.page.add(screen)

        self.page.update()