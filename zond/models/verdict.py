"""Оценка ответа: соответствие, несоответствие или нейтральный ответ.

Нужна для цветовой разметки протокола: несоответствия выделяются красным,
соответствия — зелёным. Формулировки вариантов задаёт шаблон, поэтому
классификация идёт по словарю типовых ответов, а для незнакомых формулировок
действует правило: ответ, начинающийся с «не », считается несоответствием.

Словарь намеренно небольшой и явный: лучше не подсветить неизвестный ответ,
чем подсветить его неверным цветом. Чтобы добавить свои формулировки,
достаточно расширить наборы ниже.
"""

from __future__ import annotations

from enum import StrEnum


class Verdict(StrEnum):
    """Итог проверки по одному полю."""

    OK = "ok"
    PROBLEM = "problem"
    NEUTRAL = "neutral"


#: Ответы, означающие соответствие требованию.
OK_ANSWERS = frozenset(
    {
        "соответствует",
        "исправно",
        "выполнено",
        "в наличии",
        "да",
        "работоспособно",
        "удовлетворительно",
        "хорошо",
        "отлично",
        "нормальная",
        "нормально",
        "в норме",
        "герметично",
        "допускается",
    }
)

#: Ответы, означающие несоответствие или необходимость вмешательства.
PROBLEM_ANSWERS = frozenset(
    {
        "не соответствует",
        "неисправно",
        "не выполнено",
        "отсутствует",
        "нет",
        "неудовлетворительно",
        "не работоспособно",
        "ограниченно работоспособно",
        "требует ремонта",
        "требуется ремонт",
        "аварийное",
        "критическая",
        "повышенная",
        "не герметично",
        "частично",
        "допускается с ограничениями",
    }
)

#: Итог работы с замечанием, выявленным в прошлый раз.
RESOLVED = "Устранено"
NOT_RESOLVED = "Не устранено"
NOT_CHECKED = "Не проверялось"

#: Варианты для поля «состояние замечания».
RESOLUTION_OPTIONS = (RESOLVED, NOT_RESOLVED, NOT_CHECKED)

#: Ответы, которые не являются ни соответствием, ни нарушением.
NEUTRAL_ANSWERS = frozenset({"не применимо", "не требуется", "", "—", "-"})


def classify(value: object | None) -> Verdict:
    """Определить оценку по значению поля."""

    if isinstance(value, bool):
        return Verdict.OK if value else Verdict.PROBLEM

    if value is None:
        return Verdict.NEUTRAL

    text = str(value).strip().lower().rstrip(".")

    if text in NEUTRAL_ANSWERS:
        return Verdict.NEUTRAL

    if text in OK_ANSWERS:
        return Verdict.OK

    if text in PROBLEM_ANSWERS:
        return Verdict.PROBLEM

    # Незнакомая формулировка: «Не соответствует проекту» и подобные.
    if text.startswith("не "):
        return Verdict.PROBLEM

    return Verdict.NEUTRAL


def is_problem(value: object | None) -> bool:
    return classify(value) is Verdict.PROBLEM


def is_ok(value: object | None) -> bool:
    return classify(value) is Verdict.OK
