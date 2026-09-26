"""Библиотека шаблонов проверок.

Шаблон — обычный CSV-файл, но приложение должно быть рабочим инструментом, а
не витриной: пользователь постепенно собирает свою базу шаблонов, и всё, что
в ней лежит, он может удалить или заменить.

Поэтому примеры, поставляемые внутри приложения, при первом запуске
копируются в папку библиотеки. Иначе их нельзя ни удалить, ни поправить, и
список выглядит неизменяемым — а он должен принадлежать пользователю. Туда же
попадают шаблоны, выбранные из памяти устройства: искать файл в «Загрузках»
каждый раз не нужно.

Копирование выполняется один раз. Отметка о том, какие примеры уже
раскладывались, хранится в служебном файле: удалённый пример не появится
снова при следующем запуске, а новый пример из свежей версии приложения
добавится.
"""

from __future__ import annotations

import json
import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

#: Служебный файл с отметкой о разложенных примерах.
MARKER_NAME = ".examples.json"

#: Расширение файлов шаблонов.
TEMPLATE_SUFFIX = ".csv"


@dataclass(frozen=True, slots=True)
class LibraryEntry:
    """Шаблон в библиотеке."""

    path: Path

    @property
    def name(self) -> str:
        """Машинное имя шаблона — имя файла без расширения."""

        return self.path.stem


class TemplateLibrary:
    """Папка с шаблонами, которой владеет пользователь."""

    def __init__(
        self,
        root: Path,
        examples_dir: Path | None = None,
        name_of: Callable[[Path], str] | None = None,
    ) -> None:
        self.root = Path(root)
        self.examples_dir = Path(examples_dir) if examples_dir is not None else None

        #: Как назвать пример в библиотеке. Имена в поставке технические
        #: (``kip_kranovyy_uzel_mg``), а папка принадлежит пользователю:
        #: в файловом менеджере он должен видеть то же, что и в приложении.
        self.name_of = name_of or (lambda path: path.name)

    # ------------------------------------------------------------- каталог

    def ensure(self) -> None:
        """Создать каталог библиотеки и разложить примеры при первом запуске."""

        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.exception("Не удалось создать каталог шаблонов %s", self.root)
            return

        self._seed_examples()

    def _seed_examples(self) -> None:
        """Скопировать примеры, которые ещё не раскладывались.

        Отметка хранит имена уже разложенных файлов, а не просто факт
        копирования: иначе удалённый пользователем пример возвращался бы при
        каждом запуске.
        """

        if self.examples_dir is None or not self.examples_dir.is_dir():
            return

        seeded = self._read_seeded()
        added: list[str] = []

        for source in sorted(self.examples_dir.glob(f"*{TEMPLATE_SUFFIX}")):
            if source.name in seeded:
                continue

            target = self.root / self.name_of(source)

            try:
                if not target.exists():
                    shutil.copy2(source, target)

                added.append(source.name)
            except OSError:
                logger.exception("Не удалось скопировать пример %s", source)

        if added:
            self._write_seeded(seeded | set(added))
            logger.info("В библиотеку добавлено примеров: %s", len(added))

    def _read_seeded(self) -> set[str]:
        try:
            payload = json.loads((self.root / MARKER_NAME).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return set()

        names = payload.get("seeded") if isinstance(payload, dict) else None

        return {str(name) for name in names} if isinstance(names, list) else set()

    def _write_seeded(self, names: set[str]) -> None:
        payload = {"seeded": sorted(names)}

        try:
            (self.root / MARKER_NAME).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            logger.exception("Не удалось сохранить отметку о примерах")

    # -------------------------------------------------------------- список

    def list_entries(self) -> list[LibraryEntry]:
        """Шаблоны библиотеки по алфавиту."""

        try:
            paths = sorted(
                path
                for path in self.root.glob(f"*{TEMPLATE_SUFFIX}")
                if path.is_file() and not path.name.startswith(".")
            )
        except OSError:
            logger.exception("Не удалось прочитать каталог шаблонов %s", self.root)
            return []

        return [LibraryEntry(path=path) for path in paths]

    def path_of(self, name: str) -> Path:
        """Путь к шаблону библиотеки по машинному имени."""

        return self.root / f"{name}{TEMPLATE_SUFFIX}"

    def missing_examples(self) -> list[Path]:
        """Примеры поставки, которых нет в библиотеке.

        Нужны, чтобы предложить восстановление: удаление необратимо, и без
        этого вернуть случайно удалённый пример было бы нечем.
        """

        if self.examples_dir is None or not self.examples_dir.is_dir():
            return []

        return [
            source
            for source in sorted(self.examples_dir.glob(f"*{TEMPLATE_SUFFIX}"))
            if not (self.root / self.name_of(source)).exists()
        ]

    def restore_examples(self) -> int:
        """Вернуть в библиотеку отсутствующие примеры поставки.

        Существующие файлы не трогаются: пользователь мог поправить пример под
        себя, и затирать его правку нельзя.
        """

        restored = 0

        for source in self.missing_examples():
            try:
                shutil.copy2(source, self.root / self.name_of(source))
            except OSError:
                logger.exception("Не удалось восстановить пример %s", source)
                continue

            restored += 1

        if restored:
            logger.info("Восстановлено примеров: %s", restored)

        return restored

    # ------------------------------------------------------------ операции

    def import_file(self, source: str | Path) -> Path | None:
        """Добавить шаблон в библиотеку.

        Файл с тем же именем заменяется: пользователь правит шаблон на
        компьютере и приносит новую версию, а не второй такой же файл.
        """

        origin = Path(source)
        target = self.root / origin.name

        try:
            self.root.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origin, target)
        except OSError:
            logger.exception("Не удалось добавить шаблон %s в библиотеку", origin)
            return None

        logger.info("Шаблон добавлен в библиотеку: %s", target)
        return target

    def delete(self, name: str) -> bool:
        """Удалить шаблон из библиотеки."""

        target = self.path_of(name)

        try:
            target.unlink()
        except FileNotFoundError:
            return False
        except OSError:
            logger.exception("Не удалось удалить шаблон %s", target)
            return False

        logger.info("Шаблон удалён: %s", target)
        return True
