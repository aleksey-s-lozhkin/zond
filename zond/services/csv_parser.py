import csv

from pathlib import Path

from zond.models.field import Field, FieldType


class CSVParser:
    """Парсер CSV с поддержкой группировки"""

    def detect_encoding(self, file_path):
        """Определяет кодировку файла перебором"""
        encodings = [
            'utf-8-sig', 'utf-8', 'cp1251', 'windows-1251',
            'koi8-r', 'cp866', 'mac-cyrillic', 'latin-1'
        ]

        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    f.read(1000)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue

        return 'utf-8'

    def parse_template(self, file_path):
        """ Парсит шаблон CSV с поддержкой групп """

        try:
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(
                    f"Файл не найден: {path}"
                )

            encoding = self.detect_encoding(file_path)
            print(f"🔍 Определена кодировка: {encoding}")

            with open(file_path, 'r', encoding=encoding) as f:
                # Определяем разделитель
                sample = f.read(1024)
                f.seek(0)
                delimiter = self._detect_delimiter(sample)
                print(f"🔍 Определен разделитель: '{delimiter}'")

                reader = csv.DictReader(f, delimiter=delimiter)

                required_columns = {
                    "name",
                    "label",
                    "type",
                }

                missing = required_columns - set(reader.fieldnames or [])

                if missing:
                    raise ValueError(
                        f"Отсутствуют обязательные колонки: {', '.join(sorted(missing))}"
                    )

                fields = []

                if not reader.fieldnames:
                    print("❌ Не удалось прочитать заголовки CSV")
                    return None

                print(f"📋 Найденные колонки: {reader.fieldnames}")

                for row in reader:

                    field_type = row.get(
                        "type",
                        "text",
                    ).strip().lower()

                    try:
                        field_type = FieldType(field_type)
                    except ValueError:
                        field_type = FieldType.TEXT

                    field = Field(
                        order=int(row.get("order", 0)),
                        name=row["name"].strip(),
                        label=row["label"].strip(),
                        type=field_type,
                        group=row.get(
                            "group",
                            "Общие сведения",
                        ).strip(),

                        required=(
                                row.get(
                                    "required",
                                    "false",
                                ).strip().lower()
                                == "true"
                        ),

                        options=self._parse_options(
                            row.get(
                                "options",
                                ""
                            )
                        ),

                        placeholder=row.get(
                            "placeholder",
                            ""
                        ).strip(),

                        description=row.get(
                            "description",
                            ""
                        ).strip(),

                        unit=row.get(
                            "unit",
                            ""
                        ).strip(),
                    )
                    fields.append(field)

                if not fields:
                    print("❌ Не найдено полей в CSV")
                    return None

                print(f"✅ Загружено полей: {len(fields)}")

                fields.sort(
                    key=lambda field: field.order
                )
                return fields

        except Exception as e:
            print(f"❌ Ошибка парсинга CSV: {e}")
            return None

    def _detect_delimiter(self, sample):
        """Определяет разделитель CSV"""
        if ';' in sample and ',' not in sample:
            return ';'
        if '\t' in sample and (',' not in sample and ';' not in sample):
            return '\t'
        return ','

    def _parse_options(
            self,
            options_str: str,
    ) -> tuple[str, ...]:
        """Парсит варианты для Dropdown."""

        if not options_str:
            return ()

        for separator in ("\t", ";", ",", "|"):
            if separator in options_str:
                return tuple(
                    option.strip()
                    for option in options_str.split(separator)
                    if option.strip()
                )

        return (options_str.strip(),)