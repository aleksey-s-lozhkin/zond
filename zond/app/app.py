import flet as ft

from zond.app.state import ZondState
from zond.app.navigator import ZondNavigator
from zond.ui.colors import AppColors
from zond.ui.theme import build_theme
from zond.ui.screens.upload_screen import UploadScreen
from zond.ui.screens.check_screen import CheckScreen
from zond.services.template_loader import TemplateLoader
from zond.services.inspection_factory import InspectionFactory


class ZondApp:
    """ Главный объект приложения. """

    def __init__(self, page: ft.Page):

        self.page = page

        self.state = ZondState()

        self.template_loader = TemplateLoader()

        self.navigator = ZondNavigator(self.page)

        # FilePicker
        self.file_picker = ft.FilePicker()
        self.page.services.append(
            self.file_picker
        )

        self._configure_page()


    def _configure_page(self):

        self.page.title = "ЗОНД: ECTS"

        self.page.theme_mode = ft.ThemeMode.LIGHT

        self.page.theme = build_theme()

        self.page.bgcolor = AppColors.BACKGROUND

        self.page.padding = 0

        self.page.spacing = 0


        # Пока для desktop-теста

        self.page.window.width = 430

        self.page.window.height = 860

    def start(self):

        self.navigator.show(
            UploadScreen(
                on_upload=self.open_file_picker
            )
        )

    async def open_file_picker(self, e):
        print("OPEN PICKER")

        files = await self.file_picker.pick_files(
            allowed_extensions=["csv"],
            allow_multiple=False,
        )

        if not files:
            print("Файл не выбран")
            return

        file = files[0]

        print("Выбран файл:")
        print(file.name)
        print(file.path)

        try:
            template = self.template_loader.load(
                file.path
            )

        except Exception as ex:
            print(
                "Ошибка загрузки:",
                ex
            )
            return

        self.state.template = template
        self.state.inspection = InspectionFactory.create(
            template
        )

        print(
            len(self.state.inspection.items)
        )

        print(
            "Шаблон:",
            template.name
        )

        print(
            "Количество полей:",
            len(template.fields)
        )

        self.navigator.show(CheckScreen(self.state, self.navigator))

    # def on_file_selected(self, e):
    #
    #     if not e.files:
    #         return
    #
    #     file = e.files[0]
    #
    #     template = self.template_loader.load(file.path)
    #
    #     self.state.template = template
    #
    #     print(
    #         "Загружено полей:",
    #         len(template.fields)
    #     )
    #
    #     self.navigator.show(CheckScreen(self.state))
    #
    # def on_file_uploaded(self, e):
    #
    #     template = self.template_loader.load(file.path)
    #
    #     self.state.template = template
    #
    #     self.navigator.show(
    #         CheckScreen(
    #             self.state
    #         )
    #     )
