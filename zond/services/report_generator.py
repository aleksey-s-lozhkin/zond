"""Формирование PDF-протокола проверки.

Кириллица в PDF требует TTF-шрифта с соответствующими глифами: встроенные
шрифты reportlab (Helvetica и т. п.) её не содержат. Поэтому генератор ищет
DejaVu Sans в каталоге ``assets/fonts``, затем в системных каталогах, и только
в крайнем случае откатывается на Helvetica (с предупреждением в логе).
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from zond.models.inspection import Inspection, format_datetime
from zond.models.verdict import NOT_CHECKED, NOT_RESOLVED, RESOLVED, Verdict, classify
from zond.services.errors import ReportError

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FONT_REGULAR = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"

#: Где искать TTF с кириллицей: сначала в проекте, затем в системе.
FONT_CANDIDATES: tuple[tuple[Path, Path], ...] = (
    (
        PROJECT_ROOT / "assets" / "fonts" / "DejaVuSans.ttf",
        PROJECT_ROOT / "assets" / "fonts" / "DejaVuSans-Bold.ttf",
    ),
    (
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ),
    (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ),
)

ACCENT = colors.HexColor("#2563EB")
MUTED = colors.HexColor("#6B7280")
BORDER = colors.HexColor("#D1D5DB")
ALERT = colors.HexColor("#DC2626")

#: Цвета оценки: соответствие и несоответствие.
OK_COLOR = colors.HexColor("#15803D")
PROBLEM_COLOR = colors.HexColor("#DC2626")


class ReportGenerator:
    """Строит PDF-протокол по завершённой проверке."""

    def __init__(self) -> None:
        self.regular_font, self.bold_font = _resolve_fonts()

    def generate(self, inspection: Inspection, path: str | Path) -> Path:
        """Сформировать PDF и вернуть путь к нему."""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        styles = self._styles()

        document = SimpleDocTemplate(
            str(target),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=f"Протокол проверки — {inspection.title}",
            author=inspection.executor or "ЗОНД: ECTS",
            subject=inspection.template.name,
            creator="ЗОНД: ECTS",
        )

        story: list = []
        story.extend(self._header(inspection, styles))
        story.extend(self._summary(inspection, styles))
        story.extend(self._groups(inspection, styles))
        story.extend(self._signature(inspection, styles))

        try:
            document.build(
                story,
                onFirstPage=self._draw_footer,
                onLaterPages=self._draw_footer,
            )
        except ReportError:
            raise
        except Exception as error:  # pragma: no cover - сбои reportlab/ФС
            raise ReportError(f"Не удалось сформировать PDF: {error}") from error

        logger.info("Протокол проверки %s сохранён в %s", inspection.inspection_id, target)
        return target

    # ------------------------------------------------------------- стили

    def _styles(self) -> dict[str, ParagraphStyle]:
        return {
            "title": ParagraphStyle(
                "title",
                fontName=self.bold_font,
                fontSize=17,
                leading=21,
                textColor=colors.HexColor("#111827"),
                spaceAfter=2,
            ),
            "subtitle": ParagraphStyle(
                "subtitle",
                fontName=self.regular_font,
                fontSize=9.5,
                leading=13,
                textColor=MUTED,
            ),
            "group": ParagraphStyle(
                "group",
                fontName=self.bold_font,
                fontSize=12,
                leading=16,
                textColor=ACCENT,
                spaceBefore=4,
                spaceAfter=4,
            ),
            "cell": ParagraphStyle(
                "cell",
                fontName=self.regular_font,
                fontSize=9,
                leading=12,
                alignment=TA_LEFT,
            ),
            "cellBold": ParagraphStyle(
                "cellBold",
                fontName=self.bold_font,
                fontSize=9,
                leading=12,
                alignment=TA_LEFT,
            ),
            "cellMuted": ParagraphStyle(
                "cellMuted",
                fontName=self.regular_font,
                fontSize=8.5,
                leading=11,
                textColor=MUTED,
            ),
            "note": ParagraphStyle(
                "note",
                fontName=self.regular_font,
                fontSize=9,
                leading=13,
                textColor=ALERT,
            ),
            "body": ParagraphStyle(
                "body",
                fontName=self.regular_font,
                fontSize=9.5,
                leading=13,
            ),
            "cellOk": ParagraphStyle(
                "cellOk",
                fontName=self.regular_font,
                fontSize=9,
                leading=12,
                textColor=OK_COLOR,
            ),
            "cellProblem": ParagraphStyle(
                "cellProblem",
                fontName=self.bold_font,
                fontSize=9,
                leading=12,
                textColor=PROBLEM_COLOR,
            ),
            "valueOk": ParagraphStyle(
                "valueOk",
                fontName=self.bold_font,
                fontSize=9.5,
                leading=13,
                textColor=OK_COLOR,
            ),
            "valueProblem": ParagraphStyle(
                "valueProblem",
                fontName=self.bold_font,
                fontSize=9.5,
                leading=13,
                textColor=PROBLEM_COLOR,
            ),
        }

    # ------------------------------------------------------------- блоки

    @staticmethod
    def _header(inspection: Inspection, styles: dict) -> list:
        return [
            Paragraph("ПРОТОКОЛ ПРОВЕРКИ ОБОРУДОВАНИЯ", styles["title"]),
            Paragraph(
                f"Система «ЗОНД: ECTS» · шаблон «{escape(inspection.template.name)}»",
                styles["subtitle"],
            ),
            Spacer(1, 10),
        ]

    @staticmethod
    def _summary(inspection: Inspection, styles: dict) -> list:
        problems = inspection.problems
        conformities = inspection.conformities

        # (подпись, значение, стиль значения)
        rows = [
            ("Объект", inspection.object_name or "—", "cell"),
            ("Исполнитель", inspection.executor or "—", "cell"),
            ("Начало проверки", format_datetime(inspection.started_at), "cell"),
            ("Завершение", format_datetime(inspection.finished_at), "cell"),
            ("Заполнено полей", f"{inspection.answered_count} из {inspection.total_items}", "cell"),
            (
                "Соответствий",
                str(len(conformities)),
                "valueOk" if conformities else "cell",
            ),
            (
                "Несоответствий",
                str(len(problems)),
                "valueProblem" if problems else "cell",
            ),
            ("Идентификатор", inspection.inspection_id, "cell"),
        ]

        if inspection.is_repeat:
            defects = inspection.previous_defects
            resolved = len(inspection.resolved_defects)

            rows.insert(
                -1,
                (
                    "Замечания прошлой проверки",
                    f"устранено {resolved} из {len(defects)}" if defects else "не выявлялись",
                    "valueOk" if defects and resolved == len(defects) else "cell",
                ),
            )

        table = Table(
            [
                [
                    Paragraph(escape(name), styles["cellBold"]),
                    Paragraph(escape(str(value)), styles[style]),
                ]
                for name, value, style in rows
            ],
            colWidths=[45 * mm, None],
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.25, BORDER),
                ]
            )
        )

        story: list = [table, Spacer(1, 10)]

        story.extend(ReportGenerator._problem_block(inspection, styles))
        story.extend(ReportGenerator._repeat_block(inspection, styles))

        missing = inspection.missing_required

        if missing:
            names = ", ".join(escape(item.field.title) for item in missing[:8])
            suffix = f" и ещё {len(missing) - 8}" if len(missing) > 8 else ""
            story.append(
                Paragraph(
                    f"Не заполнены обязательные поля ({len(missing)}): {names}{suffix}.",
                    styles["note"],
                )
            )
            story.append(Spacer(1, 8))

        return story

    @staticmethod
    def _repeat_block(inspection: Inspection, styles: dict) -> list:
        """Замечания прошлой проверки и их состояние.

        На повторном выезде важнее не сам список, а динамика: что закрыто, а
        что осталось. Поэтому состояние вынесено отдельной колонкой и
        подсвечено.
        """

        if not inspection.is_repeat:
            return []

        defects = inspection.previous_defects

        if not defects:
            return []

        rows = [
            [
                Paragraph("Шаг проверки", styles["cellBold"]),
                Paragraph("Поле", styles["cellBold"]),
                Paragraph("В прошлый раз", styles["cellBold"]),
                Paragraph("Сейчас", styles["cellBold"]),
            ]
        ]

        for item in defects:
            state, state_style = _resolution_style(item.resolution)

            rows.append(
                [
                    Paragraph(escape(item.field.group), styles["cell"]),
                    Paragraph(escape(item.field.title), styles["cell"]),
                    Paragraph(escape(item.display_previous()), styles["cellProblem"]),
                    Paragraph(escape(state), styles[state_style]),
                ]
            )

        table = Table(
            rows,
            colWidths=[36 * mm, None, 34 * mm, 30 * mm],
            hAlign="LEFT",
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF4FF")),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, ACCENT),
                    ("INNERGRID", (0, 1), (-1, -1), 0.2, BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        resolved = len(inspection.resolved_defects)

        return [
            Paragraph(
                f"Замечания прошлой проверки: {len(defects)}, устранено {resolved}",
                styles["group"],
            ),
            table,
            Spacer(1, 12),
        ]

    @staticmethod
    def _problem_block(inspection: Inspection, styles: dict) -> list:
        """Перечень выявленных несоответствий отдельным блоком.

        В таблицах по группам несоответствия выделены цветом, но их нужно
        ещё и найти среди сотни строк, поэтому они собраны в начале отчёта.
        """

        problems = inspection.problems

        if not problems:
            return [
                Paragraph(
                    "Несоответствий требованиям не выявлено.",
                    styles["valueOk"],
                ),
                Spacer(1, 10),
            ]

        rows = [
            [
                Paragraph("Шаг проверки", styles["cellBold"]),
                Paragraph("Поле", styles["cellBold"]),
                Paragraph("Ответ", styles["cellBold"]),
            ]
        ]

        for item in problems:
            rows.append(
                [
                    Paragraph(escape(item.field.group), styles["cell"]),
                    Paragraph(escape(item.field.title), styles["cell"]),
                    Paragraph(escape(item.display_value()), styles["cellProblem"]),
                ]
            )

        table = Table(
            rows,
            colWidths=[42 * mm, None, 40 * mm],
            hAlign="LEFT",
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FEF2F2")),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, PROBLEM_COLOR),
                    ("INNERGRID", (0, 1), (-1, -1), 0.2, BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        return [
            Paragraph(f"Выявленные несоответствия: {len(problems)}", styles["group"]),
            table,
            Spacer(1, 12),
        ]

    @staticmethod
    def _groups(inspection: Inspection, styles: dict) -> list:
        story: list = []

        has_unit = any(item.field.unit for item in inspection.items)
        has_comment = any(item.comment for item in inspection.items)

        for group in inspection.template.groups:
            items = inspection.items_in_group(group)

            if not items:
                continue

            header = ["Поле", "Значение"]

            if has_unit:
                header.append("Ед.")

            if has_comment:
                header.append("Примечание")

            rows = [[Paragraph(escape(name), styles["cellBold"]) for name in header]]

            for item in items:
                marker = " *" if item.field.required else ""
                value_style = _value_style(item)

                row = [
                    Paragraph(f"{escape(item.field.title)}{marker}", styles["cell"]),
                    Paragraph(escape(item.display_value()), styles[value_style]),
                ]

                if has_unit:
                    # Пустая ячейка читается лучше, чем прочерк в колонке единиц.
                    row.append(Paragraph(escape(item.field.unit), styles["cellMuted"]))

                if has_comment:
                    row.append(Paragraph(escape(item.comment or "—"), styles["cellMuted"]))

                rows.append(row)

            table = Table(
                rows,
                colWidths=_column_widths(has_unit, has_comment),
                hAlign="LEFT",
                repeatRows=1,
            )
            table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF4FF")),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, ACCENT),
                        ("INNERGRID", (0, 1), (-1, -1), 0.2, BORDER),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )

            story.append(KeepTogether([Paragraph(escape(group), styles["group"]), table]))
            story.append(Spacer(1, 8))

        story.append(
            Paragraph(
                "* — обязательное для заполнения поле. "
                "Зелёным выделены ответы «соответствует», "
                "красным — выявленные несоответствия.",
                styles["cellMuted"],
            )
        )
        story.append(Spacer(1, 12))

        return story

    @staticmethod
    def _signature(inspection: Inspection, styles: dict) -> list:
        line = "_" * 40
        executor = escape(inspection.executor) if inspection.executor else "&nbsp;"

        return [
            Spacer(1, 8),
            Paragraph(
                f"Проверку выполнил: {executor}<br/><br/>{line}<br/>"
                '<font size="8" color="#6B7280">подпись / расшифровка</font>',
                styles["body"],
            ),
        ]

    def _draw_footer(self, canvas, document) -> None:
        canvas.saveState()
        canvas.setFont(self.regular_font, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, "ЗОНД: ECTS")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"стр. {document.page}")
        canvas.drawCentredString(
            A4[0] / 2,
            10 * mm,
            datetime.now().strftime("сформирован %d.%m.%Y %H:%M"),
        )
        canvas.restoreState()


def _value_style(item) -> str:
    """Стиль ячейки значения: цвет зависит от оценки ответа."""

    if item.is_empty:
        return "cellMuted"

    verdict = classify(item.value)

    if verdict is Verdict.OK:
        return "cellOk"

    if verdict is Verdict.PROBLEM:
        return "cellProblem"

    return "cell"


def _column_widths(has_unit: bool, has_comment: bool) -> list[float]:
    """Ширины колонок таблицы группы под доступную ширину A4."""

    available = A4[0] - 36 * mm
    value_width = 55 * mm
    unit_width = 16 * mm if has_unit else 0.0
    comment_width = 35 * mm if has_comment else 0.0
    field_width = available - value_width - unit_width - comment_width

    widths = [field_width, value_width]

    if has_unit:
        widths.append(unit_width)

    if has_comment:
        widths.append(comment_width)

    return widths


def _resolve_fonts() -> tuple[str, str]:
    """Зарегистрировать TTF с кириллицей и вернуть имена шрифтов."""

    for regular, bold in FONT_CANDIDATES:
        if not regular.exists():
            continue

        bold_path = bold if bold.exists() else regular

        try:
            registered = pdfmetrics.getRegisteredFontNames()

            if FONT_REGULAR not in registered:
                pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular)))

            if FONT_BOLD not in registered:
                pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_path)))

            return FONT_REGULAR, FONT_BOLD
        except Exception:  # pragma: no cover - повреждённый шрифт
            logger.exception("Не удалось зарегистрировать шрифт %s", regular)

    logger.warning(
        "TTF с кириллицей не найден — PDF будет сформирован шрифтом Helvetica, "
        "кириллические символы могут отображаться некорректно."
    )
    return "Helvetica", "Helvetica-Bold"


def _resolution_style(resolution: str) -> tuple[str, str]:
    """Подпись и стиль состояния замечания для протокола."""

    if resolution == RESOLVED:
        return resolution, "valueOk"

    if resolution == NOT_RESOLVED:
        return resolution, "valueProblem"

    return NOT_CHECKED, "cell"
