import flet as ft

from zond.app.app import ZondApp
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def main(page: ft.Page):

    app = ZondApp(page)

    app.start()


if __name__ == "__main__":

    ft.run(
        main,
        assets_dir=str(BASE_DIR / "assets")
    )