"""Ошибки предметной области.

Все исключения приложения наследуются от :class:`ZondError`, чтобы UI-слой мог
отличить ожидаемую проблему (показать пользователю понятный диалог) от
программной ошибки (показать traceback в лог).
"""

from __future__ import annotations

from dataclasses import dataclass


class ZondError(Exception):
    """Базовая ошибка приложения."""


class TemplateError(ZondError):
    """Ошибка при работе с шаблоном проверки."""


@dataclass(frozen=True, slots=True)
class ParseProblem:
    """Одна проблема, найденная при разборе шаблона."""

    reason: str
    row: int | None = None
    column: str | None = None

    def __str__(self) -> str:
        if self.row is None:
            return self.reason
        if self.column is None:
            return f"строка {self.row}: {self.reason}"
        return f"строка {self.row}, колонка «{self.column}»: {self.reason}"


class TemplateParseError(TemplateError):
    """Шаблон не удалось разобрать.

    Несёт список :class:`ParseProblem`, чтобы пользователь мог исправить файл
    за один проход, а не по одной ошибке за раз.
    """

    def __init__(self, message: str, problems: list[ParseProblem] | None = None) -> None:
        self.problems: list[ParseProblem] = list(problems or [])
        super().__init__(message)

    def user_message(self, limit: int = 10) -> str:
        """Текст для показа в диалоге: заголовок + перечень проблем."""

        if not self.problems:
            return str(self)

        shown = self.problems[:limit]
        lines = [str(self), ""]
        lines.extend(f"• {problem}" for problem in shown)

        hidden = len(self.problems) - len(shown)
        if hidden > 0:
            lines.append(f"…и ещё {hidden}.")

        return "\n".join(lines)


class StorageError(ZondError):
    """Ошибка чтения или записи файла проверки."""


class ReportError(ZondError):
    """Ошибка формирования отчёта."""
