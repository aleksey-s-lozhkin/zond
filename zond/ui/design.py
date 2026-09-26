"""Токены размеров и типографики."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Space:
    """Шаг отступов."""

    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32
    XXL = 48


@dataclass(frozen=True)
class Radius:
    """Радиусы скругления."""

    SM = 8
    MD = 12
    LG = 16
    XL = 24


@dataclass(frozen=True)
class FontSize:
    """Размеры шрифта."""

    CAPTION = 12
    BODY = 14
    SUBTITLE = 16
    TITLE = 22
    HERO = 30


@dataclass(frozen=True)
class ControlSize:
    """Размеры элементов управления."""

    BUTTON_HEIGHT = 52
    INPUT_HEIGHT = 48
    ICON = 64
    LOGO = 110
    PROGRESS_BAR = 6


@dataclass(frozen=True)
class StrokeWidth:
    """Толщины линий."""

    HAIRLINE = 1
    EMPHASIS = 2
