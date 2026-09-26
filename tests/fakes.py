"""Тестовые двойники Flet.

``FletTestApp`` из комплекта Flet требует Flutter-инструментарий и
скриншотные эталоны, поэтому для быстрых тестов логики используется лёгкая
заглушка страницы. Она повторяет только тот интерфейс ``ft.Page``, которым
реально пользуется приложение.
"""

from __future__ import annotations

from pathlib import Path

import flet as ft


class FakeWindow:
    """Заглушка окна приложения."""

    def __init__(self) -> None:
        self.width: int | None = None
        self.height: int | None = None
        self.min_width: int | None = None
        self.min_height: int | None = None


class FakePage:
    """Минимальная замена :class:`flet.Page`."""

    def __init__(self) -> None:
        self.services: list = []
        self.controls: list = []
        self.window = FakeWindow()

        # По умолчанию настольная платформа: так тесты проверяют обычное
        # поведение, а мобильное задаётся явно.
        self.platform = ft.PagePlatform.MACOS

        self.title: str | None = None
        self.theme_mode = None
        self.theme = None
        self.bgcolor: str | None = None
        self.padding = None
        self.spacing = None

        self.dialogs: list = []
        self.updates = 0
        self.tasks: list[tuple] = []

    # ----------------------------------------------------- управление деревом

    def clean(self) -> None:
        self.controls.clear()

    def add(self, *controls) -> None:
        self.controls.extend(controls)

    def update(self, *controls) -> None:
        self.updates += 1

    # ------------------------------------------------------------- задания

    def run_task(self, handler, *args, **kwargs):
        """Запомнить корутину, отправленную задачей страницы."""

        self.tasks.append((handler, args, kwargs))
        return

    # --------------------------------------------------------------- диалоги

    def show_dialog(self, dialog) -> None:
        self.dialogs.append(dialog)

    def pop_dialog(self) -> None:
        if self.dialogs:
            self.dialogs.pop()


class FakeFilePickerFile:
    """Заглушка выбранного файла."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self.name = Path(path).name
        self.size = Path(path).stat().st_size if Path(path).exists() else 0


class FakeUrlLauncher:
    """Заглушка :class:`flet.UrlLauncher`.

    Настоящий сервис асинхронный, поэтому заглушка повторяет его контракт:
    методы — корутины. Если приложение забудет ``await``, тест это покажет.
    """

    def __init__(self) -> None:
        self.urls: list[str] = []
        self.can_launch = True

    async def can_launch_url(self, url) -> bool:
        return self.can_launch

    async def launch_url(self, url, *args, **kwargs) -> None:
        self.urls.append(str(url))


class FakeStoragePaths:
    """Заглушка :class:`flet.StoragePaths`."""

    def __init__(
        self,
        documents: Path | None = None,
        external: Path | None = None,
    ) -> None:
        self.documents = documents
        self.external = external
        self.available = True

    def _resolve(self, value: Path | None) -> str | None:
        if not self.available:
            raise RuntimeError("платформа недоступна")

        return None if value is None else str(value)

    async def get_application_documents_directory(self) -> str | None:
        return self._resolve(self.documents)

    async def get_external_storage_directory(self) -> str | None:
        return self._resolve(self.external)


class FakeShare:
    """Заглушка :class:`flet.Share`."""

    def __init__(self) -> None:
        self.files: list[str] = []
        self.fail = False

    async def share_files(self, files, **_kwargs) -> None:
        if self.fail:
            raise RuntimeError("меню «Поделиться» недоступно")

        self.files.extend(str(item) for item in files)
