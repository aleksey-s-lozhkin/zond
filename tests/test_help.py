"""Тесты справки.

Справка — часть интерфейса, а не документ: она должна открываться с рабочего
экрана и отвечать на те вопросы, из-за которых её открыли. Поэтому
проверяется, что на экране есть все три ответа — с чего начать, откуда взять
шаблон и куда попадают протоколы.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import flet as ft

from tests.fakes import FakeStoragePaths
from tests.helpers import collect_texts
from zond.app.app import ZondApp
from zond.services.json_storage import JsonStorage
from zond.ui.screens.help_screen import HelpScreen
from zond.ui.screens.upload_screen import UploadScreen


def help_texts(app: ZondApp) -> list[str]:
    screen = HelpScreen(app)

    return collect_texts(screen.content)


def test_help_opens_from_start_screen(app: ZondApp) -> None:
    app.start()
    app.open_help()

    assert isinstance(app.navigator.current, HelpScreen)


def test_help_returns_to_start_screen(app: ZondApp) -> None:
    app.start()
    app.open_help()
    app.navigator.back()

    assert isinstance(app.navigator.current, UploadScreen)


def test_help_explains_how_to_start(app: ZondApp) -> None:
    texts = help_texts(app)

    assert "С чего начать" in texts
    assert any("Выберите шаблон проверки" in text for text in texts)
    assert any("«Завершить»" in text for text in texts)


def test_help_explains_where_templates_come_from(app: ZondApp) -> None:
    texts = help_texts(app)

    assert "Откуда взять шаблон" in texts
    assert any("уже внутри приложения" in text for text in texts)
    assert any("CSV" in text for text in texts)


def test_help_explains_where_protocols_go(app: ZondApp) -> None:
    texts = help_texts(app)

    assert "Куда сохраняются протоколы" in texts
    assert any("Поделиться" in text for text in texts)
    assert app.export_hint() in texts


def test_help_shows_export_folder_after_mobile_prepare(
    mobile_app: ZondApp,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """В справке тот же путь, что показан на стартовом экране."""

    documents = tmp_path / "Documents"
    documents.mkdir()
    monkeypatch.setattr("zond.app.app.PUBLIC_DOCUMENTS_DIR", documents)
    mobile_app.storage_paths = FakeStoragePaths(documents=tmp_path / "data")

    asyncio.run(mobile_app.prepare())

    assert "Документы/ЗОНД" in help_texts(mobile_app)


def test_help_explains_marks(app: ZondApp) -> None:
    texts = help_texts(app)

    assert "Обозначения" in texts
    assert any("обязательное поле" in text for text in texts)
    assert any("несоответствие" in text for text in texts)


def test_help_has_back_button(app: ZondApp) -> None:
    app.start()

    from tests.helpers import find_control

    assert find_control(HelpScreen(app), ft.IconButton) is not None


def test_storage_accepts_separate_protocol_folder(
    sample_template: Path,
    tmp_path: Path,
) -> None:
    """Каталог протоколов можно задать отдельно от данных проверок."""

    from zond.services.inspection_factory import InspectionFactory
    from zond.services.template_loader import TemplateLoader

    storage = JsonStorage(tmp_path / "root", pdf_dir=tmp_path / "out")
    inspection = InspectionFactory.create(
        TemplateLoader().load(sample_template),
        "Объект",
        "Исполнитель",
    )

    assert storage.pdf_dir == tmp_path / "out"
    assert storage.pdf_path(inspection).parent == tmp_path / "out"
    assert storage.inspections_dir == tmp_path / "root" / "inspections"
