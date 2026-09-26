"""Экран завершения проверки."""

from __future__ import annotations

import flet as ft

from zond.models.inspection import format_datetime
from zond.ui.colors import AppColors
from zond.ui.components.buttons import GhostButton, PrimaryButton, SecondaryButton
from zond.ui.components.cards import EmptyState, InfoRow, SectionCard
from zond.ui.components.layout import ScreenBody
from zond.ui.design import FontSize, Space
from zond.ui.icons import AppIcons
from zond.ui.screens.base_screen import AppScreen


class FinishScreen(AppScreen):
    """Итоги проверки, сохранение и формирование протокола."""

    def compose(self) -> ft.Control:
        inspection = self.app.state.inspection

        if inspection is None or not inspection.is_finished:
            return EmptyState(
                "Проверка не завершена",
                "Вернитесь к заполнению формы.",
                icon=AppIcons.WARNING,
            )

        json_path = self.app.storage.inspections_dir / self.app.storage.file_name(inspection)
        pdf_path = self.app.storage.pdf_path(inspection)
        pdf_exists = pdf_path.exists()

        cards: list[ft.Control] = [
            SectionCard(
                InfoRow("Объект", inspection.object_name or "—"),
                InfoRow("Исполнитель", inspection.executor or "—"),
                InfoRow("Шаблон", inspection.template.name),
                InfoRow("Начало", format_datetime(inspection.started_at)),
                InfoRow("Завершение", format_datetime(inspection.finished_at)),
                InfoRow("Длительность", _format_duration(inspection)),
                InfoRow(
                    "Заполнено",
                    f"{inspection.answered_count} из {inspection.total_items}",
                    emphasize=True,
                ),
                InfoRow(
                    "Соответствий",
                    str(len(inspection.conformities)),
                    value_color=AppColors.SUCCESS,
                ),
                InfoRow(
                    "Несоответствий",
                    str(len(inspection.problems)),
                    value_color=AppColors.ERROR if inspection.problems else AppColors.SUCCESS,
                    emphasize=bool(inspection.problems),
                ),
                title="Итоги проверки",
                icon=AppIcons.SUCCESS,
            )
        ]

        missing = inspection.missing_required

        if missing:
            cards.append(
                SectionCard(
                    *[
                        ft.Text(
                            f"• {item.field.title} ({item.field.group})",
                            size=FontSize.CAPTION,
                            color=AppColors.ERROR,
                        )
                        for item in missing[:10]
                    ],
                    title=f"Не заполнено обязательных полей: {len(missing)}",
                    icon=AppIcons.WARNING,
                )
            )

        cards.append(
            SectionCard(
                InfoRow(
                    "Данные проверки",
                    self.app.location_label(json_path),
                    tooltip=str(json_path),
                    max_lines=2,
                ),
                InfoRow(
                    "Протокол PDF",
                    (self.app.location_label(pdf_path) if pdf_exists else "ещё не сформирован"),
                    value_color=AppColors.TEXT if pdf_exists else AppColors.TEXT_SECONDARY,
                    tooltip=str(pdf_path) if pdf_exists else None,
                    max_lines=2,
                ),
                title="Сохранённые файлы",
                subtitle="Данные сохранены автоматически.",
                icon=AppIcons.SAVE,
            )
        )

        buttons: list[ft.Control] = [
            PrimaryButton(
                "Сформировать PDF" if not pdf_exists else "Обновить PDF",
                icon=AppIcons.PDF,
                on_click=self._make_pdf,
                expand=True,
            )
        ]

        if pdf_exists:
            buttons.append(
                SecondaryButton(
                    "Открыть PDF",
                    icon=AppIcons.OPEN,
                    on_click=self._open_pdf,
                    expand=True,
                )
            )

        success_block = ft.Row(
            spacing=Space.MD,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(
                    AppIcons.SUCCESS,
                    size=44,
                    color=AppColors.SUCCESS,
                ),
                ft.Column(
                    spacing=2,
                    expand=True,
                    tight=True,
                    controls=[
                        ft.Text(
                            "Проверка завершена",
                            size=FontSize.TITLE,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT,
                        ),
                        ft.Text(
                            inspection.title,
                            size=FontSize.BODY,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
            ],
        )

        return ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ScreenBody(success_block, *cards, top=Space.LG),
                ft.Container(
                    padding=ft.Padding(
                        left=Space.LG,
                        right=Space.LG,
                        top=Space.MD,
                        bottom=Space.LG,
                    ),
                    content=ft.Column(
                        spacing=Space.SM,
                        tight=True,
                        controls=[
                            ft.Row(spacing=Space.MD, controls=buttons),
                            ft.Row(
                                spacing=Space.MD,
                                controls=[
                                    SecondaryButton(
                                        "История проверок",
                                        icon=AppIcons.HISTORY,
                                        on_click=self._open_history,
                                        expand=True,
                                    ),
                                    GhostButton(
                                        "Новая проверка",
                                        icon=AppIcons.ADD,
                                        on_click=self._restart,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        )

    # ------------------------------------------------------------- обработчики

    def _make_pdf(self, event) -> None:
        path = self.app.generate_pdf()

        if path is not None:
            self.refresh()

    async def _open_pdf(self, event) -> None:
        inspection = self.app.state.inspection

        if inspection is None:
            return

        await self.app.open_path(self.app.storage.pdf_path(inspection))

    def _open_history(self, event) -> None:
        self.app.open_history()

    def _restart(self, event) -> None:
        self.app.restart()


def _format_duration(inspection) -> str:
    """Человекочитаемая длительность проверки."""

    if inspection.finished_at is None:
        return "—"

    seconds = int((inspection.finished_at - inspection.started_at).total_seconds())

    if seconds < 0:
        return "—"

    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours} ч {minutes} мин"

    if minutes:
        return f"{minutes} мин {secs} с"

    return f"{secs} с"
