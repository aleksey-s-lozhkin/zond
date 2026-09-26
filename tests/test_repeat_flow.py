"""Тесты сценария повторного выезда через интерфейс.

Проверяется путь целиком: выбрать шаблон, увидеть прошлые проверки, перенести
значения, разобрать замечания и попасть в форму. Именно этот сценарий описан
как основной при эксплуатации, поэтому он проверяется отдельно от модели.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import flet as ft

from tests.helpers import collect_texts, complete_inspection, sample_value
from zond.app.app import ZondApp
from zond.models.verdict import NOT_RESOLVED, RESOLVED
from zond.ui.screens.check_screen import REPEAT_NONE
from zond.ui.screens.defects_screen import DefectsScreen
from zond.ui.screens.finish_screen import FinishScreen
from zond.ui.screens.inspection_screen import InspectionScreen


def radio_labels(screen) -> list[str]:
    """Подписи радиокнопок выбора прошлой проверки.

    :class:`flet.Radio` хранит подпись строкой, а не контролом
    :class:`flet.Text`, поэтому общий обход текстов их не видит.
    """

    group = screen.repeat_group

    if group is None:
        return []

    return [str(option.label) for option in group.content.controls]


def load_template(app: ZondApp, path: Path, choose_file) -> None:
    choose_file(path)
    asyncio.run(app.pick_template())


def finish_one(app: ZondApp) -> None:
    """Пройти проверку до конца и вернуться на стартовый экран."""

    complete_inspection(app)
    app.restart()


#: Замечания, оставляемые в прошлой проверке: нужны два, чтобы проверить
#: частичный разбор.
DEFECTS = {"condition": "Требует ремонта", "vibration": "Критическая"}


def fill_preserving_defect(app: ZondApp) -> None:
    """Пройти форму, оставив замечание по состоянию оборудования.

    Обычное заполнение подставило бы первый вариант списка, то есть
    «Отличное», и замечание исчезло бы — а от него зависит шаг разбора.
    """

    guard = 0

    while True:
        guard += 1

        if guard > 50:  # pragma: no cover - защита от зацикливания
            raise AssertionError("Форма не завершилась за 50 шагов")

        screen = app.navigator.current

        if isinstance(screen, FinishScreen):
            return

        assert isinstance(screen, InspectionScreen), f"неожиданный экран: {screen!r}"

        for control in screen.field_controls:
            if control.field.name in DEFECTS:
                control.set_value(DEFECTS[control.field.name])
            else:
                control.set_value(sample_value(control.field))

            screen._field_changed(control)

        screen._go_next(None)


def prepare_previous(app: ZondApp, sample_template: Path, choose_file):
    """Создать завершённую проверку с замечанием и вернуть её."""

    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос Н-12", "Иванов И.И.")
    fill_preserving_defect(app)
    app.restart()

    return next(entry.inspection for entry in app.storage.list_stored() if not entry.is_draft)


# --------------------------------------------------- список прошлых проверок


def test_no_repeat_card_without_finished_checks(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """Пока проверок нет, выбирать нечего."""

    load_template(app, sample_template, choose_file)

    screen = app.navigator.current
    labels = collect_texts(screen.content)

    assert not any("Повторная проверка" in label for label in labels)


def test_repeat_card_lists_finished_checks(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    prepare_previous(app, sample_template, choose_file)
    load_template(app, sample_template, choose_file)

    screen = app.navigator.current
    labels = collect_texts(screen.content)

    assert any("Повторная проверка" in label for label in labels)
    assert any("несоответствий" in label for label in radio_labels(screen))
    assert any("Начать с пустой формы" in label for label in radio_labels(screen))


def test_candidates_are_only_finished_checks_of_this_template(
    app: ZondApp,
    sample_template: Path,
    choose_file,
    tmp_path: Path,
) -> None:
    """Черновики и чужие шаблоны в список не попадают."""

    prepare_previous(app, sample_template, choose_file)

    # Черновик по тому же шаблону.
    load_template(app, sample_template, choose_file)
    app.start_inspection("Черновой объект", "")
    app.save_draft()
    app.restart()

    load_template(app, sample_template, choose_file)

    candidates = app.repeat_candidates()

    assert len(candidates) == 1
    assert candidates[0].object_name == "Насос Н-12"


def test_candidates_are_empty_on_start_screen(app: ZondApp) -> None:
    assert app.repeat_candidates() == []


# -------------------------------------------------------------- перенос


def test_empty_form_starts_without_previous(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    prepare_previous(app, sample_template, choose_file)
    load_template(app, sample_template, choose_file)

    screen = app.navigator.current

    assert screen.repeat_group.value == REPEAT_NONE

    screen._start(None)

    inspection = app.state.inspection

    assert not inspection.is_repeat
    assert inspection.get_item("model").value is None


def test_selected_previous_is_carried_over(
    app: ZondApp,
    sample_template: Path,
    choose_file,
    tmp_path: Path,
) -> None:
    previous = prepare_previous(app, sample_template, choose_file)
    load_template(app, sample_template, choose_file)

    screen = app.navigator.current
    screen.repeat_group.value = previous.inspection_id
    screen._start(None)

    inspection = app.state.inspection

    assert inspection.is_repeat
    assert inspection.previous_inspection_id == previous.inspection_id


def test_start_button_label_changes_with_selection(
    app: ZondApp,
    sample_template: Path,
    choose_file,
    tmp_path: Path,
) -> None:
    previous = prepare_previous(app, sample_template, choose_file)
    load_template(app, sample_template, choose_file)

    screen = app.navigator.current

    assert screen.start_button.content.value == "Начать проверку"

    screen.repeat_group.value = previous.inspection_id
    screen._choose_repeat(None)

    assert screen.start_button.content.value == "Начать с прошлой"


# -------------------------------------------------------- разбор замечаний


def test_defects_screen_opens_before_the_form(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    previous = prepare_previous(app, sample_template, choose_file)
    load_template(app, sample_template, choose_file)

    screen = app.navigator.current
    screen.repeat_group.value = previous.inspection_id
    screen._start(None)

    assert isinstance(app.navigator.current, DefectsScreen)


def test_defects_screen_shows_previous_answer(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    previous = prepare_previous(app, sample_template, choose_file)
    load_template(app, sample_template, choose_file)

    screen = app.navigator.current
    screen.repeat_group.value = previous.inspection_id
    screen._start(None)

    labels = collect_texts(app.navigator.current.content)

    assert any("Требует ремонта" in label for label in labels)
    assert any("Осталось разобрать" in label for label in labels)


def test_continue_is_blocked_until_all_resolved(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    previous = prepare_previous(app, sample_template, choose_file)
    load_template(app, sample_template, choose_file)

    check = app.navigator.current
    check.repeat_group.value = previous.inspection_id
    check._start(None)

    screen = app.navigator.current

    assert screen.continue_button.disabled

    for name, selector in screen.selectors.items():
        selector.value = RESOLVED
        screen._choose(name, _event(RESOLVED))

    assert not screen.continue_button.disabled

    screen._continue(None)

    assert isinstance(app.navigator.current, InspectionScreen)
    assert app.state.inspection.get_item("condition").resolution == RESOLVED


def test_partial_resolution_keeps_button_disabled(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """Пока есть неразобранное замечание, дальше не пускаем."""

    previous = prepare_previous(app, sample_template, choose_file)
    load_template(app, sample_template, choose_file)

    check = app.navigator.current
    check.repeat_group.value = previous.inspection_id
    check._start(None)

    screen = app.navigator.current
    names = list(screen.selectors)

    screen._choose(names[0], _event(NOT_RESOLVED))

    assert screen.continue_button.disabled


def test_no_defects_screen_when_previous_is_clean(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """Если замечаний не было, лишний шаг не показывается."""

    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос Н-12", "Иванов И.И.")
    complete_inspection(app)
    app.restart()

    load_template(app, sample_template, choose_file)

    check = app.navigator.current
    previous = app.repeat_candidates()[0]
    check.repeat_group.value = previous.inspection_id
    check._start(None)

    assert isinstance(app.navigator.current, InspectionScreen)


def test_repeat_values_are_visible_in_the_form(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """После разбора замечаний форма открывается с прошлыми ответами."""

    previous = prepare_previous(app, sample_template, choose_file)
    load_template(app, sample_template, choose_file)

    check = app.navigator.current
    check.repeat_group.value = previous.inspection_id
    check._start(None)

    review = app.navigator.current

    for name, selector in review.selectors.items():
        selector.value = RESOLVED
        review._choose(name, _event(RESOLVED))

    review._continue(None)

    # Поле «Состояние» лежит в другой группе, поэтому смотрим саму проверку,
    # а не контролы первого шага формы.
    assert app.state.inspection.get_item("condition").value == "Требует ремонта"
    assert app.state.inspection.get_item("condition").resolution == RESOLVED


# ------------------------------------------------------------------ утилиты


class _event:
    """Событие изменения с нужным значением контрола."""

    def __init__(self, value: object) -> None:
        self.control = ft.Text(value=str(value))


def test_event_helper_works() -> None:
    assert _event("x").control.value == "x"
