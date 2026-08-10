from dataclasses import dataclass


@dataclass(frozen=True)
class Space:
    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32
    XXL = 48


@dataclass(frozen=True)
class Radius:
    SM = 8
    MD = 12
    LG = 16
    XL = 24


@dataclass(frozen=True)
class FontSize:
    CAPTION = 12
    BODY = 14
    SUBTITLE = 16
    TITLE = 22
    HERO = 30


@dataclass(frozen=True)
class ControlSize:
    BUTTON_HEIGHT = 52
    INPUT_HEIGHT = 48
    ICON = 64
    