from pathlib import Path

from zond.models.template import Template
from zond.services.csv_parser import CSVParser


class TemplateLoader:
    """ Загружает шаблон проверки из CSV. """

    def __init__(self):

        self.parser = CSVParser()


    def load(self, file_path: str) -> Template:

        fields = self.parser.parse_template(
            file_path
        )

        if fields is None:
            raise ValueError(
                "Не удалось загрузить шаблон"
            )

        return Template(
            name=Path(file_path).stem,
            fields=fields,
        )
