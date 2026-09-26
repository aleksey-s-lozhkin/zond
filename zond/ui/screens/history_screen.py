"""Экран истории проверок."""

from __future__ import annotations

import flet as ft

from zond.services.json_storage import StoredInspection
from zond.ui.colors import AppColors
from zond.ui.components.buttons import GhostButton, PrimaryButton
from zond.ui.components.cards import Badge, EmptyState, SectionCard
from zond.ui.components.dialogs import show_confirm, show_error
from zond.ui.components.headers import ScreenHeader
from zond.ui.design import ControlSize, FontSize, Radius, Space
from zond.ui.icons import AppIcons
from zond.ui.screens.base_screen import AppScreen


class HistoryScreen(AppScreen):
    """Список сохранённых проверок: черновики и завершённые."""

    def compose(self) -> ft.Control:
        entries = self.app.storage.list_stored()

        if not entries:
            body: ft.Control = ft.Container(
                expand=True,
                alignment=ft.Alignment(0, 0),
                content=EmptyState(
                    "Сохранённых проверок нет",
                    "Завершённые проверки и черновики появятся здесь.",
                    icon=AppIcons.HISTORY,
                ),
            )
        else:
            body = ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                spacing=Space.MD,
                controls=[self._entry_card(entry) for entry in entries],
            )

        return ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ScreenHeader(
                    "История проверок",
                    description=f"Всего записей: {len(entries)}",
                    on_back=self._go_back,
                ),
                body,
                ft.Container(
                    padding=ft.Padding(
                        left=Space.LG,
                        right=Space.LG,
                        top=Space.MD,
                        bottom=Space.LG,
                    ),
                    content=GhostButton(
                        "Обновить список",
                        icon=AppIcons.HISTORY,
                        on_click=self._refresh,
                    ),
                ),
            ],
        )

    # ------------------------------------------------------------- разметка

    def _entry_card(self, entry: StoredInspection) -> ft.Control:
        badge = (
            Badge("черновик", AppColors.WARNING, AppColors.WARNING_SOFT)
            if entry.is_draft
            else Badge("завершена", AppColors.SUCCESS, AppColors.SUCCESS_SOFT)
        )

        actions: list[ft.Control] = [
            PrimaryButton(
                "Продолжить" if entry.is_draft else "Открыть",
                icon=AppIcons.PLAY if entry.is_draft else AppIcons.OPEN,
                on_click=lambda event, item=entry: self._open(item),
                expand=True,
            )
        ]

        if not entry.is_draft:
            actions.append(
                GhostButton(
                    "PDF",
                    icon=AppIcons.PDF,
                    on_click=lambda event, item=entry: self._make_pdf(item),
                )
            )

        actions.append(
            GhostButton(
                "Удалить",
                icon=AppIcons.DELETE,
                on_click=lambda event, item=entry: self._delete(item),
            )
        )

        return SectionCard(
            ft.Row(
                spacing=Space.SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        entry.title,
                        size=FontSize.SUBTITLE,
                        weight=ft.FontWeight.W_600,
                        color=AppColors.TEXT,
                        expand=True,
                    ),
                    badge,
                ],
            ),
            ft.Text(
                entry.subtitle,
                size=FontSize.CAPTION,
                color=AppColors.TEXT_SECONDARY,
            ),
            ft.ProgressBar(
                value=entry.progress,
                bar_height=ControlSize.PROGRESS_BAR,
                color=AppColors.PRIMARY,
                bgcolor=AppColors.BORDER,
                border_radius=Radius.XL,
            ),
            ft.Text(
                f"Инспектор: {entry.inspector or '—'} · шаблон: {entry.template_name}",
                size=FontSize.CAPTION,
                color=AppColors.TEXT_SECONDARY,
            ),
            ft.Row(spacing=Space.SM, controls=actions),
        )

    # ------------------------------------------------------------- обработчики

    def _go_back(self, event) -> None:
        if not self.app.navigator.back():
            self.app.restart()

    def _refresh(self, event) -> None:
        self.refresh()

    def _open(self, entry: StoredInspection) -> None:
        self.app.resume_inspection(entry)

    def _make_pdf(self, entry: StoredInspection) -> None:
        if entry.is_draft:
            show_error(
                self.app.page,
                "Проверка не завершена",
                "Протокол формируется только по завершённой проверке. "
                "Продолжите заполнение и завершите её.",
            )
            return

        path = self.app.generate_pdf_for(entry.inspection)

        if path is not None:
            self.app.open_path(path)

    def _delete(self, entry: StoredInspection) -> None:
        show_confirm(
            self.app.page,
            "Удалить проверку?",
            f"Запись «{entry.title}» от {entry.subtitle} будет удалена безвозвратно.",
            on_confirm=lambda event: self.app.delete_stored(entry),
            confirm_text="Удалить",
            danger=True,
        )
