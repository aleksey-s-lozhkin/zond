"""Экран подтверждения загруженного шаблона."""

from __future__ import annotations

import flet as ft

from zond.models.inspection import format_datetime
from zond.ui.colors import AppColors
from zond.ui.components.buttons import PrimaryButton, SecondaryButton
from zond.ui.components.cards import EmptyState, InfoRow, SectionCard
from zond.ui.components.headers import ScreenHeader
from zond.ui.components.layout import ActionBar, ScreenBody
from zond.ui.design import FontSize, Space
from zond.ui.icons import AppIcons
from zond.ui.screens.base_screen import AppScreen

#: Значение радиокнопки «начать с пустой формы».
REPEAT_NONE = ""

#: Сколько символов названия объекта показывать в списке прошлых проверок.
OBJECT_PREVIEW = 24


def _candidate_label(inspection) -> str:
    """Строка прошлой проверки для списка выбора."""

    moment = inspection.finished_at or inspection.started_at
    label = f"{format_datetime(moment)} · несоответствий: {len(inspection.problems)}"

    name = inspection.object_name.strip()

    if name:
        if len(name) > OBJECT_PREVIEW:
            name = name[:OBJECT_PREVIEW] + "…"

        label += f" · {name}"

    return label


class CheckScreen(AppScreen):
    """Показывает состав шаблона и собирает сведения о проверке."""

    def compose(self) -> ft.Control:
        template = self.app.state.template

        #: Проверки, выбранные для переноса значений: значение радиокнопки —
        #: идентификатор проверки.
        self.repeat_choices: dict[str, object] = {}
        self.repeat_group: ft.RadioGroup | None = None

        if template is None:
            return EmptyState(
                "Шаблон не загружен",
                "Вернитесь на стартовый экран и выберите CSV-файл.",
                icon=AppIcons.WARNING,
            )

        inspection = self.app.state.inspection

        self.object_input = ft.TextField(
            label="Объект (в протоколе)",
            hint_text="Наименование объекта или узла проверки",
            value=inspection.object_name if inspection else "",
            border_radius=12,
            filled=True,
            fill_color=AppColors.SURFACE,
            dense=True,
        )

        self.executor_input = ft.TextField(
            label="Исполнитель (в протоколе)",
            hint_text="ФИО и должность: приборист, слесарь КИПиА, инженер",
            value=inspection.executor if inspection else "",
            border_radius=12,
            filled=True,
            fill_color=AppColors.SURFACE,
            dense=True,
        )

        cards: list[ft.Control] = [
            SectionCard(
                InfoRow("Название", template.name),
                InfoRow("Полей", str(len(template.fields))),
                InfoRow("Групп", str(template.total_groups)),
                InfoRow(
                    "Обязательных",
                    str(len(template.required_fields)),
                    value_color=AppColors.PRIMARY if template.required_fields else AppColors.TEXT,
                ),
                title="Шаблон проверки",
                icon=AppIcons.LIST,
            )
        ]

        if template.warnings:
            cards.append(
                SectionCard(
                    *[
                        ft.Row(
                            spacing=Space.SM,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Icon(AppIcons.WARNING, size=18, color=AppColors.WARNING),
                                ft.Text(
                                    warning,
                                    size=FontSize.CAPTION,
                                    color=AppColors.TEXT,
                                    expand=True,
                                ),
                            ],
                        )
                        for warning in template.warnings
                    ],
                    title="Предупреждения при разборе",
                    subtitle="Шаблон загружен, но проверьте перечисленные места.",
                    icon=AppIcons.WARNING,
                )
            )

        cards.append(
            SectionCard(
                self.object_input,
                self.executor_input,
                title="Сведения о проверке",
                subtitle="Необязательно: попадут в протокол и название проверки.",
                icon=AppIcons.APP,
            )
        )

        repeat_card = self._repeat_card()

        if repeat_card is not None:
            cards.append(repeat_card)

        cards.append(
            SectionCard(
                *[
                    InfoRow(group, f"{len(template.fields_in_group(group))} пол.")
                    for group in template.groups
                ],
                title="Группы полей",
                icon=AppIcons.LIST,
            )
        )

        return ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ScreenHeader(
                    "Шаблон загружен",
                    description=template.name,
                    on_back=self._go_back,
                    actions=[self._share_button()],
                ),
                ScreenBody(*cards, top=Space.XS),
                ActionBar(
                    SecondaryButton(
                        "Назад",
                        icon=AppIcons.BACK,
                        on_click=self._go_back,
                        expand=True,
                    ),
                    self._start_button(),
                ),
            ],
        )

    def _share_button(self) -> ft.Control:
        """Отправка шаблона: второстепенное действие, поэтому в шапке.

        В нижней панели три кнопки не помещаются на телефонной ширине, и
        подписи переносятся посередине слов.
        """

        return ft.IconButton(
            icon=AppIcons.SHARE,
            icon_color=AppColors.TEXT,
            tooltip="Отправить шаблон",
            on_click=self._share,
        )

    def _start_button(self) -> PrimaryButton:
        self.start_button = PrimaryButton(
            "Начать проверку",
            icon=AppIcons.PLAY,
            on_click=self._start,
            expand=True,
        )

        return self.start_button

    # -------------------------------------------------------- повторная проверка

    def _repeat_card(self) -> ft.Control | None:
        """Выбор проверки, с которой перенести значения.

        Список выбирается вручную: объектов немного, а автоматический подбор
        по одному названию шаблона легко подставил бы ответы с чужого объекта.
        """

        candidates = self.app.repeat_candidates()

        if not candidates:
            return None

        options: list[ft.Control] = [self._repeat_row(REPEAT_NONE, "Начать с пустой формы")]

        for inspection in candidates:
            key = inspection.inspection_id
            self.repeat_choices[key] = inspection
            options.append(self._repeat_row(key, _candidate_label(inspection)))

        self.repeat_group = ft.RadioGroup(
            value=REPEAT_NONE,
            on_change=self._choose_repeat,
            content=ft.Column(controls=options, spacing=Space.XS, tight=True),
        )

        subtitle = (
            "Значения прошлой проверки подставятся в форму — править нужно "
            "только изменившееся. Прежние замечания разбираются отдельным шагом."
        )

        return SectionCard(
            self.repeat_group,
            title=f"Повторная проверка ({len(candidates)})",
            subtitle=subtitle,
            icon=AppIcons.HISTORY,
        )

    def _repeat_row(self, value: str, label: str) -> ft.Control:
        """Строка выбора прошлой проверки.

        Подпись радиокнопки не переносится и обрезается по краю экрана,
        поэтому текст вынесен отдельным контролом, а нажатие ловит вся
        строка целиком.
        """

        return ft.Container(
            padding=ft.Padding(left=0, top=Space.XS, right=Space.SM, bottom=Space.XS),
            border_radius=8,
            on_click=lambda event, key=value: self._select_repeat(key),
            content=ft.Row(
                spacing=Space.XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Radio(value=value, label=""),
                    ft.Text(label, size=FontSize.BODY, color=AppColors.TEXT, expand=True),
                ],
            ),
        )

    def repeat_options(self) -> list[tuple[str, str]]:
        """Варианты выбора прошлой проверки: значение и подпись."""

        if self.repeat_group is None:
            return []

        return [
            (row.content.controls[0].value, row.content.controls[1].value)
            for row in self.repeat_group.content.controls
        ]

    def _select_repeat(self, value: str) -> None:
        if self.repeat_group is None:
            return

        self.repeat_group.value = value
        self._choose_repeat(None)

    # ------------------------------------------------------------- обработчики

    def _choose_repeat(self, event) -> None:
        selected = self.repeat_group.value if self.repeat_group else REPEAT_NONE

        if self.start_button is not None:
            self.start_button.content = ft.Text(
                "Начать проверку" if selected == REPEAT_NONE else "Начать с прошлой",
                size=FontSize.SUBTITLE,
                weight=ft.FontWeight.W_600,
            )

        self.safe_update()

    async def _share(self, event) -> None:
        await self.app.share_template()

    def _go_back(self, event) -> None:
        self.app.navigator.back()

    def _start(self, event) -> None:
        selected = self.repeat_group.value if self.repeat_group else REPEAT_NONE

        self.app.start_inspection(
            object_name=(self.object_input.value or "").strip(),
            executor=(self.executor_input.value or "").strip(),
            previous=self.repeat_choices.get(selected or ""),
        )
