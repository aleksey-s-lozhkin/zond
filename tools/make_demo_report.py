"""Пример заполнения проверки и формирования протокола.

Демонстрирует использование сервисного слоя без графического интерфейса:
загрузка шаблона → создание проверки → заполнение → сохранение → PDF.

Запуск (из корня проекта):

    python tools/make_demo_report.py                   # все шаблоны из templates/
    python tools/make_demo_report.py --out /tmp/demo
    python tools/make_demo_report.py templates/elektroustanovki.csv

Этим же скриптом обновляются образцы протоколов в docs/.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:  # pragma: no cover - зависит от запуска
    sys.path.insert(0, str(PROJECT_ROOT))

from zond.models.field import FieldType  # noqa: E402
from zond.models.inspection import Inspection  # noqa: E402
from zond.services.inspection_factory import InspectionFactory  # noqa: E402
from zond.services.json_storage import JsonStorage  # noqa: E402
from zond.services.report_generator import ReportGenerator  # noqa: E402
from zond.services.template_loader import TemplateLoader  # noqa: E402
from zond.utils.logging_setup import configure_logging  # noqa: E402

TEMPLATES_DIR = PROJECT_ROOT / "templates"

OBJECT = "ПАО «Газпром», ООО «Газпром трансгаз Самара», ЛПУМГ №2"
EXECUTOR = "Иванов И.И., инженер КИПиА"

#: Ответы для шаблона КИП кранового узла; для остальных шаблонов
#: используются значения по умолчанию (см. :func:`default_value`).
ANSWERS: dict[str, str] = {
    "object_name": OBJECT,
    "pipeline": "МГ «Уренгой — Помары — Ужгород», DN 1400, Ру 7,4 МПа",
    "crane_unit_no": "КУ-14",
    "km_axis": "142 км + 350 м",
    "crane_type": "Шаровой",
    "crane_dn": "1400",
    "crane_pn": "7,4",
    "work_pressure": "5,4",
    "inspection_type": "ТО-2",
    "executor": EXECUTOR,
    "outdoor_temp": "12",
    "weather": "Ясно, ветер 3 м/с, видимость полная",
    "kip_system": "Микропроцессорная",
    "explosion_zone": "В-Iа",
    "regulatory_basis": "ФНП № 534 и № 536, ВРД 39-1.10-006-2000, ГОСТ IEC 60079-17-2011",
    "installation_name": "Крановый узел №14, шкаф КИПиА",
    "voltage_class": "До 1000 В",
    "supply_system": "TN-S",
    "network_type": "Трёхфазная",
    "location_conditions": "На открытом воздухе",
    "hazard_level": "Средний уровень опасности",
    "security_type": "Частная охранная организация",
    "grounding_value": "3,8",
    "grounding_test_date": "2026-05-14",
    "insulation_test_date": "2026-05-14",
    "insulation_value": "20",
    "test_voltage": "1000",
    "loop_value": "0,4",
    "loop_test_date": "2026-05-14",
    "lightning_value": "8",
    "voltage_absence_check": "Выполнено",
    "sensors_total": "8",
    "sensor_ex_value": "Ex ia IIC T4 Ga",
    "sensor_deviation": "0,4",
    "manometers_total": "6",
    "manometer_control_device": "МП4-У, зав. № 4471, класс 0,4",
    "impulse_test_pressure": "5,4",
    "tubing_test_pressure": "5,4",
    "jb_total": "4",
    "cables_total": "12",
    "alarm_zones": "12",
    "cctv_cameras": "16",
    "acs_log_depth": "90",
    "cctv_archive_depth": "30",
    "battery_voltage": "13,2",
    "backup_runtime": "24",
    "panels_count": "4",
    "motors_count": "3",
    "motor_insulation": "50",
    "func_result": "Работоспособно с замечаниями",
    "condition_assessment": "Ограниченно работоспособно",
    "operation_permission": "Допускается с ограничениями",
    "repair_deadline": "2026-10-26",
    "approver": "Петров П.П., главный инженер ЛПУМГ №2",
    "notes": "Работы выполнялись по наряду-допуску № 214 от 26.09.2026",
    # --- Автомобиль УАЗ Патриот
    "vehicle_model": "УАЗ Патриот, 2019 год выпуска",
    "state_number": "А123ВС 163",
    "vin": "XTT316300K1234567",
    "inspector": "Инженер по безопасности движения Смирнов А.В.",
    "normative_base": "ТР ТС 018/2011, приложение 8, ГОСТ 33997-2016, ПДД РФ",
    "odometer": "74 250",
    "last_service_odometer": "70 000",
    "next_service_odometer": "85 000",
    "odometer_check": "Соответствует",
    "tire_pressure_value": "Передние 2,1 / задние 2,1 кгс/см²",
    "release_time": "07:40, механик Петров П.П.",
    "pre_trip_remarks": "Не выявлено",
    "corrosion_map": "Не обнаружено",
    "washer_volume": "4",
    "charging_voltage": "14,2",
    "co_value": "0,4",
    "tread_depth": "6,5",
    "pads_front": "9",
    "pads_rear": "8",
    "discs_thickness": "24",
    "brake_specific_force": "0,58",
    "windshield_light": "78",
}

#: Точечные несоответствия для шаблона КИП: показывают, как протокол
#: отображает выявленные дефекты.
NON_CONFORMANCES: dict[str, str] = {
    "jb_moisture": "Не соответствует",
    "cable_marking": "Не соответствует",
}

DEFECTS_TEXT: dict[str, str] = {
    "defects_found": (
        "1. В соединительной коробке К3 обнаружен конденсат и следы "
        "увлажнения клеммной колодки.\n"
        "2. Отсутствует маркировка кабельной линии КЛ-7 на конце "
        "со стороны датчика PT-1402."
    ),
    "defects_critical": "Дефектов, требующих немедленного устранения, не выявлено.",
    "work_performed": (
        "Продувка импульсных линий, подтяжка клеммных соединений "
        "в коробках К1 и К3, чистка контактов"
    ),
    "recommendation": (
        "Заменить уплотнение крышки коробки К3, восстановить маркировку КЛ-7, "
        "повторно проверить сопротивление изоляции после устранения замечаний."
    ),
}


def default_value(field) -> object:
    """Правдоподобное значение по типу поля."""

    if field.type is FieldType.CHECKBOX:
        return True

    if field.type is FieldType.DROPDOWN:
        return "Соответствует" if "Соответствует" in field.options else field.options[0]

    if field.type is FieldType.NUMBER:
        return "1"

    if field.type is FieldType.DATE:
        return date.today().isoformat()

    if field.type is FieldType.TIME:
        return "09:30"

    if field.type is FieldType.TEXTAREA:
        return "Замечаний нет"

    return "—"


def fill(inspection: Inspection, today: str) -> None:
    """Заполнить проверку: сначала ответы по умолчанию, затем уточнения."""

    for item in inspection.items:
        name = item.field.name
        value = ANSWERS.get(name, DEFECTS_TEXT.get(name, default_value(item.field)))

        if name in ("inspection_date", "next_check_date"):
            value = today
        elif name == "inspection_time":
            value = "09:30"

        inspection.set_value(name, value)

    for name, value in NON_CONFORMANCES.items():
        if inspection.get_item(name) is not None:
            inspection.set_value(name, value)

    _ensure_non_conformances(inspection)


def _ensure_non_conformances(inspection: Inspection) -> None:
    """Отметить пару несоответствий, чтобы в протоколе была цветовая разметка."""

    if inspection.problems:
        return

    marked = 0

    for item in inspection.items:
        if marked >= 2:
            break

        if item.field.type is FieldType.DROPDOWN and "Не соответствует" in item.field.options:
            inspection.set_value(item.field.name, "Не соответствует")
            marked += 1


def build_demo(template_path: Path, out_dir: Path) -> tuple[Path, Path]:
    """Собрать демонстрационную проверку и протокол для одного шаблона."""

    store = JsonStorage(out_dir)
    template = TemplateLoader().load(template_path)
    inspection = InspectionFactory.create(template, OBJECT, EXECUTOR)

    today = date.today().isoformat()
    fill(inspection, today)

    missing = inspection.missing_required

    if missing:
        titles = ", ".join(item.field.title for item in missing[:5])
        raise SystemExit(f"{template_path.name}: не заполнены обязательные поля: {titles}")

    inspection.set_value("next_check_date", (date.today() + timedelta(days=90)).isoformat())
    inspection.mark_finished()

    json_path = store.finalize(inspection)
    pdf_path = ReportGenerator().generate(inspection, store.pdf_path(inspection))

    print(f"{template_path.name}: {len(template.fields)} полей, {template.total_groups} групп")
    print(f"   заполнено {inspection.answered_count}/{inspection.total_items}")
    print(
        f"   соответствий {len(inspection.conformities)}, несоответствий {len(inspection.problems)}"
    )
    print(f"   JSON: {json_path.name}")
    print(f"   PDF : {pdf_path}")

    return json_path, pdf_path


def main() -> None:
    configure_logging("WARNING")

    parser = argparse.ArgumentParser(description="Пример заполнения проверки и протокол")
    parser.add_argument(
        "templates",
        nargs="*",
        type=Path,
        help="CSV-шаблоны; по умолчанию все из каталога templates/",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "reports",
        help="каталог для сохранения результатов",
    )

    args = parser.parse_args()

    templates = args.templates or sorted(TEMPLATES_DIR.glob("*.csv"))

    for template_path in templates:
        build_demo(template_path, args.out)
        print()


if __name__ == "__main__":
    main()
