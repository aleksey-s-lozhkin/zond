"""Разбор CSV-шаблонов проверок.

Парсер рассчитан на «грязные» файлы, которые готовят люди в Excel/LibreOffice:
BOM, разные кодировки, `;`/`,`/табуляция как разделитель, пустые строки и
незаполненные необязательные колонки.

Принцип разделения ошибок:

* **ошибка** — данные потерять нельзя (пустое имя поля, дубликат имени,
  список без вариантов, нет обязательных колонок) → разбор прерывается со
  списком всех найденных проблем;
* **предупреждение** — данные можно восстановить (неизвестный тип, пустой
  ``order``) → шаблон загружается, предупреждения показываются пользователю.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

from zond.models.field import Field, FieldType
from zond.services.errors import ParseProblem, TemplateParseError

try:  # pragma: no cover - зависит от окружения
    from charset_normalizer import from_bytes as _detect_from_bytes
except ImportError:  # pragma: no cover
    _detect_from_bytes = None

logger = logging.getLogger(__name__)

#: Колонки, без которых шаблон не имеет смысла.
REQUIRED_COLUMNS = ("name", "label", "type")

#: Все колонки, которые понимает парсер.
KNOWN_COLUMNS = (
    "order",
    "name",
    "label",
    "type",
    "group",
    "required",
    "options",
    "placeholder",
    "description",
    "unit",
)

#: Значения колонки ``required``, считающиеся истиной.
TRUE_VALUES = frozenset({"true", "1", "yes", "y", "да", "истина", "+", "x", "v"})

#: Кодировки для резервного перебора, если автоопределение не сработало.
FALLBACK_ENCODINGS = ("utf-8-sig", "utf-8", "cp1251")

#: Возможные разделители в порядке приоритета.
DELIMITERS = (",", ";", "\t", "|")

#: Значение группы по умолчанию.
DEFAULT_GROUP = "Общие сведения"

#: Разделители вариантов внутри колонки ``options``.
OPTION_SEPARATORS = ("\t", ";", "|", ",")


@dataclass(slots=True)
class ParseResult:
    """Результат разбора шаблона."""

    fields: list[Field]
    warnings: list[str] = field(default_factory=list)


class CSVParser:
    """Парсер CSV с поддержкой группировки полей."""

    # ------------------------------------------------------------ публичное

    def parse_template(self, file_path: str | Path) -> ParseResult:
        """Разобрать CSV-шаблон.

        Raises:
            TemplateParseError: файл нечитаем, структурно некорректен или
                содержит строки, которые нельзя восстановить.
        """

        path = Path(file_path)

        if not path.exists():
            raise TemplateParseError(f"Файл не найден: {path}")

        if not path.is_file():
            raise TemplateParseError(f"Это не файл: {path}")

        text, encoding = self._read_text(path)
        logger.debug("Шаблон %s прочитан в кодировке %s", path.name, encoding)

        header, rows = self._split_rows(text)

        if not header:
            raise TemplateParseError("Файл пуст: не найдена строка заголовков")

        self._check_required_columns(header)

        warnings: list[str] = []
        problems: list[ParseProblem] = []

        self._warn_unknown_columns(header, warnings)

        fields: list[Field] = []
        seen_names: dict[str, int] = {}

        for row in rows:
            line_number = row["line"]
            cells = row["cells"]

            if not any(str(cell).strip() for cell in cells):
                continue  # пустая строка — обычное дело в конце файла

            if len(cells) > len(header):
                warnings.append(
                    f"Строка {line_number}: значений больше, чем колонок "
                    f"({len(cells)} > {len(header)}); лишние проигнорированы."
                )

            raw = {
                column: (cells[index] if index < len(cells) else "")
                for index, column in enumerate(header)
            }

            parsed = self._build_field(raw, line_number, warnings, problems)

            if parsed is None:
                continue

            if parsed.name in seen_names:
                problems.append(
                    ParseProblem(
                        reason=(
                            f"поле «{parsed.name}» уже описано в строке {seen_names[parsed.name]}"
                        ),
                        row=line_number,
                        column="name",
                    )
                )
                continue

            seen_names[parsed.name] = line_number
            fields.append(parsed)

        if problems:
            raise TemplateParseError(
                f"Шаблон «{path.name}» содержит ошибки: {len(problems)}.",
                problems,
            )

        if not fields:
            raise TemplateParseError(f"В файле «{path.name}» не найдено ни одного поля проверки.")

        fields.sort(key=lambda item: item.order)

        logger.info(
            "Шаблон %s: %s полей, %s предупреждений",
            path.name,
            len(fields),
            len(warnings),
        )

        return ParseResult(fields=fields, warnings=warnings)

    # --------------------------------------------------------- чтение файла

    def _read_text(self, path: Path) -> tuple[str, str]:
        """Прочитать файл, определив кодировку.

        Возвращает текст и имя использованной кодировки.
        """

        try:
            data = path.read_bytes()
        except OSError as error:
            raise TemplateParseError(f"Не удалось прочитать файл: {error}") from error

        if not data.strip():
            raise TemplateParseError("Файл пуст.")

        detected = self._detect_encoding(data)

        if detected is not None:
            try:
                return data.decode(detected), detected
            except UnicodeDecodeError:  # pragma: no cover - защита от ложного детекта
                logger.warning("Автоопределение кодировки %s оказалось неверным", detected)

        for encoding in FALLBACK_ENCODINGS:
            try:
                return data.decode(encoding), encoding
            except UnicodeDecodeError:
                continue

        logger.warning("Кодировка не определена, читаю cp1251 с заменой символов")
        return data.decode("cp1251", errors="replace"), "cp1251/replace"

    @staticmethod
    def _detect_encoding(data: bytes) -> str | None:
        """Определить кодировку по содержимому файла."""

        if data.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"

        if _detect_from_bytes is None:
            return None

        try:
            match = _detect_from_bytes(data).best()
        except Exception:  # pragma: no cover - библиотека не должна ронять разбор
            logger.exception("Ошибка определения кодировки")
            return None

        if match is None or not match.encoding:
            return None

        encoding = match.encoding.lower()

        # charset-normalizer иногда возвращает экзотические однобайтовые
        # кодировки для коротких русских файлов — доверяем только тем, что
        # реально поддерживают кириллицу.
        if encoding in {"utf_8", "utf-8", "utf_8_sig", "cp1251", "windows-1251"}:
            return encoding

        return None

    # ------------------------------------------------------ разбор структуры

    def _split_rows(self, text: str) -> tuple[list[str], list[dict]]:
        """Разделить текст на нормализованный заголовок и строки данных."""

        delimiter = self._detect_delimiter(text)
        logger.debug("Определён разделитель: %r", delimiter)

        reader = csv.reader(io.StringIO(text), delimiter=delimiter)

        try:
            raw_header = next(reader)
        except StopIteration:
            return [], []

        header = [self._normalize_header(cell) for cell in raw_header]

        rows: list[dict] = []

        for cells in reader:
            rows.append({"line": reader.line_num, "cells": cells})

        return header, rows

    def _check_required_columns(self, header: list[str]) -> None:
        missing = [column for column in REQUIRED_COLUMNS if column not in header]

        if not missing:
            return

        raise TemplateParseError(
            "В шаблоне нет обязательных колонок: "
            + ", ".join(f"«{column}»" for column in missing)
            + ".",
            [
                ParseProblem(
                    reason=f"добавьте колонку «{column}»",
                    row=1,
                    column=column,
                )
                for column in missing
            ],
        )

    @staticmethod
    def _warn_unknown_columns(header: list[str], warnings: list[str]) -> None:
        unknown = [column for column in header if column and column not in KNOWN_COLUMNS]

        if unknown:
            warnings.append(
                "Неизвестные колонки проигнорированы: "
                + ", ".join(f"«{column}»" for column in unknown)
                + "."
            )

    @staticmethod
    def _normalize_header(cell: str) -> str:
        """Привести имя колонки к нижнему регистру без пробелов и BOM."""

        return cell.replace("\ufeff", "").strip().lower().replace(" ", "_").replace("-", "_")

    def _detect_delimiter(self, text: str) -> str:
        """Определить разделитель CSV.

        Основной критерий — число колонок в строке заголовков: значения с
        запятыми внутри (частый случай в русских шаблонах) находятся в данных,
        а не в заголовке, поэтому подсчёт по заголовку устойчивее ``csv.Sniffer``.
        """

        first_line = next((line for line in text.splitlines() if line.strip()), "")

        if first_line:
            counts = {
                delimiter: len(next(csv.reader([first_line], delimiter=delimiter)))
                for delimiter in DELIMITERS
            }
            best = max(counts, key=lambda item: counts[item])

            if counts[best] > 1:
                tied = [item for item in DELIMITERS if counts[item] == counts[best]]

                if len(tied) == 1:
                    return best

        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters="".join(DELIMITERS))

            if dialect.delimiter in DELIMITERS:
                return dialect.delimiter
        except csv.Error:
            pass

        return ","

    # ----------------------------------------------------------- разбор поля

    def _build_field(
        self,
        raw: dict[str, str],
        line_number: int,
        warnings: list[str],
        problems: list[ParseProblem],
    ) -> Field | None:
        """Собрать поле из строки CSV или зафиксировать проблему."""

        name = (raw.get("name") or "").strip()
        label = (raw.get("label") or "").strip()
        raw_type = (raw.get("type") or "").strip().lower()

        if not name:
            problems.append(
                ParseProblem(
                    reason="не заполнено машинное имя поля", row=line_number, column="name"
                )
            )
            return None

        if not label:
            warnings.append(
                f"Строка {line_number}: не заполнена подпись поля «{name}», использую машинное имя."
            )
            label = name

        field_type = self._parse_type(raw_type, name, line_number, warnings)
        options = self._parse_options(raw.get("options", ""))

        if field_type is FieldType.DROPDOWN and not options:
            problems.append(
                ParseProblem(
                    reason=(
                        f"для поля «{name}» типа «список» не заданы варианты в колонке «options»"
                    ),
                    row=line_number,
                    column="options",
                )
            )
            return None

        return Field(
            order=self._parse_order(raw.get("order", ""), line_number, warnings),
            name=name,
            label=label,
            type=field_type,
            group=(raw.get("group") or "").strip() or DEFAULT_GROUP,
            required=self._parse_bool(raw.get("required", "")),
            options=options,
            placeholder=(raw.get("placeholder") or "").strip(),
            description=(raw.get("description") or "").strip(),
            unit=(raw.get("unit") or "").strip(),
        )

    @staticmethod
    def _parse_type(
        raw_type: str,
        name: str,
        line_number: int,
        warnings: list[str],
    ) -> FieldType:
        if not raw_type:
            warnings.append(
                f"Строка {line_number}: у поля «{name}» не указан тип, использую «текст»."
            )
            return FieldType.TEXT

        try:
            return FieldType(raw_type)
        except ValueError:
            supported = ", ".join(item.value for item in FieldType)
            warnings.append(
                f"Строка {line_number}: неизвестный тип поля «{raw_type}» "
                f"у «{name}», использую «текст» (поддерживаются: {supported})."
            )
            return FieldType.TEXT

    @staticmethod
    def _parse_order(raw_order: str, line_number: int, warnings: list[str]) -> int:
        """Разобрать порядок сортировки с откатом на позицию строки."""

        value = (raw_order or "").strip()

        if not value:
            warnings.append(
                f"Строка {line_number}: не указан порядок «order», использую порядок строк в файле."
            )
            return line_number * 10

        try:
            return int(float(value.replace(",", ".")))
        except ValueError:
            warnings.append(
                f"Строка {line_number}: порядок «{value}» не является числом, "
                "использую порядок строк в файле."
            )
            return line_number * 10

    @staticmethod
    def _parse_bool(raw_value: str) -> bool:
        return (raw_value or "").strip().lower() in TRUE_VALUES

    @staticmethod
    def _parse_options(options_str: str) -> tuple[str, ...]:
        """Разобрать варианты для поля-списка."""

        if not options_str or not options_str.strip():
            return ()

        for separator in OPTION_SEPARATORS:
            if separator in options_str:
                return tuple(
                    option.strip() for option in options_str.split(separator) if option.strip()
                )

        return (options_str.strip(),)
