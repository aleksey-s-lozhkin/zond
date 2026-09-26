"""Общие фикстуры тестов."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:  # pragma: no cover - зависит от запуска
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.fakes import FakeFilePickerFile, FakePage, FakeUrlLauncher  # noqa: E402
from zond.app.app import ZondApp  # noqa: E402
from zond.services.json_storage import JsonStorage  # noqa: E402

SAMPLE_TEMPLATE = PROJECT_ROOT / "templates" / "sample.csv"


@pytest.fixture
def page() -> FakePage:
    return FakePage()


@pytest.fixture
def storage(tmp_path: Path) -> JsonStorage:
    return JsonStorage(tmp_path / "reports")


@pytest.fixture
def app(page: FakePage, storage: JsonStorage) -> ZondApp:
    application = ZondApp(page, storage=storage)

    # Настоящий UrlLauncher требует живого сеанса Flet.
    application.url_launcher = FakeUrlLauncher()
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
