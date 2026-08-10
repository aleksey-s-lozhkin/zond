import flet as ft

from .colors import AppColors


def build_theme():

    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=AppColors.PRIMARY,
            surface=AppColors.SURFACE,
        )
    )