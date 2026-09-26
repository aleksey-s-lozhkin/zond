"""Определение платформы и связанные с ней особенности.

На мобильных платформах поведение отличается в трёх местах: каталог данных
доступен только для чтения рядом с приложением, файловый диалог не отдаёт
локальный путь к выбранному файлу, а ссылки ``file://`` нельзя открыть другим
приложением. Здесь собраны признаки платформы, чтобы эти различия были в одном
месте, а не расползались по экранам и сервисам.
"""

from __future__ import annotations

import flet as ft

#: Платформы с сенсорным вводом, где приложение работает из песочницы.
MOBILE_PLATFORMS = frozenset(
    {
        ft.PagePlatform.ANDROID,
        ft.PagePlatform.ANDROID_TV,
        ft.PagePlatform.IOS,
    }
)

#: Платформы Android: внешний каталог приложения виден пользователю.
ANDROID_PLATFORMS = frozenset({ft.PagePlatform.ANDROID, ft.PagePlatform.ANDROID_TV})

#: Настольные платформы, где доступны окно и локальные файлы.
DESKTOP_PLATFORMS = frozenset(
    {
        ft.PagePlatform.MACOS,
        ft.PagePlatform.WINDOWS,
        ft.PagePlatform.LINUX,
    }
)


def _platform_of(page: ft.Page) -> ft.PagePlatform | None:
    """Платформа страницы или ``None``, если её не удалось определить."""

    return getattr(page, "platform", None)


def is_mobile(page: ft.Page) -> bool:
    """Работает ли приложение на мобильной платформе."""

    return _platform_of(page) in MOBILE_PLATFORMS


def is_android(page: ft.Page) -> bool:
    """Работает ли приложение на Android."""

    return _platform_of(page) in ANDROID_PLATFORMS


def is_desktop(page: ft.Page) -> bool:
    """Работает ли приложение на настольной платформе."""

    platform = _platform_of(page)

    # Платформа неизвестна (например, в тестах или в веб-режиме) — считаем,
    # что ограничений мобильной песочницы нет.
    if platform is None:
        return True

    return platform in DESKTOP_PLATFORMS


def has_local_files(page: ft.Page) -> bool:
    """Отдаёт ли файловый диалог локальный путь к выбранному файлу."""

    return is_desktop(page)
