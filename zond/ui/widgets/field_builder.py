import flet as ft

from typing import Callable
from zond.models.field import Field, FieldType


class FieldBuilder:

    @staticmethod
    def build(
            field: Field,
            on_change: Callable | None = None,
    ):

        control: ft.Control


        match field.type:

            case FieldType.TEXT:

                control = ft.TextField(
                    hint_text=field.placeholder,
                    border_radius=10,
                    on_change=on_change,
                )


            case FieldType.NUMBER:

                control = ft.TextField(
                    hint_text=field.placeholder,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    border_radius=10,
                    on_change=on_change,
                )


            case FieldType.TEXTAREA:

                control = ft.TextField(
                    hint_text=field.placeholder,
                    multiline=True,
                    min_lines=3,
                    border_radius=10,
                    on_change=on_change,
                )


            case FieldType.CHECKBOX:

                control = ft.Checkbox(
                    on_change=on_change
                )


            case FieldType.DROPDOWN:

                control = ft.Dropdown(
                    options=[
                        ft.DropdownOption(
                            text=x
                        )
                        for x in field.options
                    ],
                    border_radius=10,
                    on_select=on_change,
                )


            case _:

                control = ft.Text(
                    f"Неизвестный тип {field.type}"
                )


        return ft.Column(
            spacing=8,

            controls=[

                ft.Text(
                    field.label,
                    size=16,
                    weight=ft.FontWeight.W_500,
                ),

                control

            ]
        )
