"""Построение элементов формы по описанию поля.

``FieldControl`` инкапсулирует ввод, подпись, подсказку, единицу измерения и
сообщение об ошибке, поэтому экран проверки не знает деталей конкретного типа
поля.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from datetime import date, datetime, time

import flet as ft

from zond.models.field import Field, FieldType
from zond.ui.colors import AppColors
from zond.ui.design import FontSize, Radius, Space

logger = logging.getLogger(__name__)

#: Формат даты для отображения пользователю.
DATE_DISPLAY_FORMAT = "%d.%m.%Y"

#: Варианты ввода даты, которые принимает парсер.
DATE_INPUT_FORMATS = ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")

#: Варианты ввода времени.
TIME_INPUT_FORMATS = ("%H:%M", "%H:%M:%S", "%H.%M")


def _safe_update(control: ft.Control) -> None:
    """Обновить контрол, если он смонтирован."""

    with contextlib.suppress(RuntimeError):
        control.update()


class FieldControl(ft.Column):
    """Поле формы с валидацией и отображением ошибок."""

    def __init__(
        self,
        field: Field,
        value: object | None = None,
        on_change: Callable[[FieldControl], None] | None = None,
        page: ft.Page | None = None,
    ) -> None:
        super().__init__(
            spacing=Space.XS,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.field = field
        self._on_change = on_change
        self._page = page

        self.input: ft.Control = self._create_input(value)

        controls: list[ft.Control] = []

        if field.type is not FieldType.CHECKBOX:
            controls.append(self._build_label())

        controls.append(self._inset(self.input))

        if field.description:
            controls.append(
                ft.Text(
                    field.description,
                    size=FontSize.CAPTION,
                    color=AppColors.TEXT_SECONDARY,
                )
            )

        self.controls = controls

    # ------------------------------------------------------------- разметка

    def _build_label(self) -> ft.Control:
        """Подпись поля.

        Собирается одним :class:`flet.Text` из фрагментов: строка из
        отдельных контролов в ``Row`` не переносится и обрезается на узком
        окне, а ``Text`` переносит текст по доступной ширине.
        """

        spans = [
            ft.TextSpan(
                self.field.title,
                style=ft.TextStyle(
                    size=FontSize.BODY,
                    weight=ft.FontWeight.W_600,
                    color=AppColors.TEXT,
                ),
            )
        ]

        if self.field.required:
            spans.append(
                ft.TextSpan(
                    " *",
                    style=ft.TextStyle(
                        size=FontSize.SUBTITLE,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.PRIMARY,
                    ),
                )
            )

        if self.field.unit:
            spans.append(
                ft.TextSpan(
                    f"  ({self.field.unit})",
                    style=ft.TextStyle(
                        size=FontSize.CAPTION,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                )
            )

        return ft.Text(
            spans=spans,
            tooltip="Обязательное поле" if self.field.required else None,
        )

    def _inset(self, control: ft.Control) -> ft.Control:
        """Выделить обязательное поле.

        У полей ввода заливка и рамка задаются при создании; у флажка
        собственного фона нет, поэтому обязательный флажок оборачивается в
        тонированный контейнер.
        """

        if not self.field.required or self.field.type is not FieldType.CHECKBOX:
            return control

        return ft.Container(
            padding=ft.Padding(
                left=Space.SM,
                top=Space.XS,
                right=Space.SM,
                bottom=Space.XS,
            ),
            bgcolor=AppColors.PRIMARY_SOFT,
            border=ft.Border.all(1, AppColors.PRIMARY_BORDER),
            border_radius=Radius.SM,
            content=control,
        )

    def _input_style(self) -> dict:
        """Заливка и рамка поля.

        Обязательные поля получают мягкую заливку и синюю рамку: звёздочка в
        подписи на маленьком экране почти не заметна, а цвет видно сразу.
        Цвет ошибки остаётся красным, поэтому состояния не путаются.
        """

        if self.field.required:
            return {
                "filled": True,
                "fill_color": AppColors.PRIMARY_SOFT,
                "border_color": AppColors.PRIMARY_BORDER,
                "focused_border_color": AppColors.PRIMARY,
            }

        return {
            "filled": True,
            "fill_color": AppColors.SURFACE,
            "border_color": AppColors.BORDER,
            "focused_border_color": AppColors.PRIMARY,
        }

    def _create_input(self, value: object | None) -> ft.Control:
        field = self.field
        common = {
            **self._input_style(),
            "border_radius": Radius.SM,
            "dense": True,
        }

        if field.type is FieldType.CHECKBOX:
            return ft.Checkbox(
                value=bool(value),
                label=field.title,
                on_change=lambda e: self._emit_change(),
            )

        if field.type is FieldType.DROPDOWN:
            return ft.Dropdown(
                value=self._as_text(value) or None,
                options=[ft.DropdownOption(key=option) for option in field.options],
                hint_text=field.placeholder or "Выберите значение",
                on_select=lambda e: self._emit_change(),
                **common,
            )

        if field.type is FieldType.TEXTAREA:
            return ft.TextField(
                value=self._as_text(value),
                hint_text=field.placeholder,
                multiline=True,
                min_lines=3,
                max_lines=8,
                on_change=lambda e: self._emit_change(),
                **common,
            )

        if field.type is FieldType.DATE:
            return self._create_date_input(value, common)

        if field.type is FieldType.TIME:
            return self._create_time_input(value, common)

        keyboard = ft.KeyboardType.NUMBER if field.type is FieldType.NUMBER else None

        return ft.TextField(
            value=self._as_text(value),
            hint_text=field.placeholder,
            keyboard_type=keyboard,
            suffix=ft.Text(field.unit, size=FontSize.CAPTION, color=AppColors.TEXT_SECONDARY)
            if field.unit
            else None,
            on_change=lambda e: self._emit_change(),
            **common,
        )

    def _create_date_input(self, value: object | None, common: dict) -> ft.TextField:
        """Поле даты: нативный выбор даты либо ручной ввод без страницы."""

        parsed = _parse_date(self._as_text(value))
        picker_available = self._page is not None

        return ft.TextField(
            value=parsed.strftime(DATE_DISPLAY_FORMAT) if parsed else self._as_text(value),
            hint_text=DATE_DISPLAY_FORMAT if picker_available else "ДД.ММ.ГГГГ",
            read_only=picker_available,
            suffix_icon=ft.Icons.CALENDAR_MONTH,
            on_click=self._open_date_picker if picker_available else None,
            on_change=None if picker_available else (lambda e: self._emit_change()),
            **common,
        )

    def _create_time_input(self, value: object | None, common: dict) -> ft.TextField:
        """Поле времени: нативный выбор времени либо ручной ввод."""

        parsed = _parse_time(self._as_text(value))
        picker_available = self._page is not None

        return ft.TextField(
            value=parsed.strftime("%H:%M") if parsed else self._as_text(value),
            hint_text="ЧЧ:ММ",
            read_only=picker_available,
            suffix_icon=ft.Icons.SCHEDULE,
            on_click=self._open_time_picker if picker_available else None,
            on_change=None if picker_available else (lambda e: self._emit_change()),
            **common,
        )

    # ---------------------------------------------------------- нативные пикеры

    def _open_date_picker(self, e=None) -> None:
        if self._page is None:
            return

        current = _parse_date(self._as_text(self.input.value))

        picker = ft.DatePicker(
            value=datetime.combine(current, time.min) if current else datetime.now(),
            first_date=datetime(1950, 1, 1),
            last_date=datetime(2100, 12, 31),
            help_text=f"Дата: {self.field.title}",
            cancel_text="Отмена",
            confirm_text="Выбрать",
            on_change=self._date_selected,
        )

        self._page.show_dialog(picker)

    def _date_selected(self, event) -> None:
        selected = event.control.value

        if isinstance(selected, (datetime, date)):
            self.input.value = selected.strftime(DATE_DISPLAY_FORMAT)

        _safe_update(self.input)
        self._emit_change()

    def _open_time_picker(self, e=None) -> None:
        if self._page is None:
            return

        current = _parse_time(self._as_text(self.input.value))

        picker = ft.TimePicker(
            value=current or time(hour=datetime.now().hour, minute=0),
            help_text=f"Время: {self.field.title}",
            cancel_text="Отмена",
            confirm_text="Выбрать",
            on_change=self._time_selected,
        )

        self._page.show_dialog(picker)

    def _time_selected(self, event) -> None:
        selected = event.control.value

        if isinstance(selected, time):
            self.input.value = selected.strftime("%H:%M")

        _safe_update(self.input)
        self._emit_change()

    # ------------------------------------------------------------- значение

    @property
    def value(self) -> object | None:
        """Нормализованное значение поля.

        Даты и время хранятся в ISO-виде, чтобы их можно было сравнивать и
        сортировать независимо от формата отображения.
        """

        if isinstance(self.input, ft.Checkbox):
            return bool(self.input.value)

        raw = self._as_text(getattr(self.input, "value", "")).strip()

        if not raw:
            return None

        if self.field.type is FieldType.DATE:
            parsed = _parse_date(raw)
            return parsed.isoformat() if parsed else raw

        if self.field.type is FieldType.TIME:
            parsed = _parse_time(raw)
            return parsed.strftime("%H:%M") if parsed else raw

        return raw

    @property
    def is_empty(self) -> bool:
        # У флажка «пусто» — это снятая галочка, а не отсутствие значения.
        if self.field.type is FieldType.CHECKBOX:
            return not bool(self.input.value)

        return self.value is None

    def set_value(self, value: object | None) -> None:
        """Программно установить значение."""

        if isinstance(self.input, ft.Checkbox):
            self.input.value = bool(value)
        elif self.field.type is FieldType.DATE:
            parsed = _parse_date(self._as_text(value))
            self.input.value = (
                parsed.strftime(DATE_DISPLAY_FORMAT) if parsed else self._as_text(value)
            )
        elif self.field.type is FieldType.TIME:
            parsed = _parse_time(self._as_text(value))
            self.input.value = parsed.strftime("%H:%M") if parsed else self._as_text(value)
        elif self.field.type is FieldType.DROPDOWN:
            self.input.value = self._as_text(value) or None
        else:
            self.input.value = self._as_text(value)

        _safe_update(self.input)

    # ------------------------------------------------------------ валидация

    def validate(self) -> str | None:
        """Проверить значение. Возвращает текст ошибки или ``None``."""

        if self.field.required and self.is_empty:
            return "Обязательное поле"

        raw = self._as_text(getattr(self.input, "value", "")).strip()

        if not raw:
            return None

        if self.field.type is FieldType.NUMBER and not _is_number(raw):
            return "Введите число"

        if self.field.type is FieldType.DATE and _parse_date(raw) is None:
            return "Укажите дату в формате ДД.ММ.ГГГГ"

        if self.field.type is FieldType.TIME and _parse_time(raw) is None:
            return "Укажите время в формате ЧЧ:ММ"

        return None

    def show_error(self, message: str | None) -> None:
        """Показать или сбросить сообщение об ошибке."""

        if isinstance(self.input, ft.TextField):
            self.input.error = message
        elif isinstance(self.input, ft.Dropdown):
            self.input.error_text = message
        elif isinstance(self.input, ft.Checkbox):
            self.input.error = message

        _safe_update(self.input)

    # -------------------------------------------------------------- служебное

    def _emit_change(self) -> None:
        self.show_error(None)

        if self._on_change is not None:
            self._on_change(self)

    @staticmethod
    def _as_text(value: object | None) -> str:
        if value is None:
            return ""

        if isinstance(value, bool):
            return "Да" if value else ""

        return str(value)


def _is_number(raw: str) -> bool:
    try:
        float(raw.replace(",", ".").replace(" ", ""))
    except ValueError:
        return False

    return True


def _parse_date(raw: str) -> date | None:
    """Разобрать дату в поддерживаемых форматах."""

    text = raw.strip()

    if not text:
        return None

    for fmt in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


def _parse_time(raw: str) -> time | None:
    text = raw.strip()

    if not text:
        return None

    for fmt in TIME_INPUT_FORMATS:
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue

    return None


class FieldBuilder:
    """Фабрика полей формы (сохранена для обратной совместимости)."""

    @staticmethod
    def build(
        field: Field,
        value: object | None = None,
        on_change: Callable[[FieldControl], None] | None = None,
        page: ft.Page | None = None,
    ) -> FieldControl:
        return FieldControl(field=field, value=value, on_change=on_change, page=page)
