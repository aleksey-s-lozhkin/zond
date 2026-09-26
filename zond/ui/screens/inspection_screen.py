"""Экран пошагового заполнения проверки."""

from __future__ import annotations

import flet as ft

from zond.ui.colors import AppColors
from zond.ui.components.buttons import PrimaryButton, SecondaryButton
from zond.ui.components.cards import EmptyState
from zond.ui.components.dialogs import show_error
from zond.ui.components.headers import ScreenHeader
from zond.ui.components.progress import ProgressWidget
from zond.ui.design import FontSize, Space
from zond.ui.icons import AppIcons
from zond.ui.screens.base_screen import AppScreen
from zond.ui.widgets.field_builder import FieldControl


class InspectionScreen(AppScreen):
    """Форма текущей группы полей с переходом между шагами."""

    field_controls: list[FieldControl]

    def compose(self) -> ft.Control:
        state = self.app.state
        inspection = state.inspection

        if inspection is None or not state.current_fields:
            return EmptyState(
                "Нет данных для заполнения",
                "Загрузите шаблон проверки заново.",
                icon=AppIcons.WARNING,
            )

        self.field_controls = []

        for field in state.current_fields:
            item = inspection.get_item(field.name)

            self.field_controls.append(
                FieldControl(
                    field=field,
                    value=item.value if item is not None else None,
                    on_change=self._field_changed,
                    page=self.app.page,
                )
            )

        self.progress = ProgressWidget(
            title="Заполнено полей",
            current=state.answered_fields,
            total=state.total_fields,
        )

        group_required = [field for field in state.current_fields if field.required]

        hints: list[ft.Control] = []

        if group_required:
            hints.append(
                ft.Row(
                    spacing=Space.XS,
                    controls=[
                        ft.Text("*", size=FontSize.CAPTION, color=AppColors.ERROR),
                        ft.Text(
                            f"обязательных полей на шаге: {len(group_required)}",
                            size=FontSize.CAPTION,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                )
            )

        is_last = state.is_last_group

        return ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ScreenHeader(
                    state.current_group or "Проверка",
                    description=(
                        f"Шаг {state.current_group_index + 1} из {state.total_groups}"
                        f" · {inspection.template.name}"
                    ),
                    on_back=self._go_back,
                ),
                self.progress,
                ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=Space.LG,
                    controls=[*self.field_controls, *hints],
                ),
                ft.Container(
                    padding=ft.Padding(
                        left=Space.LG,
                        right=Space.LG,
                        top=Space.MD,
                        bottom=Space.LG,
                    ),
                    content=ft.Row(
                        spacing=Space.MD,
                        controls=[
                            SecondaryButton(
                                "Назад",
                                icon=AppIcons.BACK,
                                on_click=self._go_back,
                                expand=True,
                            ),
                            PrimaryButton(
                                "Завершить" if is_last else "Далее",
                                icon=AppIcons.SUCCESS if is_last else AppIcons.NEXT,
                                on_click=self._go_next,
                                expand=True,
                            ),
                        ],
                    ),
                ),
            ],
        )

    # ------------------------------------------------------------- обработчики

    def _field_changed(self, control: FieldControl) -> None:
        """Сохранить значение поля в проверку и обновить прогресс."""

        inspection = self.app.state.inspection

        if inspection is None:
            return

        item = inspection.get_item(control.field.name)

        if item is None:
            return

        item.value = control.value
        item.is_checked = not item.is_empty

        self.app.state.mark_modified()
        self.progress.set_progress(
            self.app.state.answered_fields,
            self.app.state.total_fields,
        )

    def _persist_group(self) -> None:
        """Перенести значения всех полей шага в модель."""

        for control in self.field_controls:
            self._field_changed(control)

    def _validate_group(self) -> list[str]:
        """Проверить поля шага. Подсвечивает проблемные поля."""

        problems: list[str] = []

        for control in self.field_controls:
            message = control.validate()
            control.show_error(message)

            if message:
                problems.append(f"{control.field.title}: {message}")

        return problems

    def _go_next(self, event) -> None:
        self._persist_group()

        problems = self._validate_group()

        if problems:
            show_error(
                self.app.page,
                "Проверьте заполнение",
                "Перейти дальше нельзя, пока не исправлено:\n\n"
                + "\n".join(f"• {problem}" for problem in problems),
            )
            return

        if self.app.state.is_last_group:
            self._finish()
            return

        self.app.save_draft()
        self.app.state.next_group()
        self.refresh()

    def _go_back(self, event) -> None:
        self._persist_group()

        if self.app.state.previous_group():
            self.app.save_draft()
            self.refresh()
            return

        # Первая группа — выходим к сведениям о шаблоне.
        self.app.save_draft()
        self.app.navigator.back()

    def _finish(self) -> None:
        inspection = self.app.state.inspection

        if inspection is None:
            return

        missing = inspection.missing_required

        if missing:
            listed = "\n".join(
                f"• {item.field.title} ({item.field.group})" for item in missing[:15]
            )
            extra = f"\n…и ещё {len(missing) - 15}." if len(missing) > 15 else ""

            show_error(
                self.app.page,
                "Не все обязательные поля заполнены",
                f"Незаполненных обязательных полей: {len(missing)}.\n\n{listed}{extra}",
            )

            self.app.state.goto_first_incomplete_group()
            self.refresh()
            return

        self.app.finish_inspection()
