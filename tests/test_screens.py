"""Дымовые тесты сборки экранов.

Каждый экран собирается без реальной страницы Flet: это ловит неверные
параметры контролов Flet, которые иначе проявились бы только при запуске.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fakes import FakePage
from tests.helpers import complete_inspection
from zond.app.app import ZondApp
from zond.services.json_storage import JsonStorage
from zond.services.template_loader import TemplateLoader
from zond.ui.components.buttons import (
    DangerButton,
    GhostButton,
    PrimaryButton,
    SecondaryButton,
    SuccessButton,
)
from zond.ui.components.cards import Badge, EmptyState, InfoRow, SectionCard
from zond.ui.components.headers import ScreenHeader
from zond.ui.components.progress import ProgressWidget
from zond.ui.screens.check_screen import CheckScreen
from zond.ui.screens.finish_screen import FinishScreen
from zond.ui.screens.history_screen import HistoryScreen
from zond.ui.screens.inspection_screen import InspectionScreen
from zond.ui.screens.upload_screen import UploadScreen

# ------------------------------------------------------------------ компоненты


def test_all_buttons_can_be_created() -> None:
    """Раньше кнопки падали: в Flet 0.86 у них нет параметра text."""

    assert PrimaryButton("A") is not None
    assert SecondaryButton("B") is not None
    assert SuccessButton("C") is not None
    assert DangerButton("D") is not None
    assert GhostButton("E") is not None


def test_success_button_uses_success_colour() -> None:
    from zond.ui.colors import AppColors

    assert SuccessButton("C").style.bgcolor == AppColors.SUCCESS


def test_progress_widget_ratio() -> None:
    widget = ProgressWidget("Заголовок", 1, 4)

    assert widget._bar.value == pytest.approx(0.25)


def test_progress_widget_handles_zero_total() -> None:
    assert ProgressWidget("Заголовок", 0, 0)._bar.value == 0.0


def test_progress_widget_clamps_overflow() -> None:
    assert ProgressWidget("Заголовок", 10, 4)._bar.value == 1.0


def test_progress_widget_updates_without_page() -> None:
    widget = ProgressWidget("Заголовок", 1, 4)
    widget.set_progress(3, 4)  # не должно бросать вне страницы

    assert widget._counter.value == "3/4"


def test_section_card_with_header() -> None:
    import flet as ft

    card = SectionCard(ft.Text("тело"), title="Заголовок", subtitle="Подзаголовок")

    assert card.content is not None
    assert card.border is not None


def test_info_row_and_badge_and_empty_state() -> None:
    assert InfoRow("Метка", "Значение") is not None
    assert Badge("статус") is not None
    assert EmptyState("Пусто", "Описание") is not None


def test_screen_header_with_and_without_back() -> None:
    import flet as ft

    assert ScreenHeader("Заголовок") is not None
    assert ScreenHeader("Заголовок", description="Описание", on_back=lambda e: None) is not None
    assert ScreenHeader("Заголовок", actions=[ft.Text("x")]) is not None


# --------------------------------------------------------------------- экраны


def test_upload_screen_builds(app: ZondApp) -> None:
    assert isinstance(app.navigator.current, UploadScreen)


def test_check_screen_builds(app: ZondApp, sample_template: Path) -> None:
    app.state.set_template(TemplateLoader().load(sample_template))

    screen = CheckScreen(app)

    assert screen.content is not None


def test_check_screen_without_template(page: FakePage, storage: JsonStorage) -> None:
    application = ZondApp(page, storage=storage)

    screen = CheckScreen(application)

    assert isinstance(screen.content, EmptyState)


def test_inspection_screen_without_inspection(page: FakePage, storage: JsonStorage) -> None:
    application = ZondApp(page, storage=storage)

    screen = InspectionScreen(application)

    assert isinstance(screen.content, EmptyState)


def test_inspection_screen_builds_fields(app: ZondApp, sample_template: Path) -> None:
    template = TemplateLoader().load(sample_template)
    app.state.set_template(template)

    from zond.services.inspection_factory import InspectionFactory

    app.state.set_inspection(InspectionFactory.create(template))

    screen = InspectionScreen(app)

    assert len(screen.field_controls) == 3
    assert screen.content is not None


def test_finish_screen_without_finished_inspection(page: FakePage, storage: JsonStorage) -> None:
    application = ZondApp(page, storage=storage)

    screen = FinishScreen(application)

    assert isinstance(screen.content, EmptyState)


def test_finish_screen_builds(app: ZondApp, sample_template: Path, choose_file) -> None:
    import asyncio

    choose_file(sample_template)

    asyncio.run(app.pick_template())
    app.start_inspection("Насос", "Иванов")

    complete_inspection(app)

    assert isinstance(app.navigator.current, FinishScreen)


def test_history_screen_empty(page: FakePage, storage: JsonStorage) -> None:
    application = ZondApp(page, storage=storage)

    screen = HistoryScreen(application)

    assert screen.content is not None


def test_history_screen_with_entries(app: ZondApp, sample_template: Path, choose_file) -> None:
    import asyncio

    choose_file(sample_template)
    asyncio.run(app.pick_template())
    app.start_inspection("Насос", "Иванов")
    complete_inspection(app)

    app.open_history()

    assert isinstance(app.navigator.current, HistoryScreen)
