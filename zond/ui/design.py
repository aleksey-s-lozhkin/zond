"""Токены размеров и типографики."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Space:
    """Шаг отступов."""

    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


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

    CAPTION = 11
    BODY = 13
    #: Подписи кнопок: крупнее основного текста, но не настолько, чтобы
    #: слово перестало помещаться в кнопку и рвалось посередине.
    BUTTON = 14
    SUBTITLE = 15
    TITLE = 19
    HERO = 26


@dataclass(frozen=True)
class ControlSize:
    """Размеры элементов управления."""

    BUTTON_HEIGHT = 46
    INPUT_HEIGHT = 42
    ICON = 56
    LOGO = 92
    PROGRESS_BAR = 6


@dataclass(frozen=True)
class StrokeWidth:
    """Толщины линий."""

    HAIRLINE = 1
    EMPHASIS = 2
