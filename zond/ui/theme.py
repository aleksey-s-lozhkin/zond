"""Сборка темы Flet из дизайн-токенов."""

from __future__ import annotations

import flet as ft

from zond.ui.colors import AppColors
from zond.ui.design import FontSize


def build_theme() -> ft.Theme:
    """Тема приложения: цвета, типографика, форма элементов."""

    return ft.Theme(
        use_material3=True,
        color_scheme=ft.ColorScheme(
            primary=AppColors.PRIMARY,
            on_primary=AppColors.WHITE,
            primary_container=AppColors.PRIMARY_SOFT,
            on_primary_container=AppColors.PRIMARY_DARK,
            secondary=AppColors.TEXT_SECONDARY,
            on_secondary=AppColors.WHITE,
            surface=AppColors.SURFACE,
            on_surface=AppColors.TEXT,
            surface_container=AppColors.SURFACE_ALT,
            on_surface_variant=AppColors.TEXT_SECONDARY,
            error=AppColors.ERROR,
            on_error=AppColors.WHITE,
            error_container=AppColors.ERROR_SOFT,
            on_error_container=AppColors.ERROR,
            outline=AppColors.BORDER_STRONG,
            outline_variant=AppColors.BORDER,
        ),
        scaffold_bgcolor=AppColors.BACKGROUND,
        divider_color=AppColors.BORDER,
        text_theme=ft.TextTheme(
            body_medium=ft.TextStyle(size=FontSize.BODY, color=AppColors.TEXT),
            body_small=ft.TextStyle(size=FontSize.CAPTION, color=AppColors.TEXT_SECONDARY),
            title_medium=ft.TextStyle(
                size=FontSize.SUBTITLE,
                weight=ft.FontWeight.W_600,
                color=AppColors.TEXT,
            ),
            title_large=ft.TextStyle(
                size=FontSize.TITLE,
                weight=ft.FontWeight.BOLD,
                color=AppColors.TEXT,
            ),
        ),
    )
