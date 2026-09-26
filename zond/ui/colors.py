"""Цветовые токены приложения."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppColors:
    """Палитра. Используется и в UI, и в PDF-отчёте."""

    BACKGROUND = "#F5F7FA"

    SURFACE = "#FFFFFF"
    SURFACE_ALT = "#F9FAFB"

    PRIMARY = "#2563EB"
    PRIMARY_DARK = "#1D4ED8"
    PRIMARY_SOFT = "#EFF4FF"
    PRIMARY_BORDER = "#A8C4F0"

    SUCCESS = "#16A34A"
    SUCCESS_SOFT = "#ECFDF5"

    WARNING = "#F59E0B"
    WARNING_SOFT = "#FFFBEB"

    ERROR = "#DC2626"
    ERROR_SOFT = "#FEF2F2"

    TEXT = "#111827"
    TEXT_SECONDARY = "#6B7280"
    TEXT_DISABLED = "#9CA3AF"

    BORDER = "#E5E7EB"
    BORDER_STRONG = "#D1D5DB"

    WHITE = "#FFFFFF"
