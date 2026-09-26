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
            author=inspection.inspector or "ЗОНД: ECTS",
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
        rows = [
            ("Объект", inspection.object_name or "—"),
            ("Инспектор", inspection.inspector or "—"),
            ("Начало проверки", format_datetime(inspection.started_at)),
            ("Завершение", format_datetime(inspection.finished_at)),
            ("Заполнено полей", f"{inspection.answered_count} из {inspection.total_items}"),
            ("Идентификатор", inspection.inspection_id),
        ]

        table = Table(
            [
                [
                    Paragraph(escape(name), styles["cellBold"]),
                    Paragraph(escape(str(value)), styles["cell"]),
                ]
                for name, value in rows
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
                value_style = "cellMuted" if item.is_empty else "cell"

                row = [
                    Paragraph(f"{escape(item.field.title)}{marker}", styles["cell"]),
                    Paragraph(escape(item.display_value()), styles[value_style]),
                ]

                if has_unit:
                    row.append(Paragraph(escape(item.field.unit or "—"), styles["cellMuted"]))

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

        story.append(Paragraph("* — обязательное для заполнения поле.", styles["cellMuted"]))
        story.append(Spacer(1, 12))

        return story

    @staticmethod
    def _signature(inspection: Inspection, styles: dict) -> list:
        line = "_" * 40
        inspector = escape(inspection.inspector) if inspection.inspector else "&nbsp;"

        return [
            Spacer(1, 8),
            Paragraph(
                f"Инспектор: {inspector}<br/><br/>{line}<br/>"
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
