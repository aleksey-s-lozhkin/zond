"""Главный объект приложения: связывает состояние, сервисы и экраны."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

import flet as ft

from zond.app.navigator import ZondNavigator
from zond.app.platform import has_local_files, is_android, is_desktop, is_mobile
from zond.app.state import ZondState
from zond.models.inspection import Inspection
from zond.services.errors import ReportError, StorageError, TemplateParseError, ZondError
from zond.services.inspection_factory import InspectionFactory
from zond.services.json_storage import DEFAULT_REPORTS_DIR, JsonStorage, StoredInspection
from zond.services.naming import safe_file_name
from zond.services.report_generator import ReportGenerator
from zond.services.sample_templates import sample_title, samples_dir
from zond.services.template_library import LibraryEntry, TemplateLibrary
from zond.services.template_loader import TemplateLoader
from zond.ui.colors import AppColors
from zond.ui.components.dialogs import (
    show_confirm,
    show_error,
)
from zond.ui.screens.base_screen import AppScreen
from zond.ui.screens.check_screen import CheckScreen
from zond.ui.screens.defects_screen import DefectsScreen
from zond.ui.screens.finish_screen import FinishScreen
from zond.ui.screens.help_screen import HelpScreen
from zond.ui.screens.history_screen import HistoryScreen
from zond.ui.screens.inspection_screen import InspectionScreen
from zond.ui.screens.templates_screen import TemplatesScreen
from zond.ui.screens.upload_screen import UploadScreen
from zond.ui.theme import build_theme

logger = logging.getLogger(__name__)

#: Поля шаблона, которые автоматически заполняются из сведений о проверке.
#: Ключ — машинное имя поля в CSV, значение — атрибут проверки. Имя
#: ``inspector`` оставлено как алиас для шаблонов, созданных до переименования.
METADATA_ALIASES = {
    "object_number": "object_name",
    "object_name": "object_name",
    "executor": "executor",
    "inspector": "executor",
}

DEFAULT_WINDOW = (430, 900)

#: Общедоступная папка «Документы» на Android.
PUBLIC_DOCUMENTS_DIR = Path("/storage/emulated/0/Documents")

#: Папка «Документы» на настольных платформах. Отдельная константа, чтобы
#: тесты не писали в домашний каталог разработчика.
HOME_DOCUMENTS_DIR = Path.home() / "Documents"

#: Каталог приложения в общей папке «Документы».
EXPORT_DIR_NAME = "ЗОНД"

#: Подкаталог с готовыми протоколами.
PROTOCOLS_SUBDIR = "Протоколы"

#: Подкаталог с библиотекой шаблонов.
TEMPLATES_SUBDIR = "Шаблоны"

#: Сколько копий выбранных файлов хранить в рабочем каталоге.
#:
#: Копия нужна, чтобы отправить шаблон: путь к исходному файлу в памяти
#: устройства после выбора недоступен. Но копить их бесконечно нельзя —
#: каждая так и остаётся на диске навсегда.
INCOMING_KEEP = 20

#: Типы файлов для системного меню «Поделиться».
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".csv": "text/csv",
}


def example_name(source: Path) -> str:
    """Имя примера в библиотеке.

    В поставке файлы названы техническими именами, а библиотека принадлежит
    пользователю: в файловом менеджере он должен видеть то же название, что и
    в списке приложения.
    """

    return safe_file_name(f"{sample_title(source)}{source.suffix}")


def _is_writable(directory: Path) -> bool:
    """Можно ли писать в каталог.

    В общие каталоги Android писать разрешено не всякому приложению, поэтому
    каталог не выбирается по имени, а проверяется пробной записью.
    """

    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".zond-write-check"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
    except OSError:
        return False

    return True


def _mime_type(path: Path) -> str:
    """Тип содержимого по расширению файла."""

    return MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")


class ZondApp:
    """Приложение «ЗОНД: ECTS»."""

    def __init__(self, page: ft.Page, storage: JsonStorage | None = None) -> None:
        self.page = page

        self.state = ZondState()
        self.storage = storage if storage is not None else JsonStorage()

        #: Каталог, куда складываются готовые протоколы, если платформа
        #: предоставляет общедоступную папку.
        self.export_dir: Path | None = None

        #: Предупреждение о библиотеке шаблонов, если общая папка недоступна.
        self.library_warning = ""

        #: Библиотека шаблонов. До первого prepare живёт в каталоге по
        #: умолчанию, затем переносится в общую папку, если она доступна.
        self.library = TemplateLibrary(
            DEFAULT_REPORTS_DIR / "templates",
            examples_dir=samples_dir(),
            name_of=example_name,
        )
        self.template_loader = TemplateLoader()
        self.report_generator = ReportGenerator()

        self.navigator = ZondNavigator(page)

        self.file_picker = ft.FilePicker()
        page.services.append(self.file_picker)

        # Открытие PDF средствами системы. page.launch_url объявлен
        # устаревшим с 0.80 и превратился в корутину, поэтому используем
        # сервис UrlLauncher.
        self.url_launcher = ft.UrlLauncher()
        page.services.append(self.url_launcher)

        # Каталоги устройства и системное меню «Поделиться» — нужны на
        # мобильных платформах: писать рядом с приложением нельзя, а ссылку
        # file:// открыть другим приложением не получится.
        self.storage_paths = ft.StoragePaths()
        page.services.append(self.storage_paths)

        self.share = ft.Share()
        page.services.append(self.share)

        self._configure_page()

    # ---------------------------------------------------------------- запуск

    def _configure_page(self) -> None:
        self.page.title = "ЗОНД: ECTS"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = build_theme()
        self.page.bgcolor = AppColors.BACKGROUND
        self.page.padding = 0
        self.page.spacing = 0

        # На мобильных платформах окна нет, а размер задаёт система.
        if not is_desktop(self.page):
            return

        window = getattr(self.page, "window", None)

        if window is None:  # pragma: no cover - веб-режим без окна
            return

        width, height = DEFAULT_WINDOW
        window.width = width
        window.height = height
        window.min_width = 380
        window.min_height = 600

    async def prepare(self) -> None:
        """Уточнить каталоги под текущую платформу и разложить шаблоны.

        На мобильных платформах каталог рядом с приложением доступен только
        для чтения, поэтому данные проверок переносятся в доступный каталог:
        без этого не сохранился бы даже черновик.

        Вызывается после показа стартового экрана: интерфейс строится
        синхронно, а каталог данных запрашивается у системы асинхронно.
        """

        root = await self._mobile_data_dir() if is_mobile(self.page) else None
        export = self._shared_dir(PROTOCOLS_SUBDIR)

        candidate = JsonStorage(
            root if root is not None else self.storage.root,
            pdf_dir=export,
        )

        # Хранилище подменяется только при реальном изменении каталогов:
        # иначе объект, переданный снаружи, расходится с состоянием
        # приложения.
        changed = candidate.root != self.storage.root or candidate.pdf_dir != self.storage.pdf_dir

        if changed:
            self.storage = candidate

        self.export_dir = export

        self._prepare_library(candidate)

        logger.info(
            "Каталоги: данные %s, протоколы %s, шаблоны %s",
            candidate.root,
            candidate.pdf_dir,
            self.library.root,
        )

        if changed and self.navigator.current is not None:
            self.restart()

    def _documents_base(self) -> Path | None:
        """Общая папка «Документы» на текущей платформе."""

        candidates = [PUBLIC_DOCUMENTS_DIR] if is_android(self.page) else [HOME_DOCUMENTS_DIR]

        for base in candidates:
            if base.is_dir():
                return base

        return None

    def _shared_dir(self, subdir: str) -> Path | None:
        """Папка приложения в «Документах» для файлов, которые забирает пользователь.

        Протоколы и шаблоны складываются туда, где пользователь ищет файлы
        сам: протокол забирают с телефона, а шаблоны, наоборот, кладут туда с
        компьютера. Если платформа не разрешает запись, каталог не
        используется, и вызывающий код берёт запасной вариант.
        """

        base = self._documents_base()

        if base is None:
            return None

        target = base / EXPORT_DIR_NAME / subdir

        if _is_writable(target):
            return target

        logger.info("Запись в %s недоступна, используется каталог приложения", target)
        return None

    def _prepare_library(self, storage: JsonStorage) -> None:
        """Собрать библиотеку шаблонов и разложить в неё примеры.

        Общая папка используется, только если она полностью пригодна. После
        переустановки приложения там остаётся каталог от прежней установки с
        другим идентификатором: создавать файлы в нём ещё можно, а читать и
        перезаписывать чужие — уже нет. Тогда библиотека уходит в каталог
        приложения, а причина показывается пользователю.
        """

        fallback = storage.root / "templates"
        shared = self._shared_dir(TEMPLATES_SUBDIR)

        if shared is not None:
            candidate = TemplateLibrary(
                shared,
                examples_dir=samples_dir(),
                name_of=example_name,
            )

            if candidate.is_usable():
                self.library = candidate
            else:
                logger.warning(
                    "Каталог %s недоступен, библиотека перенесена в %s",
                    shared,
                    fallback,
                )
                self.library_warning = (
                    "Папка «Документы/ЗОНД/Шаблоны» осталась от прежней "
                    "установки и недоступна. Шаблоны сохраняются в папке "
                    "приложения."
                )
                self.library = TemplateLibrary(
                    fallback,
                    examples_dir=samples_dir(),
                    name_of=example_name,
                )
        else:
            self.library = TemplateLibrary(
                fallback,
                examples_dir=samples_dir(),
                name_of=example_name,
            )

        self.library.ensure()

    def library_hint(self) -> str:
        """Короткая подпись, где лежат шаблоны."""

        if self.library.root == self.storage.root / "templates":
            return "папка приложения"

        return f"Документы/{EXPORT_DIR_NAME}/{TEMPLATES_SUBDIR}"

    def export_hint(self) -> str:
        """Короткая подпись, куда попадают готовые протоколы."""

        if self.export_dir is not None:
            return f"Документы/{EXPORT_DIR_NAME}/{PROTOCOLS_SUBDIR}"

        return str(self.storage.pdf_dir)

    def location_label(self, path: str | Path) -> str:
        """Понятное расположение файла.

        На телефоне полный путь вместе с длинным именем файла не помещается
        и выглядит как мусор: имя всё равно не набирают руками, а открывают
        кнопкой. Поэтому там показывается только папка, а полный путь
        остаётся в подсказке. На настольных платформах путь показывается
        целиком — он помещается, и по нему ходят в проводник.
        """

        target = Path(path)

        if self.export_dir is not None and target.parent == self.export_dir:
            return self.export_hint()

        if is_mobile(self.page):
            return target.parent.name

        return str(target)

    def open_help(self) -> None:
        """Открыть справку."""

        self.navigator.push(HelpScreen(self))

    async def _mobile_data_dir(self) -> Path | None:
        """Каталог для данных проверок на мобильной платформе.

        На Android сначала пробуется внешний каталог приложения: он виден по
        USB и в файловых менеджерах. Внутренний каталог документов доступен
        только самому приложению, и забрать из него протокол можно лишь через
        «Поделиться», поэтому он используется как запасной вариант.
        """

        for getter in self._mobile_dir_getters():
            try:
                raw = await getter()
            except Exception:
                logger.exception("Не удалось определить каталог данных")
                continue

            if raw:
                return Path(raw) / "reports"

        logger.warning("Платформа не сообщила доступный каталог для данных")
        return None

    def _mobile_dir_getters(self) -> list:
        """Каталоги-кандидаты в порядке предпочтения для текущей платформы."""

        getters: list = []

        if is_android(self.page):
            getters.append(self.storage_paths.get_external_storage_directory)

        getters.append(self.storage_paths.get_application_documents_directory)

        return getters

    def start(self) -> None:
        """Показать стартовый экран."""

        self.navigator.show(UploadScreen(self))
        logger.info(
            "Приложение запущено: платформа %s, каталог данных %s",
            getattr(self.page, "platform", "неизвестна"),
            self.storage.root,
        )

    # ------------------------------------------------------------ загрузка

    async def pick_template(self) -> None:
        """Выбрать CSV-шаблон и перейти к его проверке."""

        inspection = self.state.inspection

        if inspection is not None and not inspection.is_finished:
            show_confirm(
                self.page,
                "Начать новую проверку?",
                "Текущая проверка не завершена. Она будет сохранена как черновик, "
                "после чего можно выбрать новый шаблон.",
                on_confirm=lambda event: self._load_template(),
                confirm_text="Продолжить",
            )
            return

        await self._load_template()

    async def _load_template(self, path: Path | None = None) -> None:
        if path is None:
            path = await self._pick_file(["csv"], "Выберите CSV-шаблон проверки")

        if path is None:
            return

        try:
            template = self.template_loader.load(path)
        except TemplateParseError as error:
            show_error(self.page, "Не удалось загрузить шаблон", error.user_message())
            return
        except ZondError as error:
            show_error(self.page, "Не удалось загрузить шаблон", str(error))
            return

        self._preserve_current_inspection()
        self.state.set_template(template)
        self.navigator.push(CheckScreen(self))

    async def pick_inspection(self) -> None:
        """Открыть сохранённую проверку из файла."""

        path = await self._pick_file(["json"], "Выберите файл проверки")

        if path is None:
            return

        try:
            inspection = self.storage.load(path)
        except StorageError as error:
            show_error(self.page, "Не удалось открыть проверку", str(error))
            return

        self._open_inspection(inspection)

    async def _pick_file(self, extensions: list[str], title: str) -> Path | None:
        """Выбрать файл и вернуть путь к нему.

        На настольных платформах диалог отдаёт локальный путь. В песочнице
        Android и iOS такого пути нет, поэтому файл запрашивается вместе с
        содержимым и сохраняется в рабочий каталог приложения — дальше с ним
        работают как с обычным файлом.
        """

        local_paths = has_local_files(self.page)

        files = await self.file_picker.pick_files(
            dialog_title=title,
            # Фильтр по расширениям действует только при типе CUSTOM:
            # с типом ANY Flet просто игнорирует allowed_extensions, и в
            # диалоге видны все файлы подряд.
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=extensions,
            allow_multiple=False,
            with_data=not local_paths,
        )

        if not files:
            logger.debug("Выбор файла отменён пользователем")
            return None

        selected = files[0]

        if selected.path:
            return Path(selected.path)

        content = getattr(selected, "bytes", None)

        if content:
            return self._save_incoming(selected)

        show_error(
            self.page,
            "Файл недоступен",
            "Не удалось прочитать выбранный файл. "
            "Сохраните его в память устройства и попробуйте снова.",
        )
        return None

    def _save_incoming(self, selected) -> Path | None:
        """Сохранить полученный файл в рабочий каталог приложения."""

        name = getattr(selected, "name", "") or "template.csv"
        suffix = Path(name).suffix or ".csv"

        incoming = self.storage.root / "incoming"

        try:
            incoming.mkdir(parents=True, exist_ok=True)
            target = incoming / f"{uuid4().hex[:8]}_{Path(name).stem}{suffix}"
            target.write_bytes(selected.bytes)
            self._prune_incoming(incoming)
        except OSError as error:
            logger.exception("Не удалось сохранить выбранный файл")
            show_error(self.page, "Не удалось прочитать файл", str(error))
            return None

        logger.info("Выбранный файл сохранён: %s", target)
        return target

    def open_templates(self) -> None:
        """Открыть библиотеку шаблонов."""

        self.navigator.push(TemplatesScreen(self))

    async def open_template(self, entry: LibraryEntry) -> None:
        """Загрузить шаблон из библиотеки."""

        await self._load_template(entry.path)

    async def import_template(self) -> None:
        """Добавить шаблон из памяти устройства в библиотеку и открыть его."""

        path = await self._pick_file(["csv"], "Выберите CSV-шаблон проверки")

        if path is None:
            return

        target = self.library.import_file(path)

        if target is None:
            show_error(
                self.page,
                "Не удалось добавить шаблон",
                f"Файл «{path.name}» не удалось скопировать в библиотеку.",
            )
            return

        await self._load_template(target)

    def restore_examples(self) -> int:
        """Вернуть удалённые примеры и обновить список."""

        restored = self.library.restore_examples()

        if isinstance(self.navigator.current, TemplatesScreen):
            self.navigator.current.refresh()

        return restored

    def delete_template(self, entry: LibraryEntry) -> bool:
        """Удалить шаблон из библиотеки и обновить список."""

        if not self.library.delete(entry.name):
            return False

        if isinstance(self.navigator.current, TemplatesScreen):
            self.navigator.current.refresh()

        return True

    # ----------------------------------------------------------- сценарий

    def start_inspection(
        self,
        object_name: str,
        executor: str,
        previous: Inspection | None = None,
    ) -> None:
        """Создать проверку по текущему шаблону и открыть форму.

        Если передана прошлая проверка, значения переносятся, а прежние
        замечания выносятся на отдельный шаг разбора.
        """

        template = self.state.template

        if template is None:
            show_error(self.page, "Шаблон не загружен", "Сначала выберите CSV-шаблон.")
            return

        if previous is None:
            inspection = InspectionFactory.create(template, object_name, executor)
        else:
            inspection = InspectionFactory.repeat(
                previous,
                template,
                object_name,
                executor,
            )

        self._prefill_metadata(inspection)

        self.state.set_inspection(inspection)
        self.state.mark_modified()
        self.save_draft()

        if inspection.pending_resolutions:
            self.navigator.push(DefectsScreen(self))
            return

        self.navigator.push(InspectionScreen(self))

    async def share_template(self) -> None:
        """Отправить загруженный шаблон другому человеку.

        Шаблон — обычный CSV-файл, поэтому используется тот же механизм, что
        и для протоколов: на телефоне открывается системное меню отправки.
        """

        template = self.state.template

        if template is None:
            show_error(self.page, "Шаблон не загружен", "Сначала выберите CSV-шаблон.")
            return

        if not template.source_path:
            show_error(
                self.page,
                "Файл шаблона недоступен",
                "Шаблон загружен из файла, которого больше нет на устройстве.",
            )
            return

        await self.open_path(template.source_path)

    def repeat_candidates(self) -> list[Inspection]:
        """Завершённые проверки по текущему шаблону, начиная с последней.

        Черновики в список не попадают: переносить значения имеет смысл с
        завершённого выезда, а незаконченную проверку продолжают другим
        способом.
        """

        template = self.state.template

        if template is None:
            return []

        return [
            entry.inspection
            for entry in self.storage.list_stored()
            if not entry.is_draft and entry.inspection.template.name == template.name
        ]

    def finish_defect_review(self) -> None:
        """Закончить разбор замечаний и перейти к форме."""

        self.save_draft()
        self.navigator.push(InspectionScreen(self))

    def resume_inspection(self, entry: StoredInspection) -> None:
        """Продолжить сохранённую проверку."""

        self._open_inspection(entry.inspection)

    def save_draft(self) -> Path | None:
        """Сохранить текущую проверку как черновик."""

        inspection = self.state.inspection

        if inspection is None:
            return None

        try:
            path = self.storage.save_draft(inspection)
        except StorageError as error:
            show_error(self.page, "Не удалось сохранить черновик", str(error))
            return None

        self.state.mark_saved()
        return path

    def finish_inspection(self) -> None:
        """Завершить проверку и показать итоговый экран."""

        inspection = self.state.inspection

        if inspection is None:
            return

        inspection.mark_finished()

        try:
            self.storage.finalize(inspection)
        except StorageError as error:
            show_error(self.page, "Не удалось сохранить проверку", str(error))
            return

        self.state.mark_saved()
        self.navigator.push(FinishScreen(self))

    # ------------------------------------------------------------- отчёты

    def generate_pdf(self) -> Path | None:
        """Сформировать протокол по активной проверке."""

        inspection = self.state.inspection

        if inspection is None:
            return None

        return self.generate_pdf_for(inspection)

    def generate_pdf_for(self, inspection: Inspection) -> Path | None:
        """Сформировать протокол по указанной проверке."""

        try:
            return self.report_generator.generate(
                inspection,
                self.storage.pdf_path(inspection),
            )
        except (ReportError, OSError) as error:
            logger.exception("Ошибка формирования протокола")
            show_error(self.page, "Не удалось сформировать протокол", str(error))
            return None

    async def open_path(self, path: str | Path) -> None:
        """Открыть файл средствами системы.

        Асинхронный, потому что сервис запуска :class:`flet.UrlLauncher`
        работает через корутины.
        """

        target = Path(path)

        if not target.exists():
            show_error(self.page, "Файл не найден", f"Файл не найден:\n{target}")
            return

        if is_mobile(self.page):
            await self._share_file(target)
            return

        uri = target.resolve().as_uri()

        try:
            if not await self.url_launcher.can_launch_url(uri):
                show_error(
                    self.page,
                    "Не удалось открыть файл",
                    f"Система не может открыть этот файл автоматически.\n\n"
                    f"Откройте его вручную:\n{target}",
                )
                return

            await self.url_launcher.launch_url(uri)
            logger.info("Открыт файл %s", target)
        except Exception as error:  # pragma: no cover - зависит от платформы
            logger.exception("Не удалось открыть файл %s", target)
            show_error(
                self.page,
                "Не удалось открыть файл",
                f"Откройте файл вручную:\n{target}\n\n{error}",
            )

    async def _share_file(self, target: Path) -> None:
        """Отправить файл в системное меню «Поделиться».

        Ссылку ``file://`` на Android и iOS открыть другим приложением
        нельзя из-за песочницы, поэтому протокол предлагается сохранить
        или отправить средствами системы.
        """

        try:
            # share_files принимает именно ShareFile: со строкой на стороне
            # платформы разыменовывается пустой путь и вызов падает с
            # «Null check operator used on a null value».
            result = await self.share.share_files(
                [
                    ft.ShareFile(
                        path=str(target),
                        mime_type=_mime_type(target),
                        name=target.name,
                    )
                ],
                title=target.name,
            )
            logger.info("Файл предложен к отправке (%s): %s", result.status.value, target)
        except Exception as error:  # pragma: no cover - зависит от платформы
            logger.exception("Не удалось поделиться файлом %s", target)
            show_error(
                self.page,
                "Не удалось открыть файл",
                f"Файл сохранён по пути:\n{target}\n\n{error}",
            )

    @staticmethod
    def _prune_incoming(incoming: Path, keep: int = INCOMING_KEEP) -> None:
        """Оставить только последние копии выбранных файлов.

        Копии нужны для отправки шаблонов, но без ограничения они копятся
        бесконечно и молча занимают место. Лишние удаляются по времени
        изменения: самые свежие остаются.
        """

        try:
            files = sorted(
                (path for path in incoming.iterdir() if path.is_file()),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            logger.exception("Не удалось прочитать каталог выбранных файлов")
            return

        for stale in files[keep:]:
            try:
                stale.unlink()
            except OSError:
                logger.warning("Не удалось удалить %s", stale)

    # ---------------------------------------------------------- навигация

    def open_history(self) -> None:
        self.navigator.push(HistoryScreen(self))

    def restart(self) -> None:
        """Сбросить сеанс и вернуться на стартовый экран."""

        self.state.reset()
        self.navigator.show(UploadScreen(self))

    def delete_stored(self, entry: StoredInspection) -> None:
        """Удалить сохранённую проверку и обновить список истории."""

        try:
            self.storage.delete(entry.path)
        except StorageError as error:
            show_error(self.page, "Не удалось удалить запись", str(error))
            return

        active = self.state.inspection

        if active is not None and active.inspection_id == entry.inspection.inspection_id:
            self.state.reset()

        current = self.navigator.current

        if isinstance(current, HistoryScreen):
            current.refresh()

    # ----------------------------------------------------------- служебное

    def _open_inspection(self, inspection: Inspection) -> None:
        self.state.set_inspection(inspection)

        if inspection.is_finished:
            self.navigator.push(FinishScreen(self))
            return

        self.state.goto_first_incomplete_group()
        self.state.mark_modified()
        self.navigator.push(InspectionScreen(self))

    def _preserve_current_inspection(self) -> None:
        """Сохранить незавершённую проверку перед началом новой."""

        if self.state.inspection is None or not self.state.is_modified:
            return

        self.save_draft()

    @staticmethod
    def _prefill_metadata(inspection: Inspection) -> None:
        """Заполнить одноимённые поля шаблона из сведений о проверке."""

        for field_name, attribute in METADATA_ALIASES.items():
            value = getattr(inspection, attribute, "")

            if not value:
                continue

            item = inspection.get_item(field_name)

            if item is not None and item.is_empty:
                inspection.set_value(field_name, value)

    # ------------------------------------------------------------- отладка

    def current_screen(self) -> AppScreen | None:
        """Текущий экран (используется в тестах)."""

        return self.navigator.current
