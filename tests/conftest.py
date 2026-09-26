"""Общие фикстуры тестов."""

from __future__ import annotations

import sys
from pathlib import Path

import flet as ft
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:  # pragma: no cover - зависит от запуска
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.fakes import (  # noqa: E402
    FakeFilePickerFile,
    FakePage,
    FakeShare,
    FakeStoragePaths,
    FakeUrlLauncher,
)
from zond.app.app import ZondApp, example_name  # noqa: E402
from zond.services.json_storage import JsonStorage  # noqa: E402
from zond.services.template_library import TemplateLibrary  # noqa: E402

# Минимальный шаблон для тестов: 12 полей, 4 группы. Это техническая
# фикстура, а не образец поставки, поэтому лежит в тестовых данных.
SAMPLE_TEMPLATE = PROJECT_ROOT / "tests" / "data" / "sample.csv"


@pytest.fixture
def page() -> FakePage:
    return FakePage()


@pytest.fixture
def storage(tmp_path: Path) -> JsonStorage:
    return JsonStorage(tmp_path / "reports")


@pytest.fixture
def app(
    page: FakePage,
    storage: JsonStorage,
    tmp_path: Path,
    monkeypatch,
) -> ZondApp:
    application = ZondApp(page, storage=storage)

    # Библиотека шаблонов и общие каталоги не должны трогать домашний
    # каталог разработчика: всё уводится во временную папку.
    monkeypatch.setattr("zond.app.app.HOME_DOCUMENTS_DIR", tmp_path / "Documents")
    application.library = TemplateLibrary(
        tmp_path / "templates",
        examples_dir=PROJECT_ROOT / "templates",
        # Как в приложении: примеры получают читаемые имена файлов.
        name_of=example_name,
    )

    # Настоящие сервисы требуют живого сеанса Flet.
    application.url_launcher = FakeUrlLauncher()
    application.storage_paths = FakeStoragePaths()
    application.share = FakeShare()
    application.start()

    return application


@pytest.fixture
def launcher(app: ZondApp) -> FakeUrlLauncher:
    """Заглушка запуска файлов, установленная в приложении."""

    return app.url_launcher


@pytest.fixture
def sample_template() -> Path:
    return SAMPLE_TEMPLATE


@pytest.fixture
def choose_file(app: ZondApp):
    """Подменить диалог выбора файла на возврат заданного пути."""

    def _choose(path: str | Path) -> None:
        async def _pick_files(**_kwargs):
            return [FakeFilePickerFile(path)]

        app.file_picker.pick_files = _pick_files

    return _choose


@pytest.fixture
def cancel_file_choice(app: ZondApp) -> None:
    async def _pick_files(**_kwargs):
        return []

    app.file_picker.pick_files = _pick_files


@pytest.fixture
def mobile_page() -> FakePage:
    """Страница, притворяющаяся мобильным устройством."""

    page = FakePage()
    page.platform = ft.PagePlatform.ANDROID

    return page


@pytest.fixture
def mobile_app(mobile_page: FakePage, storage: JsonStorage, tmp_path: Path) -> ZondApp:
    """Приложение на мобильной платформе."""

    application = ZondApp(mobile_page, storage=storage)
    application.url_launcher = FakeUrlLauncher()
    application.storage_paths = FakeStoragePaths(tmp_path / "documents")
    application.share = FakeShare()

    return application
