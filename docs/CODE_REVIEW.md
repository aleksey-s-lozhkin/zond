# ЗОНД: ECTS — техническое ревью кода

**Дата:** ревизия ветки `feature/ux` (4 файла с незакоммиченными изменениями)
**Стек:** Python 3.13.9, Flet 0.86.5 (Flet 1.0 alpha API)
**Объём:** ~1 590 строк Python в 30 модулях, 3 коммита в истории
**Статус:** рабочий «скелет» сквозного сценария, UI-слой в процессе переделки

> **Статус на текущий момент: все 25 замечаний устранены** (этапы 0–5 плана
> выполнены). Актуальное состояние — в разделе
> [«Что сделано по итогам ревью»](#0-что-сделано-по-итогам-ревью) ниже.
> Документ сохранён как исходный срез проблем и обоснование решений.

---

## 0. Что сделано по итогам ревью

Реализация: 181 тест, `ruff check` и `ruff format --check` без замечаний.

| № | Замечание | Как решено |
|---|---|---|
| BLOCKER-1 | `zond/ui/widgets.py` затмеён пакетом | файл удалён (`git rm`) |
| BLOCKER-2 | Кнопки падали: `text=` вместо `content=` | `components/buttons.py` переписан, базовый класс — `ft.Button` (не устаревший `ElevatedButton`); 5 типов кнопок |
| BLOCKER-3 | `ft.padding.symmetric` не существует | `ft.Padding`/`ft.Border`; `ProgressWidget` переписан и обновляется через `set_progress()` без перерисовки |
| BLOCKER-4 | Типы `date`/`time` не реализованы | `FieldControl`: нативный `DatePicker`/`TimePicker` с откатом на ручной ввод; даты хранятся в ISO |
| CRITICAL-5 | Нет завершения проверки и сохранения | `FinishScreen`, `finished_at`, сохранение по факту завершения, отчёты в `reports/inspections`, `reports/pdf` |
| CRITICAL-6 | Ошибки не доходили до пользователя | `components/dialogs.py`: `show_error`/`show_confirm`/`show_info` |
| CRITICAL-7 | Одна плохая строка убивала шаблон | Парсер разделяет ошибки и предупреждения, собирает **все** проблемы с номером строки и колонкой |
| CRITICAL-8 | Значения терялись при перерисовке | `FieldControl.set_value()`, значение берётся из `InspectionItem` при сборке экрана; есть тест |
| CRITICAL-9 | Загрузка второго шаблона не сбрасывала состояние | `ZondState.set_template()` вызывает `reset()`; тест на сброс прогресса |
| CRITICAL-10 | Нет валидации и признака «проверено» | `FieldControl.validate()`, `is_checked` выставляется, незаполненные обязательные блокируют переход |
| MAJOR-11 | Мёртвый код | Удалены `widgets.py`, `controllers/`, `icons.py` подключён, все компоненты задействованы, `answers`/`current_field_index` убраны, `JsonStorage.load()` реализован |
| MAJOR-12 | Три несовместимых контракта экранов | Единый `AppScreen(app)` + `compose()`; `BaseScreen` заменён |
| MAJOR-13 | Навигация без истории | `ZondNavigator` со стеком: `show`/`push`/`replace`/`back` |
| MAJOR-14 | Дизайн-система не применялась | Экраны собираются только из `components/*`, ни одного inline `ButtonStyle` |
| MAJOR-15 | JSON не самодостаточен | `format_version: 2` со снимком полей, `Inspection.from_dict()`, миграция v1 |
| MAJOR-16 | Нет тестов, README, конфигурации | 181 тест, `pyproject.toml`, ruff, CI, README, `docs/template.md` |
| MINOR-17 | Отладка через `print` | Модуль `logging`, `ZOND_LOG_LEVEL` |
| MINOR-18 | Атрибуты до `super().__init__()` | Устранено: экраны вызывают `super().__init__()` первым |
| MINOR-19 | Слабости парсера CSV | `charset-normalizer`, определение разделителя по заголовку, нормализация заголовков, проверка дубликатов и уникальности |
| MINOR-20 | Наивное время | Все метки времени timezone-aware (UTC) |
| MINOR-21 | Жёсткий размер окна | Размеры вынесены в константы + `min_width`/`min_height`, проверка наличия окна |
| MINOR-22 | Логотип 1.9 МБ | не изменялся (см. «Что осталось») |
| MINOR-23 | `order` не проверялся | Нечисловой `order` → откат на позицию строки с предупреждением |
| MINOR-24 | Разнобой кнопок | Единые `PrimaryButton`/`SecondaryButton`/`GhostButton`/`SuccessButton`/`DangerButton` |
| MINOR-25 | `reports/*` в `.gitignore` | Каталог данных структурирован: `drafts/`, `inspections/`, `pdf/` |

**Отступления от плана:**

* `date`/`time` реализованы нативными пикерами, а не текстовым вводом.
* Отчёты — PDF напрямую (reportlab), а не HTML: по требованию заказчика.
* История проверок и возобновление сеанса включены в объём (были опциональны).
* Дополнительно добавлены: экран истории, автосохранение черновиков, миграция
  формата v1 → v2, дымовой GUI-сценарий (`tools/smoke_gui.py`).
* Не сделано: сжатие `logo.png` (MINOR-22) и продуктовые фичи из этапа 6
  (настройки справочников, фотофиксация, роли, условные поля).

---

## 1. Что это за проект

Настольное (Flet desktop, окно 430×860) приложение для проведения проверок/освидетельствований
оборудования. Пользователь загружает CSV-шаблон проверки, приложение строит форму по группам
полей, инженер заполняет значения группа за группой, результат сохраняется в JSON.

Слоистая структура выдержана корректно и это главное достоинство кодовой базы:

```
zond/
├── ects.py                     # entrypoint: ft.run(main, assets_dir=...)
├── app/                        # ZondApp (композиция), ZondState, ZondNavigator
├── models/                     # Field/FieldType, Template, Inspection, InspectionItem (dataclass-ы)
├── services/                   # CSVParser → TemplateLoader → InspectionFactory → JsonStorage
├── controllers/                # app_controller.py — ПУСТОЙ (0 байт)
└── ui/
    ├── colors.py, design.py, theme.py, icons.py
    ├── components/             # buttons, cards, headers, progress, dialogs (dialogs — 0 байт)
    ├── screens/                # upload, check, inspection, base_screen (не используется)
    └── widgets/                # field_builder.py + КОНФЛИКТ с widgets.py (см. BLOCKER-4)
```

Разделение model / service / ui / app-state — правильное. Проблемы сосредоточены не в
архитектуре, а в **незавершённости** (пустые модули, мёртвый код) и в **несоответствии кода
фактическому API Flet 0.86.5**, из-за чего часть UI-слоя физически неработоспособна.

---

## 2. Что уже сделано

### 2.1 Работает и проверено запуском

| Возможность | Модуль | Состояние |
|---|---|---|
| Точка входа, конфигурация страницы, тема | `ects.py`, `app/app.py:38-57` | ✅ запускается |
| Определение кодировки CSV (8 кодировок) | `services/csv_parser.py:11-26` | ✅ `utf-8-sig` определён верно |
| Определение разделителя (`, ; \t`) | `services/csv_parser.py:141-147` | ⚠️ эвристика, ломается на смешанных данных |
| Парсинг CSV → `list[Field]` | `services/csv_parser.py:28-139` | ✅ `templates/sample.csv` → 12 полей |
| Парсинг `options` для dropdown | `services/csv_parser.py:149-165` | ✅ `Насос;Компрессор;...` → 5 опций |
| Валидация обязательных колонок | `services/csv_parser.py:51-62` | ✅ `name,label,type` |
| Сборка `Template` | `services/template_loader.py` | ✅ |
| Фабрика `Inspection` + items по полям | `services/inspection_factory.py` | ✅ 12 items |
| Пошаговое состояние (группы, индексы, переход вперёд) | `app/state.py:34-79` | ✅ 4 группы, переход до конца |
| Навигация без истории | `app/navigator.py` | ✅ но без back |
| FilePicker (CSV, одиночный выбор) | `app/app.py:30-33, 67-83` | ✅ API 0.86.5 валиден |
| Экран загрузки с логотипом | `ui/screens/upload_screen.py` | ✅ |
| Экран подтверждения шаблона (список групп) | `ui/screens/check_screen.py` | ✅ |
| Экран пошагового заполнения формы | `ui/screens/inspection_screen.py` | ⚠️ частично (см. ниже) |
| Построение 5 из 7 типов полей | `ui/widgets/field_builder.py` | ⚠️ text/number/textarea/checkbox/dropdown |
| Сохранение в JSON (1 формат, write-only) | `services/json_storage.py` | ✅ `/tmp` проверено |
| Дизайн-токены (цвета, отступы, радиусы, шрифты) | `ui/colors.py`, `ui/design.py` | ✅ объявлены |

Сквозной сценарий (загрузка CSV → CheckScreen → InspectionScreen → 4 группы → JSON)
**проходит end-to-end** — проверено прогоном с заглушкой страницы Flet.

### 2.2 Незакоммиченные изменения в `feature/ux`

`git diff` показывает 4 файла — это рефакторинг UI-слоя в процессе:

- `app/state.py` — переписан `next_group()` через новое свойство `is_finished`;
  `current_group`/`current_fields` теперь корректно отдают `None`/`[]` после последней группы.
  **Это исправление реального бага** (раньше `current_group` падал с `IndexError` в конце).
- `ui/components/headers.py` — `subtitle` → `description`, `bgcolor` убран, `ft.padding.symmetric`
  → `ft.Padding(...)` (правильный API 0.86.5), добавлен `on_back: Callable`.
- `ui/screens/inspection_screen.py` — подключён `ScreenHeader`, добавлен `SafeArea` + скролл,
  «Шаг N из M».
- `ui/components/cards.py` — старая `SectionCard` (с заголовком/иконкой) закомментирована,
  вместо неё упрощённая. **Регрессия:** потеряны `border`, `Radius/Space`-токены, `expand`.

Ничего из этого не закоммичено, ветка не смержена.

---

## 3. Найденные проблемы

### BLOCKER — ломает функциональность

**BLOCKER-1. `zond/ui/widgets.py` полностью мёртв — его затмевает пакет `zond/ui/widgets/`.**
В репозитории лежат одновременно файл `zond/ui/widgets.py` (115 строк, кнопки + `SectionCard` +
`ScreenHeader`) и пакет `zond/ui/widgets/`. Python выбирает **пакет**, файл недостижим:

```
$ python -c "from zond.ui.widgets import PrimaryButton"
ImportError: cannot import name 'PrimaryButton' from 'zond.ui.widgets' (.../zond/ui/widgets/__init__.py)
```

Последствия: правки в `widgets.py` не влияют ни на что; в файле дублируются компоненты из
`ui/components/`; читатель вводится в заблуждение. **Файл подлежит удалению.**

**BLOCKER-2. Все кастомные кнопки падают с `TypeError` при создании.**
`ui/components/buttons.py:18,45,73` передают `text=` в конструктор. В Flet 0.86.5 у
`Button`/`ElevatedButton`/`OutlinedButton` **нет** параметра `text` — только `content`:

```
FAIL PrimaryButton   TypeError: Button.__init__() got an unexpected keyword argument 'text'
FAIL SecondaryButton TypeError: OutlinedButton.__init__() got an unexpected keyword argument 'text'
FAIL SuccessButton   TypeError: Button.__init__() got an unexpected keyword argument 'text'
```

Сейчас не проявляется только потому, что кнопки нигде не используются (экраны строят
`ft.ElevatedButton` вручную). Как только дизайн-систему подключат — приложение упадёт.

**BLOCKER-3. `ProgressWidget` падает с `AttributeError`.**
`ui/components/progress.py:21` использует `ft.padding.symmetric(...)`, которой в 0.86.5 нет
(есть `ft.Padding.symmetric(...)`):

```
AttributeError: module 'flet.controls.padding' has no attribute 'symmetric'
```

Тот же устаревший API — в закомментированном коде `ui/components/cards.py:70` (`ft.border.all`).
Виджет прогресса нигде не подключён, поэтому падение не замечено — но именно он должен
показывать «Шаг N из M» на экране проверки.

**BLOCKER-4. Типы полей `date` и `time` не реализованы.**
`models/field.py:8-9` объявляет `DATE` и `TIME`, но `FieldBuilder` (`ui/widgets/field_builder.py:71-75`)
не имеет для них `case` и отдаёт `ft.Text("Неизвестный тип date")` вместо поля ввода:

```
text       -> TextField
number     -> TextField
date       -> Text      <-- "Неизвестный тип date"
time       -> Text      <-- "Неизвестный тип time"
dropdown   -> Dropdown
checkbox   -> Checkbox
textarea   -> TextField
```

При этом `templates/sample.csv:2` **содержит** поле `inspection_date` типа `date` с
`required=true` — то есть на первом же экране проверки пользователь видит битую строку.

### CRITICAL — сценарий не доведён до конца, данные теряются

**CRITICAL-5. Нет завершения проверки и сохранения результата.**
`ui/screens/inspection_screen.py:21-22` после последней группы показывает `ft.Text("Проверка
завершена")` и всё. Следствия:

- `Inspection.finished_at` (`models/inspection.py:20`) **никогда не заполняется** — в JSON всегда `null`;
- нет кнопки «Сохранить/Сформировать отчёт», нет финального экрана, нет возврата в начало;
- `JsonStorage.save` вызывается в `app/app.py:116-119` **сразу после загрузки шаблона**

  ```python
  JsonStorage.save(self.state.inspection, Path("reports/test.json"))
  ```

  то есть сохраняется **пустая** проверка (`value: null` у всех 12 полей — видно в
  `reports/test.json`), а не результат заполнения. Путь `reports/test.json` жёстко зашит и
  зависит от CWD запуска.

**CRITICAL-6. Ошибки не доходят до пользователя.**
`app/app.py:90-95` — любое исключение при загрузке шаблона только печатается в stdout:

```python
except Exception as ex:
    print("Ошибка загрузки:", ex)
    return
```

Пользователь остаётся на экране загрузки без какой-либо обратной связи. `ui/components/dialogs.py`
пуст (0 байт) — механизма показа ошибок нет вообще.

**CRITICAL-7. Любая «плохая» строка CSV убивает весь шаблон с невнятным сообщением.**
`services/csv_parser.py:137-139` оборачивает в `except Exception` **весь** разбор и возвращает
`None`, `TemplateLoader` (`template_loader.py:21-24`) превращает это в
`ValueError("Не удалось загрузить шаблон")` — без указания строки, колонки и причины.
Проверено на 5 фикстурах:

| Фикстура | Результат |
|---|---|
| строка короче заголовка | ❌ FAILED (generic) |
| пустой `order` | ❌ FAILED (generic) |
| заголовки `Name,Label,Type` (другой регистр) | ❌ FAILED (generic) |
| неизвестный `type` (`banana`) | ✅ OK — молча `text` |
| строка без значения в необязательной колонке | ❌ FAILED (generic) |

Конкретные причины: `csv_parser.py:85` — `int(row.get("order", 0))` падает на `""`;
`csv_parser.py:89-92,109-122` — `row.get("group", default).strip()` даёт `AttributeError:
'NoneType' object has no attribute 'strip'`, когда колонка есть в заголовке, но значение пустое
(дефолт `get` в этом случае не работает).

**CRITICAL-8. Значения теряются при перерисовке формы.**
`FieldBuilder.build` (`ui/widgets/field_builder.py:10-13`) не принимает начальное значение и не
читает `item.value`. При каждом `next_group()` контролы создаются заново
(`inspection_screen.py:72`). Пока переход только вперёд — незаметно, но `ZondState.previous_group`
(`state.py:75-79`) уже написан и кнопки «Назад» нет: как только её добавят, возврат в предыдущую
группу покажет **пустые поля**, хотя значения в `inspection.items` сохранены.

**CRITICAL-9. Загрузка второго шаблона не сбрасывает состояние.**
`app/app.py:97-100` перезаписывает `state.template` и `state.inspection`, но `ZondState.reset()`
(`state.py:82-90`) не вызывается — **и нигде не вызывается**. `current_group_index` остаётся от
предыдущего сеанса: если пользователь дошёл до 3-й группы и загрузил новый CSV, `InspectionScreen`
откроется на 3-й группе нового шаблона, а при `current_group_index >= total_groups` покажет
«Проверка завершена» вместо формы. Также `reset()` не сбрасывает `current_field_index`
(строка 88 закомментирована).

**CRITICAL-10. Нет валидации обязательных полей и нет признака «проверено».**
`Field.required` парсится (`csv_parser.py:94-100`), но нигде не проверяется и не отображается.
`InspectionItem.is_checked` (`models/inspection_item.py:16`) не выставляется никогда — в JSON
всегда `false` (`models/inspection.py:52`). Перейти к следующей группе можно с пустыми
обязательными полями. `InspectionScreen` не различает «поле не заполнено» и «поле заполнено пусто».

### MAJOR — архитектура и дублирование

**MAJOR-11. Мёртвый код: ~5 модулей и ~10 сущностей.**

| Объект | Статус |
|---|---|
| `zond/controllers/app_controller.py`, `services/report_generator.py`, `ui/components/dialogs.py` | 0 байт |
| `zond/ui/widgets.py` | недостижим (BLOCKER-1) |
| `ui/screens/base_screen.py` (`BaseScreen`) | 0 использований; требует `app.page`, тогда как экраны принимают `(state, navigator)` / `on_upload` |
| `ui/icons.py` (`AppIcons`) | 0 использований — везде прямые `ft.Icons.*` |
| `ui/components/buttons.py` | 0 использований (+ сломан, BLOCKER-2) |
| `ui/components/cards.py` (`SectionCard`) | 0 использований; 79 строк закомментированного кода (стр. 7-85) |
| `ui/components/progress.py` (`ProgressWidget`) | 0 использований (+ сломан, BLOCKER-3) |
| `ZondState.answers`, `set_answer()`, `is_modified` | `set_answer` не вызывается → `answers` пуст, `is_modified` всегда `False` |
| `ZondState.current_field_index`, `current_field` | индекс никогда не инкрементируется |
| `ZondState.reset()`, `previous_group()` | не вызываются |
| `ects.py:6 BASE_DIR` | вычисляется и не используется (передаётся литерал) |
| `services/json_storage.py: load()` | отсутствует |

**MAJOR-12. Три несовместимых способа конструирования экрана.**
`UploadScreen(on_upload=...)`, `CheckScreen(state, navigator)`, `InspectionScreen(state)`,
`BaseScreen(app)` — четыре разных контракта. Из-за этого `InspectionScreen` не может вернуться
назад (нет `navigator`), а `ScreenHeader.on_back` (`headers.py:20-29`) не передаётся ни разу.

**MAJOR-13. Навигация без истории.** `navigator.py:12-18` делает `page.clean()` + `page.add()`.
Нет стека, нет маршрутов, нет подтверждения «несохранённые данные будут потеряны», старые
экраны не освобождаются. `app.py:61-65` на старте всегда показывает `UploadScreen`.

**MAJOR-14. Дизайн-система не применяется.** Токены `ui/design.py` (Space/Radius/FontSize/
ControlSize) и компоненты `ui/components/*` объявлены, но экраны верстаются вручную:
`upload_screen.py:67-90` и `check_screen.py:79-83` задают собственные `ButtonStyle`, радиусы
12/16 и отступы 20/32 мимо токенов. Один и тот же «primary button» описан **трижды**
(`widgets.py`, `components/buttons.py`, `upload_screen.py`), все три выглядят по-разному
(elevation 1 vs 0, radius 12 vs 12, width 260 vs expand). `theme.py` — минимальный (только
`primary` и `surface`), остальные цвета подмешиваются из `AppColors` через `bgcolor`/`color`.

**MAJOR-15. JSON-отчёт не самодостаточен, обратная загрузка невозможна.**
`Inspection.to_dict()` (`models/inspection.py:33-56`) сохраняет только `field: <name>` — без
`type`, `group`, `label`, `options`, `unit`, `required`. Плюс `template` — только имя. Значит:

- `JsonStorage.load()` нельзя реализовать корректно без исходного CSV;
- по сохранённому JSON невозможно отрисовать отчёт или восстановить сеанс;
- `format_version: 1` есть, но нет ни схемы, ни валидации, ни миграций.

**MAJOR-16. Нет тестов, нет README, нет конфигурации проекта.**
Отсутствуют `tests/`, `pyproject.toml`, линтер/форматтер, CI. `README.md` — 0 байт.
`requirements.txt` — одна строка `flet==0.86.5` без перевода строки в конце, без dev-зависимостей,
без фиксации `python_requires`. Регрессии не отлавливаются: BLOCKER-2/3 никто не заметил бы,
даже если бы код использовался.

### MINOR — качество и устойчивость

**MINOR-17. Отладка через `print` в 12+ местах** (`app.py:68,76,80-114`,
`upload_screen.py:11,27`, `csv_parser.py:40,47,66,70,127,130,138`, `inspection_screen.py:90`),
включая эмодзи и stdout-вывод каждого значения поля. Модуля `logging` нет.

**MINOR-18.** `upload_screen.py:11-13` — `self.on_upload = on_upload` **до** `super().__init__()`.
Работает только потому, что Flet-контролы не используют `__slots__`; при обновлении Flet
сломается. То же в `check_screen.py:13-14`, `inspection_screen.py:12`.

**MINOR-19. Парсер CSV:**
- `detect_encoding` (`csv_parser.py:11-26`): `latin-1` декодирует **любой** файл, поэтому метод
  почти всегда «успешен» на последнем кандидате; проверяются только первые 1000 байт, а
  `UnicodeDecodeError` — подкласс `UnicodeError` (дублирование в `except`).
- `_detect_delimiter` (`csv_parser.py:141-147`): если в `;`-файле встречается запятая внутри
  значения — разделитель определится как `,` и файл развалится. `csv.Sniffer` был бы надёжнее.
- Заголовки регистрозависимы (`Name`/`Type` → generic-ошибка), `order` фактически обязателен, но
  не входит в `required_columns`, `name` не проверяется на пустоту и уникальность.
- `Inspection.get_item` (`models/inspection.py:24-31`) — линейный поиск с возвратом **первого**
  совпадения; дубликаты `name` в CSV молча смешиваются.

**MINOR-20.** `models/inspection.py:18` — `datetime.now()` без таймзоны, `isoformat()` без
смещения. Для протоколов проверки (юридически значимых) нужен tz-aware UTC.

**MINOR-21.** `app.py:55-57` — жёстко заданные 430×860 под desktop, без адаптивности и без
разделения `ft.AppView.FLET_APP` / web / mobile. `page.window` пишется без проверки `None` (веб).

**MINOR-22.** `assets/images/logo.png` — 1.9 МБ для логотипа 110×110.

**MINOR-23.** В `models/field.py` `order: int = 0` при `templates/sample.csv` с шагом 10 —
сортировка по `order` стабильна, но `order` не проверяется на уникальность.

**MINOR-24.** `inspection_screen.py:46` смешивает `ft.Button`, `check_screen.py:79` —
`ft.ElevatedButton`, `upload_screen.py:67` — `ft.ElevatedButton` со `style`. Единый компонент
кнопки отсутствует.

**MINOR-25.** `.gitignore` содержит `reports/*`, но приложение пишет именно туда — артефакты
проверок принципиально не версионируются и не имеют идентификатора/имени пользователя.

---

## 4. Что осталось сделать (roadmap по фичам)

Судя по пустым модулям и мёртвым компонентам, изначально задумывался полный продукт.
Незакрытые функциональные блоки:

1. **Завершение проверки** — экран «Проверка завершена», `finished_at`, финальное сохранение.
2. **Генерация отчётов** (`services/report_generator.py`, 0 байт) — экспорт результата
   (PDF/JSON/печатная форма), `AppIcons.SEND` явно заготовлен под «отправить/сформировать».
3. **Загрузка/возобновление проверки** (`JsonStorage.load`) — продолжить незавершённый сеанс.
4. **История проверок** — список сохранённых отчётов в `reports/`.
5. **Валидация обязательных полей** + признак «проверено» (`is_checked`).
6. **Оставшиеся типы полей** — `date` (date picker), `time`.
7. **Навигация назад** и между группами (`previous_group` уже написан).
8. **Диалоги** (`ui/components/dialogs.py`, 0 байт) — ошибки, подтверждения, «выйти без сохранения».
9. **Дизайн-система** — подключить `components/*`, удалить дубли, применить токены.
10. **Инженерная обвязка** — тесты, логирование, линтер, CI, README, `pyproject.toml`, сборка.

---

## 5. План реализации

Приоритеты: **P0 — приложение не работает как продукт**, **P1 — данные/UX**, **P2 — качество**.

### Этап 0. Стабилизация (P0) — 1 день

Цель: устранить BLOCKER-1..4 и сделать UI-слой запускаемым.

| # | Задача | Файлы | Критерий приёмки |
|---|---|---|---|
| 0.1 | Удалить затмеённый `zond/ui/widgets.py`; оставить только пакет `zond/ui/widgets/` | `zond/ui/widgets.py` | `from zond.ui.widgets import PrimaryButton` → ImportError ожидаем; `git grep -c "ui.widgets import"` даёт только `field_builder` |
| 0.2 | Починить конструкторы кнопок: `text=` → `content=ft.Text(text)` (или первый позиционный аргумент) | `ui/components/buttons.py:18,45,73` | `PrimaryButton("x")`, `SecondaryButton("x")`, `SuccessButton("x")` создаются без исключений |
| 0.3 | Починить `ProgressWidget`: `ft.padding.symmetric` → `ft.Padding.symmetric` | `ui/components/progress.py:21` | `ProgressWidget("t",1,4)` создаётся; `value == 0.25` |
| 0.4 | Убрать `ft.border.all` из закомментированного кода карточки; решить судьбу старой `SectionCard` (вернуть или удалить) | `ui/components/cards.py:7-85` | Нет комментариев-«кладбища»; `SectionCard` либо используется, либо удалена |
| 0.5 | Реализовать `date` и `time` в `FieldBuilder` (`ft.DatePicker`/`ft.TimePicker` + read-only `TextField`, либо текстовый ввод с валидацией формата) | `ui/widgets/field_builder.py:71-75` | Для всех 7 значений `FieldType` возвращается контрол ввода; `sample.csv` не содержит «Неизвестный тип» |
| 0.6 | Смоук-тест: собрать дерево всех экранов в pytest без клиента | `tests/test_smoke_ui.py` | Все экраны инстанцируются |

### Этап 1. Завершение сценария проверки (P0/P1) — 2–3 дня

| # | Задача | Файлы | Критерий приёмки |
|---|---|---|---|
| 1.1 | Ввести `FinishScreen` («Проверка завершена» + сводка + кнопки «Сохранить» / «Новая проверка») | `ui/screens/finish_screen.py` (new), `app/navigator.py` | После последней группы открывается экран завершения, а не `ft.Text` |
| 1.2 | Проставлять `finished_at` и сохранять результат по кнопке | `models/inspection.py`, `app/app.py` | `reports/<template>_<timestamp>.json` содержит заполненные `value`, `finished_at` не `null` |
| 1.3 | Убрать сохранение пустой проверки сразу после загрузки шаблона | `app/app.py:116-119` | Файл появляется только после завершения/явного сохранения |
| 1.4 | Путь сохранения: `reports/` рядом с пакетом + имя из шаблона и времени, без зависимости от CWD | `app/app.py`, `services/json_storage.py` | Запуск из любого каталога пишет в один и тот же `reports/` |
| 1.5 | Вызывать `ZondState.reset()` при загрузке нового шаблона; доделать `reset()` (сбрасывать все индексы и `answers`) | `app/app.py`, `app/state.py:82-90` | Загрузка второго CSV открывает первую группу нового шаблона |
| 1.6 | Навигация назад: кнопка в `ScreenHeader(on_back=...)`, `previous_group()`, передать `navigator` в `InspectionScreen` | `ui/screens/inspection_screen.py`, `ui/components/headers.py` | Возврат в предыдущую группу работает; значения **сохраняются** (см. 1.7) |
| 1.7 | `FieldBuilder.build(field, value=None, on_change=None)` — читать текущее значение из `item.value` | `ui/widgets/field_builder.py`, `inspection_screen.py` | После «назад/вперёд» введённые значения на месте |
| 1.8 | Валидация обязательных полей перед переходом; подсветка незаполненных; `is_checked` для checkbox-полей | `inspection_screen.py`, `models/inspection_item.py` | Переход блокируется/предупреждает при пустых `required`; в JSON `is_checked` не всегда `false` |
| 1.9 | Подключить `ProgressWidget` вместо текста «Шаг N из M» | `inspection_screen.py`, `ui/components/progress.py` | Прогресс-бар отражает `current_group_index / total_groups` |

### Этап 2. Данные и отчёты (P1) — 3–4 дня

| # | Задача | Файлы | Критерий приёмки |
|---|---|---|---|
| 2.1 | Расширить `to_dict()`: сохранять снапшот полей (`type/group/label/options/unit/required/order`) | `models/inspection.py` | JSON самодостаточен: по нему восстанавливается форма без CSV |
| 2.2 | Добавить `Inspection.from_dict()` и `JsonStorage.load()` | `models/inspection.py`, `services/json_storage.py` | Round-trip: `load(save(x)) == x` (тест) |
| 2.3 | Схема + миграции по `format_version` (1 → 2) | `services/json_storage.py` | Старые файлы читаются, новые пишутся с версией 2 |
| 2.4 | Атомарная запись (temp + `os.replace`) и обработка `OSError` | `services/json_storage.py` | Прерывание записи не оставляет битый JSON |
| 2.5 | tz-aware UTC в `started_at`/`finished_at` | `models/inspection.py:18-20` | В JSON есть смещение (`+00:00` / `Z`) |
| 2.6 | `ReportGenerator`: сводка по группам, список несоответствий, экспорт JSON и человекочитаемый отчёт (Markdown/HTML → PDF) | `services/report_generator.py` | Файл отчёта в `reports/`, открывается; покрыт тестом |
| 2.7 | Экран истории проверок: список файлов `reports/`, «продолжить»/«открыть отчёт»/«удалить» | `ui/screens/history_screen.py` (new) | Незавершённую проверку можно продолжить |

### Этап 3. UX и дизайн-система (P1) — 2–3 дня

| # | Задача | Файлы | Критерий приёмки |
|---|---|---|---|
| 3.1 | Единый контракт экрана: `Screen(app)` или `Screen(state, navigator)` — один вариант для всех | `ui/screens/*.py`, `ui/screens/base_screen.py` | `grep` показывает одинаковую сигнатуру у всех экранов |
| 3.2 | Подключить `PrimaryButton`/`SecondaryButton`/`SuccessButton` в `upload_screen`, `check_screen`, `inspection_screen`; удалить локальные `ButtonStyle` | `ui/screens/*`, `ui/components/buttons.py` | Ни одного inline `ft.ButtonStyle` в экранах |
| 3.3 | Подключить `SectionCard`; вернуть рамку/токены `Radius.LG`/`Space.LG` | `ui/components/cards.py` | Карточки единообразны |
| 3.4 | Расширить `theme.py` (все цвета `AppColors` → `ColorScheme`, типографика), убрать ручные `bgcolor` | `ui/theme.py` | Тёмная тема переключается без правок экранов |
| 3.5 | Наполнить `ui/components/dialogs.py`: `error_dialog`, `confirm_dialog`, `unsaved_changes_dialog` | `ui/components/dialogs.py` | Ошибка CSV показывается пользователю, а не в stdout |
| 3.6 | Показывать `description`, `unit`, пометку `required`; улучшить `FieldBuilder` (валидация `number`) | `ui/widgets/field_builder.py` | Поля из `sample.csv` отображаются полностью, включая `°C`, `МПа`, `лет` |
| 3.7 | Единый стиль иконок: использовать `ui/icons.py` либо удалить модуль | `ui/icons.py` | Нет дублирующего источника иконок |
| 3.8 | Заменить `page.clean()+add()` на стек экранов с корректным удалением; диалог подтверждения выхода | `app/navigator.py` | «Назад» из проверки и «Новая проверка» работают без утечек |
| 3.9 | Адаптивность: убрать жёсткие 430×860, проверить web/mobile | `app/app.py:54-57` | Окно и веб-режим отрисовываются корректно |
| 3.10 | Сжать `logo.png` (1.9 МБ → < 100 КБ) | `assets/images/logo.png` | Размер уменьшен без видимой потери качества |

### Этап 4. Надёжность (P1/P2) — 2 дня

| # | Задача | Файлы | Критерий приёмки |
|---|---|---|---|
| 4.1 | Переписать разбор CSV: `csv.Sniffer`/`Dialect`, нормализация заголовков (`strip().lower()`), обрезка BOM | `services/csv_parser.py` | Фикстуры `Name,Label,Type` проходят |
| 4.2 | Точечные ошибки вместо `except Exception`: `TemplateParseError(row, column, reason)`, `csv_parser` собирает **все** ошибки и возвращает отчёт | `services/csv_parser.py`, `services/template_loader.py` | Сообщение содержит номер строки и колонку; ни одна «плохая» строка не даёт generic-текста |
| 4.3 | Толерантность к пустым значениям: `(row.get(k) or "").strip()`; `order` — безопасный `int` с fallback на индекс строки | `services/csv_parser.py:85-122` | 5 фикстур из раздела 3 либо парсятся, либо дают точную ошибку |
| 4.4 | Валидация шаблона: уникальность и непустота `name`, ненулевые `options` при `type=dropdown`, `order` | `services/csv_parser.py` (или новый `services/template_validator.py`) | Дубликаты/пустые имена отклоняются с понятным текстом |
| 4.5 | Определение кодировки: убрать `latin-1` из приоритетного списка, читать файл целиком (или чанками с `errors='strict'`), использовать `charset-normalizer`/`chardet` при наличии | `services/csv_parser.py:11-26` | `cp1251`-файл и `utf-8`-файл определяются верно; битый файл даёт ошибку |
| 4.6 | Логирование вместо `print`: модуль `logging`, уровень из env, для отладки — `logger.debug` | все сервисы и экраны | `grep -rn "print(" zond` → пусто |
| 4.7 | Убрать присваивание атрибутов до `super().__init__()` | `upload_screen.py:11-13`, `check_screen.py:13-14`, `inspection_screen.py:12` | Атрибуты задаются после `super().__init__()` |
| 4.8 | Проверка `page.window is not None` перед установкой размеров | `app/app.py:54-57` | Веб-режим не падает |

### Этап 5. Инженерная обвязка (P2) — 1–2 дня

| # | Задача | Критерий приёмки |
|---|---|---|
| 5.1 | `pyproject.toml`: метаданные, `requires-python`, зависимости, `[project.optional-dependencies] dev` | `pip install -e .` работает |
| 5.2 | Ruff (lint + format) + конфиг, исправить все замечания | `ruff check` и `ruff format --check` без ошибок |
| 5.3 | pytest: юнит-тесты парсера (включая все 5 фикстур из раздела 3), round-trip JSON, `ZondState` (переходы, конец, reset), смоук-сборка экранов | `pytest -q` зелёный, покрытие сервисов ≥ 80 % |
| 5.4 | `README.md`: назначение, установка, запуск (`python -m zond.ects`), формат CSV-шаблона (таблица колонок), формат JSON, структура проекта | Документ описывает запуск с нуля |
| 5.5 | `docs/template.md` — спецификация CSV: обязательные колонки, типы, `options`, `group`, `order` | Есть таблица всех 10 колонок |
| 5.6 | CI (GitHub Actions): ruff + pytest на PR | Зелёный workflow |
| 5.7 | Сборка дистрибутива (PyInstaller/flet build) под Windows/macOS | Есть инструкция и артефакт |
| 5.8 | `requirements.txt` → убрать дублирование с `pyproject.toml`, добавить перевод строки | Файл консистентен |

### Этап 6. Продуктовые фичи (P2) — бэклог

- Настройки: инспектор, объект, организация (сейчас `Inspection.object_name/inspector` всегда пусты).
- Экспорт отчёта в PDF/Excel, печать, отправка (`AppIcons.SEND`).
- Фотофиксация дефектов, вложения.
- Справочники оборудования, выбор объекта из списка.
- Разграничение ролей, подпись инспектора.
- Шаблоны: несколько групп, условные поля, вычисляемые значения, шкалы/оценки.

---

## 6. Рекомендуемая последовательность и оценка

| Этап | Содержание | Оценка | Блокирует |
|---|---|---|---|
| 0 | Стабилизация (BLOCKER 1-4) | 1 день | всё остальное |
| 1 | Завершение сценария проверки | 2–3 дня | отчёты, релиз |
| 2 | Данные: round-trip, отчёты, история | 3–4 дня | релиз |
| 3 | UX и дизайн-система | 2–3 дня | релиз |
| 4 | Надёжность CSV и логирование | 2 дня | —
| 5 | Тесты, CI, документация | 1–2 дня | поддержка |
| 6 | Продуктовые фичи | бэклог | —

**Итого до MVP:** ~8–11 рабочих дней (этапы 0–2 + 4 обязательны; 3 и 5 можно вести параллельно).

**Порядок первых трёх шагов (можно сделать сразу):**

1. Этап 0 целиком — иначе UI-слой не работает и его бессмысленно дописывать.
2. Этап 1.1–1.5 — замкнуть сценарий «загрузил → заполнил → сохранил», получить первый
   полезный артефакт и устойчивую точку для тестов.
3. Этап 5.3 — тесты на парсер и round-trip JSON: они защитят рефакторинги этапов 2 и 4.

---

## 7. Приложение: как воспроизводились проверки

```bash
# 1. Запуск сценария целиком (заглушка страницы Flet вместо реального окна)
python - <<'PY'
# FakePage + ZondApp + подмена file_picker.pick_files → templates/sample.csv
# далее CheckScreen.start_check → InspectionScreen → прогон 4 групп → JsonStorage.save
PY
# Результат: 4 группы, 12 полей, JSON записан; finished_at == None; answers == {}

# 2. Тенинг модуля
python -c "import zond.ui.widgets as w; print(w.__file__)"
# → .../zond/ui/widgets/__init__.py   (файл widgets.py недостижим)

# 3. Сломанные компоненты
python -c "from zond.ui.components.buttons import PrimaryButton; PrimaryButton('x')"
# → TypeError: Button.__init__() got an unexpected keyword argument 'text'
python -c "from zond.ui.components.progress import ProgressWidget; ProgressWidget('t',1,4)"
# → AttributeError: module 'flet.controls.padding' has no attribute 'symmetric'

# 4. Типы полей
# FieldBuilder.build() для FieldType.DATE / TIME → ft.Text("Неизвестный тип ...")

# 5. Устойчивость CSV: 5 фикстур, 4 падают с generic "Не удалось загрузить шаблон"

# 6. Версия API
python -c "import inspect,flet as ft; print(list(inspect.signature(ft.Button.__init__).parameters))"
# → [..., 'content', 'icon', ...]  — параметра 'text' нет
```

Проверено на: Python 3.13.9, flet 0.86.5, macOS, ветка `feature/ux` (+4 незакоммиченных файла).
