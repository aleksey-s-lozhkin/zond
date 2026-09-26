"""Тесты библиотеки шаблонов.

Шаблоны — рабочий материал: пользователь собирает базу постепенно, и всё, что
в ней лежит, можно удалить, включая примеры. Поэтому проверяется и раскладка
примеров при первом запуске, и то, что удалённый пример не возвращается.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zond.services.template_library import MARKER_NAME, TemplateLibrary


@pytest.fixture
def examples(tmp_path: Path) -> Path:
    """Каталог с примерами, как он поставляется в приложении."""

    source = tmp_path / "examples"
    source.mkdir()

    for name in ("kip.csv", "tso.csv"):
        (source / name).write_text(
            "order;name;label;type;group\n10;a;Поле;text;Группа\n",
            encoding="utf-8",
        )

    return source


@pytest.fixture
def library(tmp_path: Path, examples: Path) -> TemplateLibrary:
    return TemplateLibrary(tmp_path / "library", examples_dir=examples)


# ------------------------------------------------------------- раскладка


def test_ensure_creates_directory(library: TemplateLibrary) -> None:
    library.ensure()

    assert library.root.is_dir()


def test_examples_are_seeded_on_first_run(library: TemplateLibrary) -> None:
    """Примеры копируются в библиотеку: иначе их нельзя ни удалить, ни править."""

    library.ensure()

    names = {entry.name for entry in library.list_entries()}

    assert names == {"kip", "tso"}


def test_seeding_happens_once(library: TemplateLibrary) -> None:
    library.ensure()
    before = (library.root / MARKER_NAME).read_text(encoding="utf-8")

    library.ensure()

    assert (library.root / MARKER_NAME).read_text(encoding="utf-8") == before


def test_deleted_example_is_not_restored(library: TemplateLibrary) -> None:
    """Удалил — значит удалил: список принадлежит пользователю."""

    library.ensure()
    assert library.delete("kip")

    library.ensure()

    names = {entry.name for entry in library.list_entries()}

    assert names == {"tso"}


def test_new_example_appears_after_update(
    library: TemplateLibrary,
    examples: Path,
) -> None:
    """Новый пример из свежей версии приложения добавляется."""

    library.ensure()

    (examples / "new.csv").write_text(
        "order;name;label;type;group\n10;a;Поле;text;Группа\n",
        encoding="utf-8",
    )

    library.ensure()

    names = {entry.name for entry in library.list_entries()}

    assert names == {"kip", "new", "tso"}


def test_edited_example_is_not_overwritten(
    library: TemplateLibrary,
) -> None:
    """Пользователь мог поправить пример — затирать его нельзя."""

    library.ensure()

    edited = library.path_of("kip")
    edited.write_text("order;name;label;type;group\n10;a;Своё;text;Своя\n", encoding="utf-8")

    library.ensure()

    assert "Своё" in edited.read_text(encoding="utf-8")


def test_ensure_survives_missing_examples(tmp_path: Path) -> None:
    library = TemplateLibrary(tmp_path / "library", examples_dir=tmp_path / "нет-такой")

    library.ensure()

    assert library.list_entries() == []


def test_ensure_survives_unwritable_directory(tmp_path: Path) -> None:
    """Ошибка каталога не должна ронять запуск приложения."""

    blocked = tmp_path / "file"
    blocked.write_text("не каталог", encoding="utf-8")

    library = TemplateLibrary(blocked)
    library.ensure()

    assert library.list_entries() == []


# ---------------------------------------------------------------- список


def test_list_is_sorted_and_filtered(library: TemplateLibrary) -> None:
    library.ensure()

    (library.root / "заметка.txt").write_text("не шаблон", encoding="utf-8")
    (library.root / ".скрытый.csv").write_text("скрытый", encoding="utf-8")
    (library.root / "aaa.csv").write_text("order;name;label;type;group\n", encoding="utf-8")

    names = [entry.name for entry in library.list_entries()]

    assert names == ["aaa", "kip", "tso"]


def test_path_of_uses_suffix(library: TemplateLibrary) -> None:
    assert library.path_of("kip").name == "kip.csv"


# -------------------------------------------------------------- операции


def test_import_copies_file(library: TemplateLibrary, tmp_path: Path) -> None:
    """Выбранный из памяти шаблон остаётся в библиотеке."""

    source = tmp_path / "свой.csv"
    source.write_text("order;name;label;type;group\n10;a;Поле;text;Группа\n", encoding="utf-8")

    target = library.import_file(source)

    assert target is not None
    assert target == library.root / "свой.csv"
    assert target.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert "свой" in {entry.name for entry in library.list_entries()}


def test_import_replaces_same_name(library: TemplateLibrary, tmp_path: Path) -> None:
    """Правленый на компьютере шаблон заменяет прежний, а не плодит копию."""

    library.ensure()

    source = tmp_path / "kip.csv"
    source.write_text("order;name;label;type;group\n10;a;Новое;text;Гр\n", encoding="utf-8")

    library.import_file(source)

    assert "Новое" in library.path_of("kip").read_text(encoding="utf-8")
    assert len(library.list_entries()) == 2


def test_import_missing_file_reports_failure(library: TemplateLibrary, tmp_path: Path) -> None:
    assert library.import_file(tmp_path / "нет.csv") is None


def test_delete_removes_file(library: TemplateLibrary) -> None:
    library.ensure()

    assert library.delete("kip")
    assert not library.path_of("kip").exists()


def test_delete_missing_file_returns_false(library: TemplateLibrary) -> None:
    library.ensure()

    assert library.delete("нет-такого") is False


# ------------------------------------------------------------------ экран


def test_screen_lists_library(app) -> None:
    from tests.helpers import collect_texts
    from zond.ui.screens.templates_screen import TemplatesScreen

    app.library.ensure()
    app.open_templates()

    labels = collect_texts(app.navigator.current.content)

    assert isinstance(app.navigator.current, TemplatesScreen)
    assert any("Добавить шаблон из файла" in label for label in labels)


def test_deleting_template_updates_the_app(app) -> None:
    app.library.ensure()
    app.open_templates()

    entry = app.library.list_entries()[0]

    assert app.delete_template(entry)
    assert entry.name not in {item.name for item in app.library.list_entries()}


def test_delete_reports_failure_for_missing(app) -> None:
    from zond.services.template_library import LibraryEntry

    app.library.ensure()

    missing = LibraryEntry(path=app.library.root / "нет.csv")

    assert app.delete_template(missing) is False


def test_import_template_from_device(app, choose_file, sample_template: Path) -> None:
    """Выбранный файл попадает в библиотеку и сразу открывается."""

    import asyncio

    app.library.ensure()
    choose_file(sample_template)

    asyncio.run(app.import_template())

    names = {entry.name for entry in app.library.list_entries()}

    assert "sample" in names
    assert app.state.template is not None
    assert app.state.template.name == "sample"


# ------------------------------------------------------- имена примеров


def test_example_names_are_readable(app) -> None:
    """В библиотеке примеры названы по-человечески, а не техническими именами."""

    from zond.app.app import example_name

    name = example_name(Path("templates/kip_kranovyy_uzel_mg.csv"))

    assert name == "КИП кранового узла газопровода.csv"


def test_example_name_has_no_forbidden_characters(app) -> None:
    """Двоеточие в названии недопустимо в имени файла на Android и Windows."""

    from zond.app.app import example_name

    name = example_name(Path("templates/uaz_patriot_to.csv"))

    assert ":" not in name
    assert name.endswith(".csv")


def test_library_seeds_readable_names(tmp_path: Path, examples: Path) -> None:
    from zond.app.app import example_name

    library = TemplateLibrary(
        tmp_path / "library",
        examples_dir=examples,
        name_of=example_name,
    )
    library.ensure()

    assert library.path_of("kip").exists() or any(
        entry.path.suffix == ".csv" for entry in library.list_entries()
    )
    assert library.list_entries()
