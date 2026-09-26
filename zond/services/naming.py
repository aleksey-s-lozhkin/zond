"""Имена файлов проверок и протоколов.

Имя файла — то, что пользователь видит в списке файлов и в присоединённом
письме. Полное название шаблона вместе с отметкой времени давало имена длиной
больше пятидесяти символов: ``20260926-205119_tehnicheskie_sredstva_ohrany_f36bc8.pdf``.
В списке файлов такое имя переносится на четыре строки, а в письме обрезается.

Поэтому имя собирается из трёх коротких частей: дата, обозначение шаблона и
короткий номер проверки — ``2026-09-26_TSO_f36bc8.pdf``. Дата в формате ISO
сортируется как текст, поэтому файлы естественно выстраиваются по порядку.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - только для аннотаций
    from zond.models.inspection import Inspection

#: Короткие обозначения поставляемых шаблонов.
#: Латиница выбрана намеренно: имя файла уходит вложением в письмо и не должно
#: зависеть от кодировки почтового клиента или архиватора.
TEMPLATE_CODES = {
    "kip_kranovyy_uzel_mg": "KIP",
    "elektroustanovki": "EL",
    "tehnicheskie_sredstva_ohrany": "TSO",
    "server_bezopasnost": "SRV",
    "uaz_patriot_to": "UAZ",
    "podyomnoe_sooruzhenie": "PSO",
}

#: Сколько символов названия шаблона оставлять, если короткого кода нет.
FALLBACK_LENGTH = 12

#: Сколько символов номера проверки оставлять в имени файла.
ID_LENGTH = 6

#: Обозначение, если от названия шаблона ничего не осталось.
DEFAULT_CODE = "check"


def file_stem(inspection: Inspection) -> str:
    """Имя файла без расширения: дата, обозначение шаблона и номер проверки."""

    moment = (inspection.finished_at or inspection.started_at).astimezone()

    return (
        f"{moment:%Y-%m-%d}_{template_code(inspection.template.name)}"
        f"_{inspection.inspection_id[:ID_LENGTH]}"
    )


def template_code(name: str) -> str:
    """Короткое обозначение шаблона для имени файла.

    Для поставляемых шаблонов берётся принятое сокращение. Для чужого шаблона
    сокращение придумать нельзя, поэтому берётся начало названия по границе
    слова: обрезать посреди слова некрасиво, а угадывать аббревиатуру —
    хуже, чем показать начало.
    """

    known = TEMPLATE_CODES.get(name)

    if known:
        return known

    return _shorten(name)


def _shorten(name: str, limit: int = FALLBACK_LENGTH) -> str:
    text = safe_name(name)

    if len(text) <= limit:
        return text

    head, separator, _tail = text[:limit].rpartition("_")

    return head if separator and head else text[:limit]


def safe_name(value: str) -> str:
    """Оставить в строке только символы, допустимые в имени файла."""

    cleaned = [char if (char.isalnum() or char in "-_") else "_" for char in value.strip()]

    return "".join(cleaned).strip("_") or DEFAULT_CODE
