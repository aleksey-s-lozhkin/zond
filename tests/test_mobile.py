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

from tests.conftest import PROJECT_ROOT
from tests.fakes import (
    FakePage,
    FakeShare,
    FakeStoragePaths,
    FakeUrlLauncher,
)
from tests.helpers import collect_texts
from zond.app.app import INCOMING_KEEP, ZondApp
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


def test_protocols_go_to_public_documents(
    mobile_app: ZondApp,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Протокол ищут в «Документах», а не в служебной папке приложения."""

    documents = tmp_path / "Documents"
    documents.mkdir()
    monkeypatch.setattr("zond.app.app.PUBLIC_DOCUMENTS_DIR", documents)

    mobile_app.storage_paths = FakeStoragePaths(
        documents=tmp_path / "data",
        external=tmp_path / "external",
    )

    asyncio.run(mobile_app.prepare())

    assert mobile_app.storage.pdf_dir == documents / "ЗОНД" / "Протоколы"
    assert mobile_app.storage.pdf_dir.is_dir()
    assert mobile_app.export_hint() == "Документы/ЗОНД/Протоколы"

    # Данные проверок остаются в каталоге приложения.
    assert mobile_app.storage.inspections_dir.parent == tmp_path / "external" / "reports"


def test_protocols_stay_in_app_dir_without_documents(
    mobile_app: ZondApp,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Если общей папки нет, протоколы не теряются."""

    monkeypatch.setattr("zond.app.app.PUBLIC_DOCUMENTS_DIR", tmp_path / "нет-такой")

    asyncio.run(mobile_app.prepare())

    assert mobile_app.export_dir is None
    assert mobile_app.storage.pdf_dir == mobile_app.storage.root / "pdf"
    assert mobile_app.export_hint() == str(mobile_app.storage.pdf_dir)


def test_documents_are_not_used_when_write_denied(
    mobile_app: ZondApp,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Общий каталог выбирается только после проверки записью."""

    documents = tmp_path / "Documents"
    documents.mkdir()
    monkeypatch.setattr("zond.app.app.PUBLIC_DOCUMENTS_DIR", documents)
    monkeypatch.setattr("zond.app.app._is_writable", lambda directory: False)

    assert mobile_app._shared_dir("Протоколы") is None


def test_desktop_uses_documents_when_available(
    app: ZondApp,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """На настольной платформе протоколы тоже уходят в «Документы»."""

    documents = tmp_path / "Документы"
    documents.mkdir()
    monkeypatch.setattr("zond.app.app.HOME_DOCUMENTS_DIR", documents)

    asyncio.run(app.prepare())

    assert app.export_dir == documents / "ЗОНД" / "Протоколы"


def test_desktop_keeps_project_reports_without_documents(
    app: ZondApp,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Нет общей папки — протоколы остаются в проекте."""

    monkeypatch.setattr("zond.app.app.HOME_DOCUMENTS_DIR", tmp_path / "нет-такой")

    asyncio.run(app.prepare())

    assert app.export_dir is None
    assert app.storage.pdf_dir == app.storage.root / "pdf"


def test_library_goes_to_documents_when_available(
    app: ZondApp,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Библиотека шаблонов тоже живёт в общей папке: туда кладут файлы с ПК."""

    documents = tmp_path / "Документы"
    documents.mkdir()
    monkeypatch.setattr("zond.app.app.HOME_DOCUMENTS_DIR", documents)

    asyncio.run(app.prepare())

    assert app.library.root == documents / "ЗОНД" / "Шаблоны"
    assert app.library.root.is_dir()


def test_library_falls_back_to_app_folder(
    app: ZondApp,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("zond.app.app.HOME_DOCUMENTS_DIR", tmp_path / "нет-такой")

    asyncio.run(app.prepare())

    assert app.library.root == app.storage.root / "templates"


def test_location_label_shows_export_folder(
    mobile_app: ZondApp,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """В интерфейсе — понятная часть пути, а не вся строка целиком."""

    documents = tmp_path / "Documents"
    documents.mkdir()
    monkeypatch.setattr("zond.app.app.PUBLIC_DOCUMENTS_DIR", documents)

    asyncio.run(mobile_app.prepare())

    label = mobile_app.location_label(mobile_app.storage.pdf_dir / "protocol.pdf")

    assert label == "Документы/ЗОНД/Протоколы"


def test_location_label_shows_folder_on_mobile(mobile_app: ZondApp) -> None:
    """На телефоне — только папка: длинное имя файла не помещается."""

    label = mobile_app.location_label(mobile_app.storage.inspections_dir / "check.json")

    assert label == "inspections"


def test_location_label_shows_full_path_on_desktop(app: ZondApp) -> None:
    """В проводнике нужен полный путь, и на настольном экране он помещается."""

    path = app.storage.inspections_dir / "check.json"

    assert app.location_label(path) == str(path)


def test_android_prefers_visible_external_storage(
    mobile_app: ZondApp,
    tmp_path: Path,
) -> None:
    """Внутренний каталог документов недоступен пользователю, внешний — виден
    по USB и в файловых менеджерах, поэтому на Android он в приоритете."""

    mobile_app.storage_paths = FakeStoragePaths(
        documents=tmp_path / "documents",
        external=tmp_path / "external",
    )

    asyncio.run(mobile_app.prepare())

    assert mobile_app.storage.root == tmp_path / "external" / "reports"


def test_android_falls_back_to_documents_when_external_missing(
    mobile_app: ZondApp,
    tmp_path: Path,
) -> None:
    mobile_app.storage_paths = FakeStoragePaths(
        documents=tmp_path / "documents",
        external=None,
    )

    asyncio.run(mobile_app.prepare())

    assert mobile_app.storage.root == tmp_path / "documents" / "reports"


def test_ios_does_not_use_external_storage(
    mobile_page: FakePage,
    storage: JsonStorage,
    tmp_path: Path,
) -> None:
    """На iOS внешнего каталога приложения не существует."""

    mobile_page.platform = ft.PagePlatform.IOS

    application = ZondApp(mobile_page, storage=storage)
    application.url_launcher = FakeUrlLauncher()
    application.storage_paths = FakeStoragePaths(
        documents=tmp_path / "documents",
        external=tmp_path / "external",
    )
    application.share = FakeShare()

    asyncio.run(application.prepare())

    assert application.storage.root == tmp_path / "documents" / "reports"


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
    assert recorder["allowed_extensions"] == ["csv"]
    assert path is not None
    assert path.read_bytes() == payload
    assert path.parent == mobile_app.storage.root / "incoming"


def test_mobile_picked_file_is_a_valid_template(mobile_app: ZondApp) -> None:
    payload = Path("tests/data/sample.csv").read_bytes()
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


def test_file_filter_is_enabled(mobile_app: ZondApp) -> None:
    """Расширения фильтруются только при типе CUSTOM.

    С типом ANY Flet молча игнорирует allowed_extensions, и в диалоге видны
    все файлы подряд — и JSON, и CSV. Ошибка была незаметна, потому что
    фильтр просто не применялся ни на одной платформе.
    """

    recorder: dict = {}
    mobile_app.file_picker.pick_files = picker_returning([], recorder)

    asyncio.run(mobile_app._pick_file(["csv"], "Тест"))

    assert recorder["file_type"] is ft.FilePickerFileType.CUSTOM
    assert recorder["allowed_extensions"] == ["csv"]


def test_inspection_picker_asks_for_json(mobile_app: ZondApp) -> None:
    recorder: dict = {}
    mobile_app.file_picker.pick_files = picker_returning([], recorder)

    asyncio.run(mobile_app._pick_file(["json"], "Проверка"))

    assert recorder["allowed_extensions"] == ["json"]


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


def test_shared_file_carries_path_and_mime_type(
    mobile_app: ZondApp,
    tmp_path: Path,
) -> None:
    """В «Поделиться» уходит ShareFile, а не строка с путём.

    На строке настоящий сервис падает с «Null check operator used on a null
    value»: платформа ждёт объект с полем path. Ошибка воспроизвелась только
    на устройстве, поэтому проверяется и здесь.
    """

    target = tmp_path / "protocol.pdf"
    target.write_bytes(b"%PDF-1.4")

    asyncio.run(mobile_app.open_path(target))

    assert len(mobile_app.share.items) == 1

    shared = mobile_app.share.items[0]

    assert isinstance(shared, ft.ShareFile)
    assert shared.path == str(target)
    assert shared.mime_type == "application/pdf"
    assert shared.name == "protocol.pdf"


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [(".pdf", "application/pdf"), (".json", "application/json"), (".csv", "text/csv")],
)
def test_mime_type_by_extension(suffix: str, expected: str) -> None:
    from zond.app.app import _mime_type

    assert _mime_type(Path(f"file{suffix}")) == expected


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


def test_json_is_shared_with_its_own_mime_type(
    mobile_app: ZondApp,
    tmp_path: Path,
) -> None:
    target = tmp_path / "inspection.json"
    target.write_text("{}", encoding="utf-8")

    asyncio.run(mobile_app.open_path(target))

    assert mobile_app.share.items[0].mime_type == "application/json"


def test_missing_file_is_reported_on_mobile(mobile_app: ZondApp, tmp_path: Path) -> None:
    asyncio.run(mobile_app.open_path(tmp_path / "нет.pdf"))

    assert mobile_app.page.dialogs
    assert mobile_app.share.files == []


# ------------------------------------------------------- встроенные образцы


def test_educational_example_is_not_bundled() -> None:
    """Учебный пример — фикстура тестов, а не образец поставки.

    Он нужен для разбора формата и проверок, но в приложении показываться
    не должен: там только рабочие шаблоны.
    """

    names = {path.name for path in available_samples()}

    assert "sample.csv" not in names
    assert not (samples_dir() / "sample.csv").exists()


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
        subtitle = sample_subtitle(path)

        assert sample_title(path)
        assert path.name in subtitle
        assert "групп" in subtitle


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (1, "поле"),
        (2, "поля"),
        (5, "полей"),
        (11, "полей"),
        (12, "полей"),
        (21, "поле"),
        (22, "поля"),
    ],
)
def test_plural_forms(count: int, expected: str) -> None:
    """Русские формы числа: 1 поле, 2 поля, 5 полей, 11 полей, 21 поле."""

    from zond.services.sample_templates import _plural

    assert _plural(count, "поле", "поля", "полей") == expected


def test_unknown_sample_gets_file_name_as_title(tmp_path: Path) -> None:
    assert sample_title(tmp_path / "неизвестный.csv") == "неизвестный"


def test_start_screen_opens_the_library(app: ZondApp) -> None:
    """Стартовый экран ведёт в библиотеку шаблонов, а не в диалог."""

    from zond.ui.screens.templates_screen import TemplatesScreen

    app.start()
    app.open_templates()

    assert isinstance(app.navigator.current, TemplatesScreen)


def test_library_screen_lists_templates(app: ZondApp) -> None:

    app.start()
    app.open_templates()

    names = collect_texts(app.navigator.current.content)

    assert any("Добавить шаблон из файла" in label for label in names)
    assert any("Шаблонов пока нет" in label or "шаблон" in label for label in names)


def test_upload_screen_has_single_template_entry(app: ZondApp) -> None:
    """Загрузка шаблона — одно действие, значит и карточка одна."""

    screen = UploadScreen(app)
    labels = collect_texts(screen.content)

    assert any("Выбрать шаблон проверки" in label for label in labels)
    assert any("Свой CSV-файл или готовый пример" in label for label in labels)
    assert not any("Готовые шаблоны" in label for label in labels)
    assert not any("Свой шаблон из файла" in label for label in labels)


def test_upload_screen_groups_actions(app: ZondApp) -> None:
    screen = UploadScreen(app)
    labels = collect_texts(screen.content)

    assert any("НАЧАТЬ ПРОВЕРКУ" in label for label in labels)
    assert any("ПРОДОЛЖИТЬ" in label for label in labels)


def test_upload_screen_links_to_help(app: ZondApp) -> None:
    from tests.helpers import find_control

    screen = UploadScreen(app)
    labels = collect_texts(screen.content)

    assert "Справка" in labels
    assert find_control(screen, ft.TextButton) is not None


# --------------------------------------------------------------- оболочка


def test_screens_use_safe_area(app: ZondApp) -> None:
    """Иначе на телефоне интерфейс уходит под строку состояния."""

    screen = UploadScreen(app)

    assert isinstance(screen.content, ft.SafeArea)
    assert screen.content.expand is True


def test_build_entry_point_starts_the_app() -> None:
    """Модуль ``main`` обязан запускать приложение сам.

    Загрузчик собранного приложения импортирует модуль и не вызывает
    ``main(page)``. Если модуль только объявит функцию, приложение стартует и
    сразу завершится — штатно, без сообщений об ошибке. Именно так выглядел
    первый запуск на Android, поэтому проверка важна.

    Импортировать модуль в тесте нельзя: он запускает приложение. Поэтому
    проверяется его исходный текст.
    """

    source = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")

    assert "from zond.ects import run" in source
    assert "\nrun()" in source


def test_run_is_a_synchronous_entry_point() -> None:
    """``run`` — обычная функция: её вызывает и консоль, и модуль main."""

    import inspect

    from zond.ects import run

    assert not inspect.iscoroutinefunction(run)


def test_main_builds_ui_and_schedules_storage_refresh() -> None:
    """Интерфейс строится синхронно, а каталог данных уточняется задачей.

    Пустая страница к концу main(page) приводила к тому, что приложение
    закрывалось сразу после запуска.
    """

    from tests.fakes import FakePage
    from zond.ects import main as ects_main

    page = FakePage()
    page.tasks.clear()

    ects_main(page)

    assert page.controls, "стартовый экран должен быть добавлен синхронно"
    assert len(page.tasks) == 1
    assert page.tasks[0][0].__name__ == "prepare"


def test_prepare_refreshes_screen_when_storage_changes(
    mobile_app: ZondApp,
    tmp_path: Path,
) -> None:
    """После смены каталога экран перерисовывается: на нём показан путь."""

    from tests.fakes import FakeStoragePaths

    mobile_app.storage_paths = FakeStoragePaths(
        documents=tmp_path / "documents",
        external=tmp_path / "external",
    )
    mobile_app.start()

    before = mobile_app.navigator.current

    asyncio.run(mobile_app.prepare())

    assert mobile_app.navigator.current is not before
    assert mobile_app.storage.root == tmp_path / "external" / "reports"


# ------------------------------------------------- копии выбранных файлов


def test_incoming_copies_are_bounded(mobile_app: ZondApp, tmp_path: Path) -> None:
    """Копии выбранных файлов не копятся бесконечно.

    Копия нужна, чтобы отправить шаблон: путь к исходному файлу после выбора
    недоступен. Но без ограничения каждая копия остаётся на диске навсегда.
    """

    incoming = mobile_app.storage.root / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)

    for index in range(INCOMING_KEEP + 5):
        path = incoming / f"{index:04d}_шаблон.csv"
        path.write_text("order;name;label;type\n", encoding="utf-8")

    ZondApp._prune_incoming(incoming)

    left = sorted(path.name for path in incoming.iterdir())

    assert len(left) == INCOMING_KEEP
    # Удаляются самые старые, свежие остаются.
    assert "0000_шаблон.csv" not in left
    assert f"{INCOMING_KEEP + 4:04d}_шаблон.csv" in left


def test_pruning_survives_unreadable_directory(app: ZondApp, tmp_path: Path) -> None:
    """Отсутствие каталога не должно ронять выбор файла."""

    ZondApp._prune_incoming(tmp_path / "нет-такого")


def test_picked_file_is_not_added_to_samples(mobile_app: ZondApp) -> None:
    """Выбранный файл не становится примером.

    Примеры лежат внутри приложения и не меняются: выбранный файл только
    копируется в рабочий каталог и разбирается.
    """

    payload = Path("tests/data/sample.csv").read_bytes()
    mobile_app.file_picker.pick_files = picker_returning([make_file("свой.csv", payload)], {})

    path = asyncio.run(mobile_app._pick_file(["csv"], "Тест"))

    assert path is not None
    assert "incoming" in path.parts
    assert path not in available_samples()
    assert all(path.name != sample.name for sample in available_samples())
