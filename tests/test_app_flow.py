"""Интеграционные тесты сквозного сценария."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from tests.helpers import complete_inspection, fill_screen, sample_value
from zond.app.app import ZondApp
from zond.services.json_storage import JsonStorage
from zond.ui.screens.base_screen import AppScreen
from zond.ui.screens.check_screen import CheckScreen
from zond.ui.screens.finish_screen import FinishScreen
from zond.ui.screens.history_screen import HistoryScreen
from zond.ui.screens.inspection_screen import InspectionScreen
from zond.ui.screens.upload_screen import UploadScreen


def load_template(app: ZondApp, path: Path, choose_file) -> None:
    choose_file(path)
    asyncio.run(app.pick_template())


# ------------------------------------------------------------- сквозной путь


def test_full_happy_path(app: ZondApp, sample_template: Path, choose_file) -> None:
    assert isinstance(app.navigator.current, UploadScreen)

    load_template(app, sample_template, choose_file)

    assert isinstance(app.navigator.current, CheckScreen)
    assert app.state.template.name == "sample"

    app.start_inspection("Насос Н-12", "Иванов И.И.")

    assert isinstance(app.navigator.current, InspectionScreen)
    assert app.state.inspection.object_name == "Насос Н-12"

    complete_inspection(app)

    assert isinstance(app.navigator.current, FinishScreen)

    inspection = app.state.inspection

    assert inspection.is_finished
    assert inspection.finished_at is not None
    assert not inspection.missing_required


def test_finished_inspection_is_saved_to_disk(
    app: ZondApp, sample_template: Path, choose_file
) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")
    complete_inspection(app)

    saved = list(app.storage.inspections_dir.glob("*.json"))

    assert len(saved) == 1

    payload = json.loads(saved[0].read_text(encoding="utf-8"))

    assert payload["finished_at"] is not None
    assert payload["format_version"] == 3
    assert len(payload["template"]["fields"]) == 12
    assert all(item["value"] is not None for item in payload["items"])


def test_draft_is_removed_after_finish(app: ZondApp, sample_template: Path, choose_file) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")

    screen = app.navigator.current
    assert isinstance(screen, InspectionScreen)

    fill_screen(app, screen)
    screen._go_next(None)

    assert len(list(app.storage.drafts_dir.glob("*.json"))) == 1

    complete_inspection(app)

    assert list(app.storage.drafts_dir.glob("*.json")) == []


def test_values_survive_group_navigation(app: ZondApp, sample_template: Path, choose_file) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")

    screen = app.navigator.current
    assert isinstance(screen, InspectionScreen)

    fill_screen(app, screen)
    first_values = {control.field.name: control.value for control in screen.field_controls}

    screen._go_next(None)

    back = app.navigator.current
    assert isinstance(back, InspectionScreen)

    back._go_back(None)

    restored = app.navigator.current
    assert isinstance(restored, InspectionScreen)

    for control in restored.field_controls:
        assert control.value == first_values[control.field.name]


def test_back_from_first_group_returns_to_template_screen(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """С первой группы «Назад» ведёт к сведениям о шаблоне и сохраняет черновик."""

    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")

    screen = app.navigator.current
    assert isinstance(screen, InspectionScreen)

    control = screen.field_controls[0]
    control.set_value(sample_value(control.field))

    screen._go_back(None)

    assert isinstance(app.navigator.current, CheckScreen)
    assert app.state.inspection.get_item(control.field.name).value == control.value
    assert len(list(app.storage.drafts_dir.glob("*.json"))) == 1


def test_progress_widget_tracks_answers(app: ZondApp, sample_template: Path, choose_file) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("", "")

    screen = app.navigator.current
    assert isinstance(screen, InspectionScreen)

    assert screen.progress._bar.value == 0.0
    assert screen.progress._counter.value == "0/12"

    control = screen.field_controls[0]
    control.set_value(sample_value(control.field))
    screen._field_changed(control)

    assert screen.progress._bar.value > 0.0
    assert screen.progress._counter.value == "1/12"


# ------------------------------------------------------------- валидация


def test_missing_required_blocks_advance(app: ZondApp, sample_template: Path, choose_file) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("", "")

    screen = app.navigator.current
    assert isinstance(screen, InspectionScreen)

    screen._go_next(None)

    assert app.page.dialogs, "ожидался диалог с перечнем незаполненных полей"
    assert app.state.current_group_index == 0
    assert screen.field_controls[0].input.error == "Обязательное поле"


def test_wrong_number_format_blocks_advance(
    app: ZondApp, sample_template: Path, choose_file
) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")

    screen = app.navigator.current
    assert isinstance(screen, InspectionScreen)

    for control in screen.field_controls:
        control.set_value(sample_value(control.field))

    temperature_like = screen.field_controls[0]
    temperature_like.set_value("   ")
    screen._go_next(None)

    assert app.page.dialogs


def test_walk_through_all_groups_and_finish(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """Заполнение всех шагов подряд приводит к экрану итогов."""

    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")

    visited: list[str] = []

    for _ in range(4):
        screen = app.navigator.current

        if isinstance(screen, FinishScreen):
            break

        assert isinstance(screen, InspectionScreen)
        visited.append(screen.app.state.current_group)

        fill_screen(app, screen)
        screen._go_next(None)

    assert isinstance(app.navigator.current, FinishScreen)
    assert visited == [
        "Общие сведения",
        "Паспортные данные",
        "Результаты осмотра",
        "Заключение",
    ]


# ------------------------------------------------------------ сохранение/загрузка


def test_history_lists_finished_inspection(
    app: ZondApp, sample_template: Path, choose_file
) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")
    complete_inspection(app)

    app.open_history()

    assert isinstance(app.navigator.current, HistoryScreen)

    entries = app.storage.list_stored()

    assert len(entries) == 1
    assert entries[0].title == "Насос"
    assert entries[0].status == "завершена"


def test_resume_finished_inspection_opens_summary(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")
    complete_inspection(app)

    entry = app.storage.list_stored()[0]

    app.restart()

    assert isinstance(app.navigator.current, UploadScreen)

    app.resume_inspection(entry)

    assert isinstance(app.navigator.current, FinishScreen)
    assert app.state.inspection.is_finished


def test_resume_draft_opens_first_incomplete_group(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")

    screen = app.navigator.current
    assert isinstance(screen, InspectionScreen)

    fill_screen(app, screen)
    screen._go_next(None)

    entry = app.storage.list_stored()[0]

    assert entry.is_draft

    app.restart()
    app.resume_inspection(entry)

    assert isinstance(app.navigator.current, InspectionScreen)
    assert app.state.current_group == "Паспортные данные"


def test_open_inspection_from_json_file(app: ZondApp, sample_template: Path, choose_file) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")
    complete_inspection(app)

    saved = next(app.storage.inspections_dir.glob("*.json"))
    app.restart()

    choose_file(saved)
    asyncio.run(app.pick_inspection())

    assert isinstance(app.navigator.current, FinishScreen)


def test_open_broken_inspection_file_shows_error(
    app: ZondApp,
    tmp_path: Path,
    choose_file,
) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{ это не json", encoding="utf-8")

    choose_file(broken)
    asyncio.run(app.pick_inspection())

    assert app.page.dialogs
    assert isinstance(app.navigator.current, UploadScreen)


def test_delete_stored_inspection(app: ZondApp, sample_template: Path, choose_file) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")
    complete_inspection(app)

    app.open_history()
    entry = app.storage.list_stored()[0]

    app.delete_stored(entry)

    assert app.storage.list_stored() == []
    assert app.state.inspection is None


# ------------------------------------------------------------------ отчёты


def test_pdf_report_is_generated(app: ZondApp, sample_template: Path, choose_file) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")
    complete_inspection(app)

    path = app.generate_pdf()

    assert path is not None
    assert path.exists()
    assert path.read_bytes()[:5] == b"%PDF-"
    assert path.parent == app.storage.pdf_dir


def test_open_path_launches_url(app: ZondApp, launcher, tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("x", encoding="utf-8")

    asyncio.run(app.open_path(target))

    assert launcher.urls
    assert launcher.urls[0].startswith("file://")


def test_open_missing_path_shows_error(app: ZondApp, launcher, tmp_path: Path) -> None:
    asyncio.run(app.open_path(tmp_path / "nope.txt"))

    assert app.page.dialogs
    assert launcher.urls == []


def test_open_path_reports_when_system_cannot_open(app: ZondApp, launcher, tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("x", encoding="utf-8")
    launcher.can_launch = False

    asyncio.run(app.open_path(target))

    assert app.page.dialogs
    assert launcher.urls == []


def test_open_path_is_a_coroutine_function() -> None:
    """Регрессия: page.launch_url устарел и стал корутиной, из-за чего PDF
    не открывался с предупреждением «coroutine was never awaited»."""

    import inspect

    assert inspect.iscoroutinefunction(ZondApp.open_path)


def test_async_event_handlers_are_real_coroutines() -> None:
    """Flet ждёт обработчик только если это корутина.

    ``lambda``, возвращающая корутину, не сработает: Flet проверяет
    ``inspect.iscoroutinefunction``, а для lambda она даёт False.
    """

    import inspect

    from zond.ui.screens.finish_screen import FinishScreen
    from zond.ui.screens.history_screen import HistoryScreen
    from zond.ui.screens.upload_screen import UploadScreen

    for method in (
        ZondApp.pick_template,
        ZondApp.pick_inspection,
        ZondApp.open_path,
        FinishScreen._open_pdf,
        HistoryScreen._make_pdf,
        UploadScreen._pick_template,
        UploadScreen._pick_inspection,
    ):
        assert inspect.iscoroutinefunction(method), method.__qualname__


# -------------------------------------------------------------- загрузка шаблона


def test_broken_template_shows_error_dialog(
    app: ZondApp,
    tmp_path: Path,
    choose_file,
) -> None:
    broken = tmp_path / "broken.csv"
    broken.write_text("label,type\nПоле,text\n", encoding="utf-8")

    choose_file(broken)
    asyncio.run(app.pick_template())

    assert app.page.dialogs
    assert isinstance(app.navigator.current, UploadScreen)
    assert app.state.template is None


def test_cancelled_file_choice_changes_nothing(app: ZondApp, cancel_file_choice) -> None:
    asyncio.run(app.pick_template())

    assert isinstance(app.navigator.current, UploadScreen)
    assert app.page.dialogs == []


def test_template_with_no_local_path_shows_error(app: ZondApp, storage: JsonStorage) -> None:
    class NoPathFile:
        name = "web.csv"
        path = None

    async def _pick_files(**_kwargs):
        return [NoPathFile()]

    app.file_picker.pick_files = _pick_files

    asyncio.run(app.pick_template())

    assert app.page.dialogs
    assert app.state.template is None


def test_loading_new_template_resets_progress(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")

    screen = app.navigator.current
    assert isinstance(screen, InspectionScreen)

    fill_screen(app, screen)
    screen._go_next(None)

    assert app.state.current_group_index == 1

    app.restart()
    load_template(app, sample_template, choose_file)

    assert app.state.current_group_index == 0
    assert app.state.inspection is None


def test_new_template_while_in_progress_asks_confirmation(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")

    choose_file(sample_template)
    asyncio.run(app.pick_template())

    # Диалог подтверждения показан, шаблон ещё не перезагружен.
    assert app.page.dialogs
    assert isinstance(app.navigator.current, InspectionScreen)


def test_metadata_prefills_matching_template_fields(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос Н-12", "Петров П.П.")

    inspection = app.state.inspection

    assert inspection.get_item("object_number").value == "Насос Н-12"
    assert inspection.get_item("executor").value == "Петров П.П."


def test_restart_clears_session(app: ZondApp, sample_template: Path, choose_file) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")

    app.restart()

    assert isinstance(app.navigator.current, UploadScreen)
    assert app.state.inspection is None
    assert app.state.template is None


def test_draft_autosave_marks_saved(app: ZondApp, sample_template: Path, choose_file) -> None:
    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос", "Иванов")

    screen = app.navigator.current
    assert isinstance(screen, InspectionScreen)

    fill_screen(app, screen)
    screen._go_next(None)

    assert not app.state.is_modified


# ------------------------------------------------------------------ навигация


def test_navigator_stack(app: ZondApp, sample_template: Path, choose_file) -> None:
    assert app.navigator.depth == 1
    assert not app.navigator.can_go_back

    load_template(app, sample_template, choose_file)

    assert app.navigator.depth == 2
    assert app.navigator.can_go_back

    assert app.navigator.back() is True
    assert isinstance(app.navigator.current, UploadScreen)
    assert app.navigator.back() is False


def test_all_screens_share_one_contract() -> None:
    """Каждый экран принимает только объект приложения."""

    from zond.ui.screens.base_screen import AppScreen as Screen

    for screen_class in (
        UploadScreen,
        CheckScreen,
        InspectionScreen,
        FinishScreen,
        HistoryScreen,
    ):
        assert issubclass(screen_class, Screen)

    import inspect

    for screen_class in (UploadScreen, CheckScreen, InspectionScreen, FinishScreen):
        parameters = list(inspect.signature(screen_class.__init__).parameters)

        assert parameters == ["self", "app"], parameters


def test_screen_has_no_reserved_build_method() -> None:
    """``build`` у Flet-контрола вызывается самим фреймворком."""

    assert not hasattr(AppScreen, "build") or "build" not in AppScreen.__dict__
    assert "compose" in AppScreen.__dict__
