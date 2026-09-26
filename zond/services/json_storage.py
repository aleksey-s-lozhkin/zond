"""Сохранение и загрузка проверок в JSON.

Структура каталога данных::

    reports/
      drafts/        # незавершённые проверки (черновики)
      inspections/   # завершённые проверки
      pdf/           # сформированные протоколы

Запись выполняется атомарно (временный файл + :func:`os.replace`), поэтому
прерывание процесса не оставляет повреждённый JSON.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from zond.models.inspection import Inspection, format_datetime
from zond.services.errors import StorageError

logger = logging.getLogger(__name__)

#: Каталог данных по умолчанию — ``<корень проекта>/reports``.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"


@dataclass(frozen=True, slots=True)
class StoredInspection:
    """Сохранённая проверка вместе с её метаданными."""

    path: Path
    inspection: Inspection

    @property
    def is_draft(self) -> bool:
        return self.inspection.finished_at is None

    @property
    def title(self) -> str:
        return self.inspection.title

    @property
    def template_name(self) -> str:
        return self.inspection.template.name

    @property
    def executor(self) -> str:
        return self.inspection.executor

    @property
    def started_at(self) -> datetime:
        return self.inspection.started_at

    @property
    def finished_at(self) -> datetime | None:
        return self.inspection.finished_at

    @property
    def total(self) -> int:
        return self.inspection.total_items

    @property
    def answered(self) -> int:
        return self.inspection.answered_count

    @property
    def progress(self) -> float:
        return self.inspection.progress

    @property
    def status(self) -> str:
        return "черновик" if self.is_draft else "завершена"

    @property
    def subtitle(self) -> str:
        """Строка с датой, статусом и прогрессом для списка."""

        moment = self.finished_at or self.started_at
        return f"{format_datetime(moment)} · {self.status} · заполнено {self.answered}/{self.total}"


class JsonStorage:
    """Хранилище проверок на файловой системе."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else DEFAULT_REPORTS_DIR
        self.inspections_dir = self.root / "inspections"
        self.drafts_dir = self.root / "drafts"
        self.pdf_dir = self.root / "pdf"

    # ------------------------------------------------------------- каталоги

    def ensure_dirs(self) -> None:
        for directory in (self.inspections_dir, self.drafts_dir, self.pdf_dir):
            directory.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------- сохранение

    def save(self, inspection: Inspection, path: str | Path) -> Path:
        """Сохранить проверку по указанному пути (атомарно)."""

        target = Path(path)
        payload = inspection.to_dict()

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            self._write_json(payload, target)
        except OSError as error:
            raise StorageError(f"Не удалось сохранить проверку: {error}") from error

        logger.info("Проверка %s сохранена в %s", inspection.inspection_id, target)
        return target

    def finalize(self, inspection: Inspection) -> Path:
        """Сохранить завершённую проверку и удалить её черновик."""

        self.ensure_dirs()
        path = self.save(inspection, self.inspections_dir / self.file_name(inspection))
        self.discard_draft(inspection)
        return path

    def save_draft(self, inspection: Inspection) -> Path:
        """Сохранить незавершённую проверку."""

        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        path = self.drafts_dir / f"{inspection.inspection_id}.json"
        return self.save(inspection, path)

    def discard_draft(self, inspection: Inspection) -> None:
        """Удалить черновик проверки, если он есть."""

        draft = self.drafts_dir / f"{inspection.inspection_id}.json"

        if draft.exists():
            try:
                draft.unlink()
            except OSError as error:  # pragma: no cover - редкий случай
                logger.warning("Не удалось удалить черновик %s: %s", draft, error)

    def delete(self, path: str | Path) -> None:
        """Удалить сохранённую проверку."""

        target = Path(path)

        try:
            target.unlink()
        except FileNotFoundError:
            logger.warning("Файл уже удалён: %s", target)
            return
        except OSError as error:
            raise StorageError(f"Не удалось удалить файл: {error}") from error

        logger.info("Удалён файл проверки %s", target)

    # -------------------------------------------------------------- загрузка

    def load(self, path: str | Path) -> Inspection:
        """Загрузить проверку из JSON."""

        target = Path(path)
        data = self._read_json(target)

        try:
            return Inspection.from_dict(data)
        except StorageError:
            raise
        except (TypeError, ValueError) as error:
            raise StorageError(f"Файл «{target.name}» повреждён: {error}") from error

    def list_stored(self) -> list[StoredInspection]:
        """Список сохранённых проверок: сначала черновики, затем завершённые.

        Повреждённые файлы не роняют список — они пропускаются с записью в лог.
        """

        stored: list[StoredInspection] = []

        for path in self._iter_files():
            try:
                stored.append(StoredInspection(path=path, inspection=self.load(path)))
            except StorageError as error:
                logger.warning("Пропускаю %s: %s", path.name, error)

        stored.sort(key=lambda item: (item.is_draft, item.started_at), reverse=True)
        return stored

    def _iter_files(self) -> list[Path]:
        paths: list[Path] = []

        for directory in (self.drafts_dir, self.inspections_dir):
            if directory.is_dir():
                paths.extend(sorted(directory.glob("*.json")))

        return paths

    # --------------------------------------------------------- имена файлов

    def file_name(self, inspection: Inspection) -> str:
        """Имя файла завершённой проверки."""

        moment = (inspection.finished_at or inspection.started_at).astimezone()
        stamp = moment.strftime("%Y%m%d-%H%M%S")
        return f"{stamp}_{_slug(inspection.template.name)}_{inspection.inspection_id[:6]}.json"

    def pdf_path(self, inspection: Inspection) -> Path:
        """Путь для PDF-протокола этой проверки."""

        return self.pdf_dir / f"{Path(self.file_name(inspection)).stem}.pdf"

    # ------------------------------------------------------- файловые утилиты

    @staticmethod
    def _write_json(payload: dict, path: Path) -> None:
        """Записать JSON атомарно: временный файл в том же каталоге + replace."""

        descriptor, temp_name = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
        )

        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())

            os.replace(temp_name, path)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise

    @staticmethod
    def _read_json(path: Path) -> dict:
        try:
            with path.open(encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError as error:
            raise StorageError(f"Файл не найден: {path}") from error
        except json.JSONDecodeError as error:
            raise StorageError(
                f"Файл «{path.name}» не является корректным JSON: {error}"
            ) from error
        except OSError as error:
            raise StorageError(f"Не удалось прочитать файл: {error}") from error


def _slug(value: str, limit: int = 40) -> str:
    """Безопасное для файловой системы имя из названия шаблона."""

    cleaned = [char if (char.isalnum() or char in "-_") else "_" for char in value.strip()]
    slug = "".join(cleaned).strip("_")

    while "__" in slug:
        slug = slug.replace("__", "_")

    return (slug or "inspection")[:limit]
