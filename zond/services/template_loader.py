"""Загрузка шаблона проверки из CSV."""

from __future__ import annotations

import logging
from pathlib import Path

from zond.models.template import Template
from zond.services.csv_parser import CSVParser

logger = logging.getLogger(__name__)


class TemplateLoader:
    """Превращает CSV-файл в :class:`Template`."""

    def __init__(self, parser: CSVParser | None = None) -> None:
        self.parser = parser or CSVParser()

    def load(self, file_path: str | Path, name: str | None = None) -> Template:
        """Загрузить шаблон.

        Args:
            file_path: путь к CSV-файлу шаблона.
            name: отображаемое имя шаблона; по умолчанию — имя файла без
                расширения.

        Raises:
            TemplateParseError: файл нечитаем или структурно некорректен.
        """

        path = Path(file_path)
        result = self.parser.parse_template(path)

        template = Template(
            name=name or path.stem,
            fields=result.fields,
            warnings=list(result.warnings),
        )

        logger.info(
            "Шаблон «%s» загружен: %s полей, %s групп",
            template.name,
            len(template.fields),
            template.total_groups,
        )

        return template
