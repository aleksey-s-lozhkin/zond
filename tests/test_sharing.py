"""Тесты отправки шаблона наружу.

Шаблон — обычный CSV, и человеку нужно передать его коллеге или забрать на
компьютер, чтобы поправить. Поэтому отправка идёт тем же механизмом, что и
протоколы, но со своим источником: путь к исходному файлу.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from tests.helpers import collect_texts, complete_inspection
from zond.app.app import ZondApp
from zond.ui.screens.upload_screen import UploadScreen


def load_template(app: ZondApp, path: Path, choose_file) -> None:
    choose_file(path)
    asyncio.run(app.pick_template())


def stub_picker(application: ZondApp, path: Path) -> None:
    """Подменить диалог выбора для конкретного экземпляра приложения.

    Фикстура ``choose_file`` привязана к своему экземпляру, поэтому для
    мобильного приложения подмена делается отдельно.
    """

    from tests.fakes import FakeFilePickerFile

    async def _pick_files(**_kwargs):
        return [FakeFilePickerFile(path)]

    application.file_picker.pick_files = _pick_files


def test_template_knows_its_source_file(app: ZondApp, sample_template: Path, choose_file) -> None:
    load_template(app, sample_template, choose_file)

    template = app.state.template

    assert template is not None
    assert Path(template.source_path) == sample_template


def test_template_is_shared_by_its_source_path(
    mobile_app: ZondApp,
    sample_template: Path,
) -> None:
    mobile_app.start()
    stub_picker(mobile_app, sample_template)
    asyncio.run(mobile_app.pick_template())

    asyncio.run(mobile_app.share_template())

    assert mobile_app.share.files == [str(sample_template)]


def test_sharing_without_template_reports_error(app: ZondApp) -> None:
    asyncio.run(app.share_template())

    assert app.page.dialogs


def test_sharing_missing_file_reports_error(
    app: ZondApp,
    sample_template: Path,
    choose_file,
    tmp_path: Path,
) -> None:
    """Шаблон загружен, а файла уже нет — говорим об этом прямо."""

    copy = tmp_path / "copy.csv"
    copy.write_text(sample_template.read_text(encoding="utf-8"), encoding="utf-8")

    load_template(app, copy, choose_file)
    copy.unlink()

    asyncio.run(app.share_template())

    assert app.page.dialogs


def test_start_screen_has_share_button(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    load_template(app, sample_template, choose_file)

    labels = collect_texts(app.navigator.current.content)

    assert "Отправить шаблон" in labels


def test_report_button_says_send_on_mobile(
    mobile_app: ZondApp,
    sample_template: Path,
) -> None:
    """На телефоне система не открывает file:// — файл уходит в «Поделиться»."""

    mobile_app.start()
    stub_picker(mobile_app, sample_template)
    asyncio.run(mobile_app.pick_template())
    mobile_app.start_inspection("Насос Н-12", "Иванов И.И.")
    complete_inspection(mobile_app)
    mobile_app.generate_pdf()
    mobile_app.navigator.current.refresh()

    labels = collect_texts(mobile_app.navigator.current.content)

    assert "Отправить PDF" in labels


def test_report_button_says_open_on_desktop(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос Н-12", "Иванов И.И.")
    complete_inspection(app)
    app.generate_pdf()
    app.navigator.current.refresh()

    labels = collect_texts(app.navigator.current.content)

    assert "Открыть PDF" in labels


def test_history_card_shows_concrete_numbers(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """«Все проверки на этом устройстве» ничего не сообщает."""

    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос Н-12", "Иванов И.И.")
    app.save_draft()
    app.restart()

    labels = collect_texts(UploadScreen(app).content)

    assert any("Незаконченных: 1" in label for label in labels)
    assert not any("Все проверки на этом устройстве" in label for label in labels)


def test_finished_count_is_shown(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос Н-12", "Иванов И.И.")
    complete_inspection(app)
    app.restart()

    labels = collect_texts(UploadScreen(app).content)

    assert any("Завершённых: 1" in label for label in labels)
