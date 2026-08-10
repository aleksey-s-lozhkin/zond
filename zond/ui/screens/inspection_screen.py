import flet as ft

from zond.app.state import ZondState
from zond.ui.widgets.field_builder import FieldBuilder


class InspectionScreen(ft.Container):

    def __init__(self, state: ZondState):

        self.state = state

        super().__init__(
            expand=True,
            content=self._build()
        )


    def _build(self):

        fields = self.state.current_fields

        if not fields:
            return ft.Text(
                "Проверка завершена"
            )


        controls: list[ft.Control] = [

            ft.Text(
                f"Группа: {self.state.current_group}",
                size=24,
                weight=ft.FontWeight.BOLD,
            )

        ]


        for field in fields:

            controls.append(
                FieldBuilder.build(
                    field,
                    lambda e, f=field: self.save_answer(f,e)
                )
            )


        controls.append(

            ft.Button(
                content=ft.Text("Следующая группа"),
                on_click=self.next_group,
            )

        )

        return ft.Container(
            width=500,
            padding=20,

            content=ft.Column(
                alignment=ft.MainAxisAlignment.START,
                scroll=ft.ScrollMode.AUTO,
                spacing=15,
                controls=controls,
            )
        )


    def next_group(self, e):

        if self.state.next_group():

            self.content = self._build()

        else:

            self.content = ft.Text(
                "Проверка завершена"
            )

        self.update()

    def save_answer(self, field, e):

        if not self.state.inspection:
            return

        item = self.state.inspection.get_item(
            field.name
        )

        if item is None:
            return

        item.value = e.control.value

        print(item.field.name, "=", item.value)
