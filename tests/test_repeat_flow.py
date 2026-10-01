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
from zond.models.verdict import RESOLVED
from zond.ui.screens.check_screen import REPEAT_NONE
from zond.ui.screens.finish_screen import FinishScreen
from zond.ui.screens.inspection_screen import InspectionScreen


def radio_labels(screen) -> list[str]:
    """Подписи строк выбора прошлой проверки.

    Обычный обход текстов их не видит: строка собирается из радиокнопки без
    подписи и отдельного текста, поэтому экран отдаёт варианты сам.
    """

    return [label for _value, label in screen.repeat_options()]


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

    assert screen.start_button.content.value == "Начать"

    screen.repeat_group.value = previous.inspection_id
    screen._choose_repeat(None)

    assert screen.start_button.content.value == "С прошлой"


# -------------------------------------------------------- разбор замечаний


def open_repeat(app: ZondApp, sample_template: Path, choose_file) -> None:
    """Выбрать прошлую проверку и начать повторную."""

    previous = prepare_previous(app, sample_template, choose_file)
    load_template(app, sample_template, choose_file)

    screen = app.navigator.current
    screen.repeat_group.value = previous.inspection_id
    screen._start(None)


def defect_texts(screen) -> list[str]:
    return [
        label
        for label in collect_texts(screen.content)
        if "Замечание прошлой проверки" in label or label.startswith("Было:")
    ]


def test_repeat_opens_the_form_itself(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """Замечания разбираются прямо в форме, отдельного шага нет.

    Отдельный экран заставлял проходить шаблон дважды: сначала разобрать
    замечания, потом заполнить форму.
    """

    open_repeat(app, sample_template, choose_file)

    assert isinstance(app.navigator.current, InspectionScreen)


def test_form_shows_the_whole_template(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """Открывается весь шаблон, а не только несоответствия."""

    open_repeat(app, sample_template, choose_file)

    template = app.state.template

    assert len(app.state.current_fields) == len(template.fields_in_group(template.groups[0]))


def test_previous_defect_is_shown_on_its_field(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    open_repeat(app, sample_template, choose_file)

    # Поле «Состояние» лежит не в первой группе: доходим до неё.
    screen = app.navigator.current
    seen: list[str] = []
    guard = 0

    while not seen and guard < 20:
        guard += 1
        seen = defect_texts(screen)

        if isinstance(app.navigator.current, FinishScreen):
            break

        screen._go_next(None)
        screen = app.navigator.current

        if not isinstance(screen, InspectionScreen):
            break

    assert seen, "замечание прошлой проверки не показано"
    # Именно значение, а не ссылка на метод: подсказка собирается из строки.
    assert any(label == "Было: Требует ремонта" for label in seen), seen
    assert not any("bound method" in label for label in seen)


def test_resolution_is_set_from_the_form(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    open_repeat(app, sample_template, choose_file)

    screen = app.navigator.current
    screen._set_resolution("condition", RESOLVED)

    assert app.state.inspection.get_item("condition").resolution == RESOLVED


def test_unresolved_defect_does_not_block_the_form(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """Форма открывается сразу: заполнять её можно и до разбора замечаний."""

    open_repeat(app, sample_template, choose_file)

    inspection = app.state.inspection

    assert inspection.pending_resolutions, "замечания должны быть неразобраны"
    assert isinstance(app.navigator.current, InspectionScreen)


def test_clean_previous_has_no_defect_block(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """Если замечаний не было, подсказок о них тоже нет."""

    load_template(app, sample_template, choose_file)
    app.start_inspection("Насос Н-12", "Иванов И.И.")
    complete_inspection(app)
    app.restart()

    load_template(app, sample_template, choose_file)

    check = app.navigator.current
    previous = app.repeat_candidates()[0]
    check.repeat_group.value = previous.inspection_id
    check._start(None)

    screen = app.navigator.current

    assert isinstance(screen, InspectionScreen)
    assert defect_texts(screen) == []


def test_repeat_values_are_visible_in_the_form(
    app: ZondApp,
    sample_template: Path,
    choose_file,
) -> None:
    """Прошлые ответы подставлены, править нужно только изменившееся."""

    open_repeat(app, sample_template, choose_file)

    assert app.state.inspection.get_item("condition").value == "Требует ремонта"


# ------------------------------------------------------------------ утилиты


class _event:
    """Событие изменения с нужным значением контрола."""

    def __init__(self, value: object) -> None:
        self.control = ft.Text(value=str(value))


def test_event_helper_works() -> None:
    assert _event("x").control.value == "x"
