"""Тесты файлового хранилища проверок."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest

from zond.models.inspection import utcnow
from zond.services.errors import StorageError
from zond.services.inspection_factory import InspectionFactory
from zond.services.json_storage import JsonStorage
from zond.services.template_loader import TemplateLoader


@pytest.fixture
def store(tmp_path: Path) -> JsonStorage:
    return JsonStorage(tmp_path / "reports")


@pytest.fixture
def inspection(sample_template: Path):
    template = TemplateLoader().load(sample_template)
    return InspectionFactory.create(template, "Насос Н-12", "Иванов И.И.")


# ------------------------------------------------------------------- запись


def test_save_creates_parent_directories(store: JsonStorage, inspection) -> None:
    target = store.root / "nested" / "deep" / "file.json"

    store.save(inspection, target)

    assert target.exists()


def test_saved_file_is_valid_utf8_json(store: JsonStorage, inspection) -> None:
    path = store.finalize(inspection)

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["object_name"] == "Насос Н-12"
    assert payload["format_version"] == 3


def test_cyrillic_is_not_escaped(store: JsonStorage, inspection) -> None:
    path = store.finalize(inspection)

    assert "Насос Н-12" in path.read_text(encoding="utf-8")


def test_file_name_contains_template_slug(store: JsonStorage, inspection) -> None:
    path = store.finalize(inspection)

    assert "sample" in path.name
    assert path.suffix == ".json"
    assert path.parent == store.inspections_dir


def test_atomic_write_leaves_no_temp_files(store: JsonStorage, inspection) -> None:
    store.finalize(inspection)

    leftovers = [item.name for item in store.inspections_dir.iterdir() if item.suffix == ".tmp"]

    assert leftovers == []


def test_save_overwrites_existing_file(store: JsonStorage, inspection) -> None:
    path = store.save(inspection, store.inspections_dir / "fixed.json")
    inspection.object_name = "Другое"

    store.save(inspection, path)

    assert json.loads(path.read_text(encoding="utf-8"))["object_name"] == "Другое"


def test_save_reports_os_error(tmp_path: Path, inspection) -> None:
    store = JsonStorage(tmp_path / "reports")
    blocker = tmp_path / "reports"
    blocker.write_text("не каталог", encoding="utf-8")

    with pytest.raises(StorageError):
        store.save(inspection, blocker / "file.json")


# ------------------------------------------------------------------ загрузка


def test_round_trip_through_disk(store: JsonStorage, inspection) -> None:
    inspection.set_value("object_number", "INV-1")
    inspection.mark_finished()

    path = store.finalize(inspection)
    restored = store.load(path)

    assert restored.to_dict() == inspection.to_dict()


def test_load_missing_file(store: JsonStorage) -> None:
    with pytest.raises(StorageError, match="не найден"):
        store.load(store.root / "nope.json")


def test_load_broken_json(store: JsonStorage, tmp_path: Path) -> None:
    broken = store.root / "broken.json"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text("{ это не json", encoding="utf-8")

    with pytest.raises(StorageError, match="корректным JSON"):
        store.load(broken)


def test_load_valid_json_with_wrong_shape(store: JsonStorage) -> None:
    path = store.root / "wrong.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"format_version": 2, "items": []}', encoding="utf-8")

    with pytest.raises(StorageError):
        store.load(path)


# ----------------------------------------------------------------- черновики


def test_draft_lives_in_drafts_dir(store: JsonStorage, inspection) -> None:
    path = store.save_draft(inspection)

    assert path.parent == store.drafts_dir
    assert path.name == f"{inspection.inspection_id}.json"


def test_finalize_removes_draft(store: JsonStorage, inspection) -> None:
    draft = store.save_draft(inspection)

    assert draft.exists()

    inspection.mark_finished()
    store.finalize(inspection)

    assert not draft.exists()
    assert len(list(store.inspections_dir.glob("*.json"))) == 1


def test_discard_draft_is_safe_when_missing(store: JsonStorage, inspection) -> None:
    store.discard_draft(inspection)  # не должно бросать


# ------------------------------------------------------------------- история


def test_list_stored_returns_drafts_first(store: JsonStorage, sample_template: Path) -> None:
    template = TemplateLoader().load(sample_template)
    now = utcnow()

    finished = InspectionFactory.create(template, "Завершённая", "A")
    finished.started_at = now - timedelta(hours=2)
    finished.mark_finished(now - timedelta(hours=1))
    store.finalize(finished)

    draft = InspectionFactory.create(template, "Черновик", "Б")
    draft.started_at = now - timedelta(hours=3)
    store.save_draft(draft)

    entries = store.list_stored()

    assert [entry.is_draft for entry in entries] == [True, False]
    assert entries[0].title == "Черновик"


def test_list_stored_metadata(store: JsonStorage, inspection) -> None:
    inspection.set_value("object_number", "INV-1")
    inspection.set_value("executor", "Петров")
    inspection.mark_finished()
    store.finalize(inspection)

    entry = store.list_stored()[0]

    assert entry.template_name == "sample"
    assert entry.executor == "Иванов И.И."
    assert entry.total == 12
    assert entry.answered == 2
    assert entry.status == "завершена"
    assert "заполнено 2/12" in entry.subtitle


def test_list_stored_skips_broken_files(store: JsonStorage, inspection) -> None:
    store.finalize(inspection)

    broken = store.inspections_dir / "broken.json"
    broken.write_text("{", encoding="utf-8")

    entries = store.list_stored()

    assert len(entries) == 1


def test_list_stored_on_empty_storage(store: JsonStorage) -> None:
    assert store.list_stored() == []


def test_delete_removes_file(store: JsonStorage, inspection) -> None:
    path = store.finalize(inspection)

    store.delete(path)

    assert not path.exists()
    assert store.list_stored() == []


def test_delete_missing_file_is_silent(store: JsonStorage) -> None:
    store.delete(store.root / "ghost.json")  # не должно бросать


# ---------------------------------------------------------------------- PDF


def test_pdf_path_matches_json_name(store: JsonStorage, inspection) -> None:
    inspection.mark_finished()

    assert store.pdf_path(inspection).stem == Path(store.file_name(inspection)).stem
    assert store.pdf_path(inspection).parent == store.pdf_dir


def test_ensure_dirs_creates_layout(store: JsonStorage) -> None:
    store.ensure_dirs()

    assert store.inspections_dir.is_dir()
    assert store.drafts_dir.is_dir()
    assert store.pdf_dir.is_dir()
