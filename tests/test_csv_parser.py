"""Тесты разбора CSV-шаблонов."""

from __future__ import annotations

from pathlib import Path

import pytest

from zond.models.field import FieldType
from zond.services.csv_parser import CSVParser
from zond.services.errors import TemplateParseError
from zond.services.template_loader import TemplateLoader


def write(path: Path, text: str, encoding: str = "utf-8") -> Path:
    path.write_text(text, encoding=encoding)
    return path


def make_csv(tmp_path: Path, rows: str, header: str | None = None) -> Path:
    header = header or "order,name,label,type,group,required,options,placeholder,description,unit"
    return write(tmp_path / "template.csv", f"{header}\n{rows}\n")


# ------------------------------------------------------------------ успешный разбор


def test_sample_template_parsed(sample_template: Path) -> None:
    template = TemplateLoader().load(sample_template)

    assert len(template.fields) == 12
    assert template.groups == [
        "Общие сведения",
        "Паспортные данные",
        "Результаты осмотра",
        "Заключение",
    ]
    assert template.warnings == []
    assert len(template.required_fields) == 5

    by_name = {field.name: field for field in template.fields}

    assert by_name["inspection_date"].type is FieldType.DATE
    assert by_name["temperature"].unit == "°C"
    assert by_name["equipment_type"].options == (
        "Насос",
        "Компрессор",
        "Вентилятор",
        "Трансформатор",
        "Электродвигатель",
    )
    assert by_name["comments"].type is FieldType.TEXTAREA


def test_fields_sorted_by_order(tmp_path: Path) -> None:
    path = make_csv(
        tmp_path,
        "30,c,Третье,text,G2,false\n10,a,Первое,text,G1,false\n20,b,Второе,text,G1,false",
    )

    names = [field.name for field in TemplateLoader().load(path).fields]

    assert names == ["a", "b", "c"]


def test_utf8_bom_is_handled(tmp_path: Path) -> None:
    path = write(
        tmp_path / "bom.csv",
        "\ufefforder,name,label,type\n1,a,Поле,text\n",
    )

    assert TemplateLoader().load(path).fields[0].name == "a"


def test_cp1251_file_is_decoded(tmp_path: Path) -> None:
    path = write(
        tmp_path / "cp1251.csv",
        "order,name,label,type\n1,obj,Номер объекта,text\n",
        encoding="cp1251",
    )

    assert TemplateLoader().load(path).fields[0].label == "Номер объекта"


def test_semicolon_delimiter_with_commas_inside_values(tmp_path: Path) -> None:
    """Запятые внутри значений не должны ломать определение разделителя."""

    path = write(
        tmp_path / "semi.csv",
        "order;name;label;type;description\n"
        "1;obj;Номер объекта;text;Уникальный идентификатор, обязателен\n",
    )

    field = TemplateLoader().load(path).fields[0]

    assert field.type is FieldType.TEXT
    assert field.description == "Уникальный идентификатор, обязателен"


def test_tab_delimiter(tmp_path: Path) -> None:
    path = write(
        tmp_path / "tab.csv",
        "order\tname\tlabel\ttype\n1\ta\tПоле\ttext\n",
    )

    assert TemplateLoader().load(path).fields[0].name == "a"


def test_empty_rows_are_skipped(tmp_path: Path) -> None:
    path = write(
        tmp_path / "blank.csv",
        "order,name,label,type\n1,a,Поле,text\n\n,,\n2,b,Второе,text\n",
    )

    assert [field.name for field in TemplateLoader().load(path).fields] == ["a", "b"]


# -------------------------------------------------------------- восстанавливаемое


def test_short_row_is_tolerated(tmp_path: Path) -> None:
    path = make_csv(tmp_path, "1,a,Поле,text,G1\n2,b,Второе,text")

    template = TemplateLoader().load(path)

    assert len(template.fields) == 2
    assert template.fields[1].group == "Общие сведения"


def test_empty_order_falls_back_to_row_position(tmp_path: Path) -> None:
    path = make_csv(tmp_path, ",a,Поле,text,G1,false")

    template = TemplateLoader().load(path)

    assert template.fields[0].order > 0
    assert any("order" in warning for warning in template.warnings)


def test_unknown_type_falls_back_to_text(tmp_path: Path) -> None:
    path = make_csv(tmp_path, "1,a,Поле,banana,G1,false")

    template = TemplateLoader().load(path)

    assert template.fields[0].type is FieldType.TEXT
    assert any("banana" in warning for warning in template.warnings)


def test_uppercase_headers_are_normalized(tmp_path: Path) -> None:
    path = write(tmp_path / "upper.csv", "Order,Name,Label,Type\n1,a,Поле,text\n")

    template = TemplateLoader().load(path)

    assert template.fields[0].name == "a"
    assert template.fields[0].type is FieldType.TEXT


def test_missing_optional_value_is_tolerated(tmp_path: Path) -> None:
    path = write(tmp_path / "short.csv", "name,label,type\nx,Поле\n")

    assert TemplateLoader().load(path).fields[0].type is FieldType.TEXT


def test_empty_label_falls_back_to_name(tmp_path: Path) -> None:
    path = make_csv(tmp_path, "1,a,,text,G1,false")

    template = TemplateLoader().load(path)

    assert template.fields[0].label == "a"
    assert any("подпись" in warning for warning in template.warnings)


def test_unknown_columns_are_reported(tmp_path: Path) -> None:
    path = write(
        tmp_path / "extra.csv",
        "order,name,label,type,secret\n1,a,Поле,text,xxx\n",
    )

    template = TemplateLoader().load(path)

    assert any("secret" in warning for warning in template.warnings)


@pytest.mark.parametrize(
    "raw,expected",
    [("true", True), ("TRUE", True), ("да", True), ("1", True), ("", False), ("нет", False)],
)
def test_required_flag_parsing(tmp_path: Path, raw: str, expected: bool) -> None:
    path = make_csv(tmp_path, f"1,a,Поле,text,G1,{raw}")

    assert TemplateLoader().load(path).fields[0].required is expected


def test_options_split_by_pipe(tmp_path: Path) -> None:
    path = make_csv(tmp_path, "1,a,Поле,dropdown,G1,false,Один|Два|Три")

    assert TemplateLoader().load(path).fields[0].options == ("Один", "Два", "Три")


# ------------------------------------------------------------------- ошибки


def test_missing_required_column(tmp_path: Path) -> None:
    path = write(tmp_path / "nocols.csv", "label,type\nПоле,text\n")

    with pytest.raises(TemplateParseError) as error:
        TemplateLoader().load(path)

    assert "обязательных колонок" in str(error.value)
    assert any(problem.column == "name" for problem in error.value.problems)


def test_empty_file(tmp_path: Path) -> None:
    path = write(tmp_path / "empty.csv", "")

    with pytest.raises(TemplateParseError, match="пуст"):
        TemplateLoader().load(path)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(TemplateParseError, match="не найден"):
        TemplateLoader().load(tmp_path / "nope.csv")


def test_empty_field_name_is_reported_with_row(tmp_path: Path) -> None:
    path = make_csv(tmp_path, "1,,Поле,text,G1,false")

    with pytest.raises(TemplateParseError) as error:
        TemplateLoader().load(path)

    problem = error.value.problems[0]
    assert problem.row == 2
    assert problem.column == "name"


def test_duplicate_names_are_rejected(tmp_path: Path) -> None:
    path = make_csv(
        tmp_path,
        "1,dup,Первое,text,G1,false\n2,dup,Второе,text,G1,false",
    )

    with pytest.raises(TemplateParseError) as error:
        TemplateLoader().load(path)

    assert "уже описано" in error.value.user_message()


def test_dropdown_without_options_is_rejected(tmp_path: Path) -> None:
    path = make_csv(tmp_path, "1,sel,Выбор,dropdown,G1,false,")

    with pytest.raises(TemplateParseError) as error:
        TemplateLoader().load(path)

    assert error.value.problems[0].column == "options"


def test_all_problems_are_collected_at_once(tmp_path: Path) -> None:
    path = make_csv(
        tmp_path,
        "1,,Пусто,text,G1,false\n2,dup,Первое,text,G1,false\n"
        "3,dup,Второе,text,G1,false\n4,sel,Выбор,dropdown,G1,false,",
    )

    with pytest.raises(TemplateParseError) as error:
        TemplateLoader().load(path)

    assert len(error.value.problems) == 3
    assert error.value.user_message().count("•") == 3


def test_parser_result_type(sample_template: Path) -> None:
    result = CSVParser().parse_template(sample_template)

    assert result.fields
    assert result.warnings == []
