"""Иконки приложения.

Единый источник иконок: экраны не должны обращаться к ``ft.Icons`` напрямую,
иначе замена иконки превращается в поиск по всему проекту.
"""

from __future__ import annotations

import flet as ft


class AppIcons:
    """Иконки, используемые интерфейсом."""

    APP = ft.Icons.SETTINGS_INPUT_COMPONENT

    UPLOAD = ft.Icons.UPLOAD_FILE
    OPEN = ft.Icons.FOLDER_OPEN
    HISTORY = ft.Icons.HISTORY
    SAVE = ft.Icons.SAVE_OUTLINED
    PDF = ft.Icons.PICTURE_AS_PDF
    DELETE = ft.Icons.DELETE_OUTLINE
    PLAY = ft.Icons.PLAY_ARROW

    BACK = ft.Icons.ARROW_BACK
    NEXT = ft.Icons.ARROW_FORWARD
    ADD = ft.Icons.ADD
    CHEVRON = ft.Icons.CHEVRON_RIGHT

    HELP = ft.Icons.HELP_OUTLINE
    SAMPLES = ft.Icons.LIBRARY_BOOKS
    TEMPLATE = ft.Icons.DESCRIPTION_OUTLINED
    FOLDER = ft.Icons.FOLDER_OUTLINED
    STORAGE = ft.Icons.INSERT_DRIVE_FILE_OUTLINED

    SUCCESS = ft.Icons.CHECK_CIRCLE
    WARNING = ft.Icons.WARNING_AMBER_ROUNDED
    ERROR = ft.Icons.ERROR_OUTLINE
    INFO = ft.Icons.INFO_OUTLINE

    CALENDAR = ft.Icons.CALENDAR_MONTH
    TIME = ft.Icons.SCHEDULE
    LIST = ft.Icons.LIST_ALT
    TEXT = ft.Icons.SHORT_TEXT
    NUMBER = ft.Icons.NUMBERS
    CHECKBOX = ft.Icons.CHECK_BOX_OUTLINED
    TOGGLE = ft.Icons.CHECK_BOX
