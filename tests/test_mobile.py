"""Тесты подготовки приложения к работе на мобильном устройстве.

На телефоне поведение отличается в трёх местах: каталог рядом с приложением
доступен только для чтения, файловый диалог не отдаёт путь к выбранному файлу,
а ссылку ``file://`` нельзя открыть другим приложением. Эти отличия и
проверяются.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import flet as ft
import pytest

from tests.fakes import FakePage, FakeStoragePaths
from tests.helpers import collect_texts
from zond.app.app import ZondApp
from zond.app.platform import has_local_files, is_desktop, is_mobile
from zond.services.json_storage import JsonStorage
from zond.services.sample_templates import (
    available_samples,
    sample_subtitle,
    sample_title,
    samples_dir,
)
from zond.ui.screens.upload_screen import UploadScreen


def make_file(name: str, content: bytes):
    """Заглушка выбранного файла с содержимым и без пути."""

    class Picked:
        path = None
        bytes = content

        def __init__(self) -> None:
            self.name = name
            self.size = len(content)

    return Picked()


def picker_returning(files, recorder: dict):
    async def pick_files(**kwargs):
        recorder.update(kwargs)
        return files

    return pick_files


# ------------------------------------------------------------- платформа


@pytest.mark.parametrize(
    "platform",
    [ft.PagePlatform.ANDROID, ft.PagePlatform.ANDROID_TV, ft.PagePlatform.IOS],
)
def test_mobile_platforms(platform: ft.PagePlatform) -> None:
    page = FakePage()
    page.platform = platform

    assert is_mobile(page)
    assert not is_desktop(page)
    assert not has_local_files(page)


@pytest.mark.parametrize(
    "platform",
    [ft.PagePlatform.MACOS, ft.PagePlatform.WINDOWS, ft.PagePlatform.LINUX],
)
def test_desktop_platforms(platform: ft.PagePlatform) -> None:
    page = FakePage()
    page.platform = platform

    assert is_desktop(page)
    assert not is_mobile(page)
    assert has_local_files(page)


def test_unknown_platform_is_treated_as_desktop() -> None:
    """Веб-режим и тесты: ограничений мобильной песочницы нет."""

    page = FakePage()
    page.platform = None

    assert is_desktop(page)
    assert not is_mobile(page)


# --------------------------------------------------------- каталог данных


def test_prepare_moves_data_to_documents_on_mobile(
    mobile_app: ZondApp,
    tmp_path: Path,
) -> None:
    """Рядом с приложением писать нельзя, иначе не сохранится даже черновик."""

    asyncio.run(mobile_app.prepare())

    assert mobile_app.storage.root == tmp_path / "documents" / "reports"

    # Каталог действительно создаётся при первой записи.
    mobile_app.storage.ensure_dirs()

    assert mobile_app.storage.inspections_dir.is_dir()


def test_prepare_keeps_storage_on_desktop(app: ZondApp, storage: JsonStorage) -> None:
    asyncio.run(app.prepare())

    assert app.storage is storage


def test_prepare_tolerates_missing_documents_dir(mobile_app: ZondApp) -> None:
    mobile_app.storage_paths = FakeStoragePaths(None)

    asyncio.run(mobile_app.prepare())

    assert mobile_app.storage.root.name == "reports"


def test_prepare_tolerates_platform_failure(mobile_app: ZondApp) -> None:
    paths = FakeStoragePaths()
    paths.available = False
    mobile_app.storage_paths = paths

    asyncio.run(mobile_app.prepare())  # не должно бросать


# ----------------------------------------------------------- выбор файла


def test_mobile_pick_file_requests_content(mobile_app: ZondApp, tmp_path: Path) -> None:
    """В песочнице пути нет, поэтому файл запрашивается вместе с содержимым."""

    recorder: dict = {}
    payload = "order;name;label;type\n1;a;Поле;text\n".encode()
    mobile_app.file_picker.pick_files = picker_returning(
        [make_file("template.csv", payload)], recorder
    )

    path = asyncio.run(mobile_app._pick_file(["csv"], "Тест"))

    assert recorder["with_data"] is True
    assert recorder["allowed_extensions"] is None
    assert path is not None
    assert path.read_bytes() == payload
    assert path.parent == mobile_app.storage.root / "incoming"


def test_mobile_picked_file_is_a_valid_template(mobile_app: ZondApp) -> None:
    payload = Path("templates/sample.csv").read_bytes()
    mobile_app.file_picker.pick_files = picker_returning([make_file("sample.csv", payload)], {})

    path = asyncio.run(mobile_app._pick_file(["csv"], "Тест"))

    assert path is not None

    template = mobile_app.template_loader.load(path)

    assert len(template.fields) == 12


def test_desktop_pick_file_uses_local_path(app: ZondApp, tmp_path: Path) -> None:
    from tests.fakes import FakeFilePickerFile

    recorder: dict = {}
    target = tmp_path / "template.csv"
    target.write_text("order;name;label;type\n1;a;Поле;text\n", encoding="utf-8")

    app.file_picker.pick_files = picker_returning([FakeFilePickerFile(target)], recorder)

    path = asyncio.run(app._pick_file(["csv"], "Тест"))

    assert recorder["with_data"] is False
    assert recorder["allowed_extensions"] == ["csv"]
    assert path == target


def test_pick_file_without_content_reports_error(mobile_app: ZondApp) -> None:
    class Empty:
        name = "пусто.csv"
        path = None
        bytes = None

    mobile_app.file_picker.pick_files = picker_returning([Empty()], {})

    path = asyncio.run(mobile_app._pick_file(["csv"], "Тест"))

    assert path is None
    assert mobile_app.page.dialogs


def test_cancelled_pick_returns_none(mobile_app: ZondApp) -> None:
    async def cancelled(**_kwargs):
        return []

    mobile_app.file_picker.pick_files = cancelled

    assert asyncio.run(mobile_app._pick_file(["csv"], "Тест")) is None
    assert mobile_app.page.dialogs == []


# --------------------------------------------------------- открытие файла


def test_mobile_shares_file_instead_of_opening(mobile_app: ZondApp, tmp_path: Path) -> None:
    """Ссылку file:// на телефоне открыть нельзя — отдаём в «Поделиться»."""

    target = tmp_path / "protocol.pdf"
    target.write_bytes(b"%PDF-1.4")

    asyncio.run(mobile_app.open_path(target))

    assert mobile_app.share.files == [str(target)]
    assert mobile_app.url_launcher.urls == []


def test_mobile_share_failure_is_reported(mobile_app: ZondApp, tmp_path: Path) -> None:
    target = tmp_path / "protocol.pdf"
    target.write_bytes(b"%PDF-1.4")
    mobile_app.share.fail = True

    asyncio.run(mobile_app.open_path(target))

    assert mobile_app.page.dialogs


def test_desktop_opens_file_with_url_launcher(app: ZondApp, launcher, tmp_path: Path) -> None:
    target = tmp_path / "protocol.pdf"
    target.write_bytes(b"%PDF-1.4")

    asyncio.run(app.open_path(target))

    assert launcher.urls
    assert app.share.files == []


def test_missing_file_is_reported_on_mobile(mobile_app: ZondApp, tmp_path: Path) -> None:
    asyncio.run(mobile_app.open_path(tmp_path / "нет.pdf"))

    assert mobile_app.page.dialogs
    assert mobile_app.share.files == []


# ------------------------------------------------------- встроенные образцы


def test_samples_are_available() -> None:
    samples = available_samples()

    assert samples, "в поставке нет ни одного образца шаблона"
    assert all(path.suffix == ".csv" for path in samples)


def test_samples_directory_is_found() -> None:
    directory = samples_dir()

    assert directory is not None
    assert directory.name == "templates"


def test_sample_titles_and_subtitles() -> None:
    for path in available_samples():
        assert sample_title(path)
        assert "полей" in sample_subtitle(path)


def test_unknown_sample_gets_file_name_as_title(tmp_path: Path) -> None:
    assert sample_title(tmp_path / "неизвестный.csv") == "неизвестный"


def test_sample_chooser_shows_dialog(app: ZondApp) -> None:
    app.choose_sample()

    assert app.page.dialogs


def test_sample_loader_is_a_coroutine_function(app: ZondApp) -> None:
    """Flet дожидается только настоящих корутин."""

    import inspect

    handler = app._sample_loader(Path("templates/sample.csv"))

    assert inspect.iscoroutinefunction(handler)


def test_sample_loader_loads_template(app: ZondApp) -> None:
    handler = app._sample_loader(Path("templates/sample.csv"))

    asyncio.run(handler(None))

    assert app.state.template is not None
    assert len(app.state.template.fields) == 12


def test_upload_screen_offers_samples(app: ZondApp) -> None:
    screen = UploadScreen(app)
    labels = collect_texts(screen.content)

    assert any("образец" in label.lower() for label in labels)


# --------------------------------------------------------------- оболочка


def test_screens_use_safe_area(app: ZondApp) -> None:
    """Иначе на телефоне интерфейс уходит под строку состояния."""

    screen = UploadScreen(app)

    assert isinstance(screen.content, ft.SafeArea)
    assert screen.content.expand is True


def test_main_entry_point_is_async() -> None:
    """flet build вызывает main(page) из модуля main."""

    import inspect

    import main as entry_point

    assert inspect.iscoroutinefunction(entry_point.main)
