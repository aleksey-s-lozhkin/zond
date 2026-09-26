"""Образцы шаблонов, поставляемые вместе с приложением.

На телефоне выбрать CSV-файл из памяти устройства неудобно, а иногда и
нечем: файл сначала нужно туда перенести. Поэтому вместе с приложением
поставляются готовые образцы, и загрузить их можно прямо из интерфейса.

Каталог с образцами лежит рядом с пакетом приложения. Если его нет
(например, приложение собрано без шаблонов), список оказывается пустым,
и интерфейс просто не показывает соответствующий пункт.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

#: Имя каталога с образцами в корне приложения.
SAMPLES_DIR_NAME = "templates"

#: Отображаемые названия образцов по имени файла.
SAMPLE_TITLES = {
    "kip_kranovyy_uzel_mg": "КИП кранового узла газопровода",
    "elektroustanovki": "Электроустановки",
    "tehnicheskie_sredstva_ohrany": "Технические средства охраны",
    "sample": "Учебный пример",
}


def samples_dir() -> Path | None:
    """Каталог с образцами шаблонов, если он доступен приложению."""

    candidate = Path(__file__).resolve().parents[2] / SAMPLES_DIR_NAME

    if candidate.is_dir():
        return candidate

    logger.info("Каталог образцов шаблонов недоступен: %s", candidate)
    return None


def available_samples() -> list[Path]:
    """Образцы шаблонов, доступные в текущей сборке."""

    directory = samples_dir()

    if directory is None:
        return []

    return sorted(directory.glob("*.csv"))


def sample_title(path: Path) -> str:
    """Понятное название образца для интерфейса."""

    return SAMPLE_TITLES.get(path.stem, path.stem)


def sample_subtitle(path: Path) -> str:
    """Пояснение к образцу: сколько в нём полей и групп."""

    try:
        from zond.services.template_loader import TemplateLoader

        template = TemplateLoader().load(path)
    except Exception:  # pragma: no cover - защита от повреждённого образца
        logger.exception("Не удалось прочитать образец %s", path)
        return path.name

    return f"{len(template.fields)} полей · {template.total_groups} групп · {path.name}"
