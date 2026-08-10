import csv
import os

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
            if not os.path.exists(file_path):
                print(f"❌ Файл не найден: {file_path}")
                return None

            encoding = self.detect_encoding(file_path)
            print(f"🔍 Определена кодировка: {encoding}")

            with open(file_path, 'r', encoding=encoding) as f:
                # Определяем разделитель
                sample = f.read(1024)
                f.seek(0)
                delimiter = self._detect_delimiter(sample)
                print(f"🔍 Определен разделитель: '{delimiter}'")

                reader = csv.DictReader(f, delimiter=delimiter)
                fields = []

                if not reader.fieldnames:
                    print("❌ Не удалось прочитать заголовки CSV")
                    return None

                print(f"📋 Найденные колонки: {reader.fieldnames}")

                for row in reader:
                    field_name = self._get_field_value(row, ['Поле', 'Field', 'Название', 'Name'])
                    if not field_name:
                        continue

                    field_type = self._get_field_value(
                        row,
                        ['Тип', 'Type'],
                        'text'
                    ).strip().lower()

                    try:
                        field_type = FieldType(field_type)
                    except ValueError:
                        field_type = FieldType.TEXT

                    field = Field(
                        name=field_name.strip(),

                        label=self._get_field_value(
                            row,
                            ['Название', 'Label', 'Поле', 'Field'],
                            field_name
                        ),

                        type=field_type,

                        required=self._get_field_value(
                            row,
                            ['Обязательное', 'Required'],
                            'false'
                        ).strip().lower() == 'true',

                        options=self._parse_options(
                            self._get_field_value(
                                row,
                                ['Варианты', 'Options'],
                                ''
                            )
                        ),

                        placeholder=self._get_field_value(
                            row,
                            ['Подсказка', 'Hint'],
                            ''
                        ),

                        group=self._get_field_value(
                            row,
                            ['Группа', 'Group'],
                            'Общие'
                        ),

                        description=self._get_field_value(
                            row,
                            ['Описание', 'Description'],
                            ''
                        ),

                        unit=self._get_field_value(
                            row,
                            ['Ед.измерения', 'Unit'],
                            ''
                        ),
                    )
                    fields.append(field)

                if not fields:
                    print("❌ Не найдено полей в CSV")
                    return None

                print(f"✅ Загружено полей: {len(fields)}")
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

    def _get_field_value(self, row, possible_names, default=''):
        """Ищет значение поля по возможным названиям колонок"""
        for name in possible_names:
            if name in row:
                return row[name].strip()
        return default

    def _parse_options(self, options_str):
        """Парсит строку с вариантами для dropdown"""
        if not options_str:
            return []

        separators = ['\t', ';', ',', '|']
        for sep in separators:
            if sep in options_str:
                return [opt.strip() for opt in options_str.split(sep) if opt.strip()]

        return [options_str.strip()]