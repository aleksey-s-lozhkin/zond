"""Пример заполнения проверки КИП кранового узла и формирования протокола.

Демонстрирует использование сервисного слоя без графического интерфейса:
загрузка шаблона → создание проверки → заполнение → сохранение → PDF.

Запуск (из корня проекта):

    python tools/make_kip_demo.py [каталог_вывода]

По умолчанию результат складывается в ``reports/`` проекта. Этим же скриптом
обновляются образцы в ``docs/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zond.models.field import FieldType  # noqa: E402
from zond.services.inspection_factory import InspectionFactory  # noqa: E402
from zond.services.json_storage import JsonStorage  # noqa: E402
from zond.services.report_generator import ReportGenerator  # noqa: E402
from zond.services.template_loader import TemplateLoader  # noqa: E402
from zond.utils.logging_setup import configure_logging  # noqa: E402

TEMPLATE = PROJECT_ROOT / "templates" / "kip_kranovyy_uzel_mg.csv"

OBJECT = "ПАО «Газпром», ООО «Газпром трансгаз Самара», ЛПУМГ №2"
EXECUTOR = "Иванов И.И., инженер КИПиА"

#: Ответы, которые отличаются от типового значения для своего типа поля.
ANSWERS: dict[str, str] = {
    "object_name": OBJECT,
    "pipeline": "МГ «Уренгой — Помары — Ужгород», DN 1400, Ру 7,4 МПа",
    "crane_unit_no": "КУ-14",
    "km_axis": "142 км + 350 м",
    "crane_type": "Шаровой",
    "crane_dn": "1400",
    "crane_pn": "7,4",
    "work_pressure": "5,4",
    "inspection_date": "2026-09-26",
    "inspection_time": "09:30",
    "inspection_type": "ТО-2",
    "executor": EXECUTOR,
    "outdoor_temp": "12",
    "weather": "Ясно, ветер 3 м/с, видимость полная",
    "kip_system": "Микропроцессорная",
    "explosion_zone": "В-Iа",
    "regulatory_basis": "ФНП № 534 и № 536, ВРД 39-1.10-006-2000, ГОСТ IEC 60079-17-2011",
    "verification_expiry": "2027-04-15",
    "calibration_interval": "12",
    "journal_last_date": "2026-08-20",
    "sensors_total": "8",
    "sensor_pressure_list": (
        "PT-1401 — Метран-150, зав. № 114502, диапазон 0–10 МПа\n"
        "PT-1402 — Метран-150, зав. № 114518, диапазон 0–10 МПа"
    ),
    "sensor_ex_value": "Ex ia IIC T4 Ga",
    "sensor_check_date": "2026-03-12",
    "sensor_deviation": "0,4",
    "manometers_total": "6",
    "manometer_control_date": "2026-08-20",
    "manometer_control_device": "МП4-У, зав. № 4471, класс 0,4",
    "manometer_list": (
        "МП4-У зав. № 2211 — 0–10 МПа, класс 1,5\nМП4-У зав. № 2212 — 0–16 МПа, класс 1,5"
    ),
    "impulse_leak_method": "Обмыливание",
    "impulse_test_pressure": "5,4",
    "jb_total": "4",
    "cables_total": "12",
    "cable_insulation_value": "20",
    "cable_test_voltage": "1000",
    "grounding_value": "3,8",
    "grounding_measure_date": "2026-05-14",
    "func_setpoint_values": (
        "Ргаз min 4,9 МПа — сработала сигнализация\nРгаз max 6,2 МПа — сработала защита"
    ),
    "valve_time_value": "45",
    "func_failures": "Отказов и ошибок связи за межпроверочный период не зафиксировано",
    "func_result": "Работоспособно с замечаниями",
    "condition_assessment": "Ограниченно работоспособно",
    "operation_permission": "Допускается с ограничениями",
    "repair_required": "Да",
    "repair_deadline": "2026-10-26",
    "next_check_date": "2026-12-26",
    "approver": "Петров П.П., главный инженер ЛПУМГ №2",
    "work_performed": (
        "Продувка импульсных линий, подтяжка клеммных соединений "
        "в коробках К1 и К3, чистка контактов"
    ),
    "notes": "Работы выполнялись по наряду-допуску № 214 от 26.09.2026",
    "defects_found": (
        "1. В соединительной коробке К3 обнаружен конденсат и следы "
        "увлажнения клеммной колодки.\n"
        "2. Отсутствует маркировка кабельной линии КЛ-7 на конце "
        "со стороны датчика PT-1402."
    ),
    "defects_critical": "Дефектов, требующих немедленного устранения, не выявлено.",
    "recommendation": (
        "Заменить уплотнение крышки коробки К3, восстановить маркировку КЛ-7, "
        "повторно проверить сопротивление изоляции после устранения замечаний."
    ),
}

#: Выявленные несоответствия — показывают, как протокол отображает дефекты.
NON_CONFORMANCES: dict[str, str] = {
    "jb_moisture": "Не соответствует",
    "cable_marking": "Не соответствует",
}


def fill(inspection) -> None:
    """Заполнить проверку правдоподобными ответами."""

    for item in inspection.items:
        field = item.field
        name = field.name

        if name in ANSWERS:
            value = ANSWERS[name]
        elif field.type is FieldType.DATE:
            value = "2026-09-26"
        elif field.type is FieldType.TIME:
            value = "09:30"
        elif field.type is FieldType.NUMBER:
            value = "1"
        elif field.type is FieldType.TEXTAREA:
            value = "Замечаний нет"
        elif field.type is FieldType.DROPDOWN:
            value = "Соответствует" if "Соответствует" in field.options else field.options[0]
        else:
            value = "—"

        inspection.set_value(name, value)

    for name, value in NON_CONFORMANCES.items():
        inspection.set_value(name, value)


def main() -> None:
    configure_logging("WARNING")

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "reports"
    store = JsonStorage(target)

    template = TemplateLoader().load(TEMPLATE)
    inspection = InspectionFactory.create(template, OBJECT, EXECUTOR)

    fill(inspection)

    print(f"Шаблон: {template.name} — {len(template.fields)} полей, {template.total_groups} групп")
    print(f"Заполнено: {inspection.answered_count}/{inspection.total_items}")
    print(f"Незаполненных обязательных: {len(inspection.missing_required)}")

    if inspection.missing_required:
        for item in inspection.missing_required:
            print(f"  · {item.field.title} ({item.field.group})")
        raise SystemExit("В примере остались незаполненные обязательные поля")

    inspection.mark_finished()

    json_path = store.finalize(inspection)
    pdf_path = ReportGenerator().generate(inspection, store.pdf_path(inspection))

    print(f"JSON: {json_path}")
    print(f"PDF : {pdf_path}")


if __name__ == "__main__":
    main()
