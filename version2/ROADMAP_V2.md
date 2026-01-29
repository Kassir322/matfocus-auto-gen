## ROADMAP v2 (переписываем v1 в отдельный проект)

### Важно (зафиксированные решения)

- **Новый проект отдельный**: в нём будет папка `old_code/` с кодом v1 для подсматривания.
- **Координаты**: храним **двумя словарями**:
  - `coordinates` (точки кликов)
  - `relative_movements` (смещения)
  - **не объединяем** их через `coords = {**...}`.
- **Остановка**: экстренная остановка по **Esc** — только жёсткий стоп подпроцесса (`terminate`), без проверок флагов внутри воркера.
- **Проверка генерации**: без HTML/DOM. Только анализ области скриншота.
- **Режимы**: есть `standard`, `multiformat`, `multiformat_with_refs`. **Первым реализуем `standard`.**
- **Параметры проверки изображения**: настраиваемые (таймаут/интервал/порог/область).
- **Файлы**: всё лежит в `data/` (settings, coordinates, prompts, refs).

---

### Что уже сделано (в этом репозитории, как документация)

- [x] `version2/PLAN_V2.md` — ТЗ и архитектура v2.
- [x] `version2/INTERFACE_aistudio_helpers.md` — интерфейс `sites/aistudio/helpers.py`.
- [x] `version2/INTERFACE_aistudio_modes.md` — интерфейсы режимов `standard` и `multiformat`.
- [x] `version2/INTERFACE_console_menu.md` — интерфейс консольного меню.
- [x] `version2/SETTINGS_V2.md` — список настроек v2 и способ настройки координат/окна.

---

### План работ для нового проекта v2 (чеклист)

#### Этап 0. Создать новый проект и положить v1 в `old_code/`

- [ ] Создать новый репозиторий/папку проекта.
- [ ] Добавить папку `old_code/` и скопировать туда v1 код (из текущего проекта) как reference.
- [ ] Создать `README.md` для v2: что делает программа, быстрый старт, хоткеи.
- [ ] Создать `data/` и положить туда:
  - `settings.json` (если нет — создаём автоматически)
  - `coordinates.json` (если нет — создаём автоматически)
  - файлы промптов
  - (для режима с референсами) `data/images/лицо` и `data/images/оборот`

#### Этап 1. Хранилища данных (без UI и без pyautogui)

Цель: простые функции, которые читают/пишут JSON.

- [ ] `settings_store.py`
  - `load_settings() -> dict`
  - `save_settings(settings: dict) -> None`
  - `apply_defaults(settings: dict) -> dict`
- [ ] `coordinates_store.py`
  - `load_coordinates() -> tuple[dict, dict]` → `(coordinates, relative_movements)`
  - `save_coordinates(coordinates: dict, relative_movements: dict) -> None`
  - `set_coordinate(name: str, x: int, y: int, coordinates: dict, relative_movements: dict) -> None`
- [ ] Определить формат `data/coordinates.json`:
  - ключ `coordinates` → dict точек
  - ключ `relative_movements` → dict смещений

#### Этап 2. Консольное меню (пока без генерации)

Цель: пользователь может выбрать сайт/режим/файл, посмотреть план.

- [ ] `ui/console_menu.py`:
  - `show_main_menu(settings, coordinates, relative_movements)`
  - `select_site(settings)`
  - `select_mode_for_site(settings)`
  - `select_prompts_file(settings)`:
    - сканирует `data/`, показывает **только файлы**
  - `show_generation_plan(settings)`:
    - вызывает `mode_standard.load_tasks_from_file` и `get_plan_info` (или выбранный режим)
- [ ] Показ “сводки перед стартом”:
  - карточек/промптов/изображений (по данным из файла промптов)

#### Этап 3. Hotkeys (полный набор, как в v1)

Цель: управление привычными клавишами, но с новой архитектурой.

- [ ] `ui/hotkeys.py` (функции + минимум состояния):
  - Ctrl+0: меню координат (как в v1)
  - Ctrl+Shift+P: получить координаты мыши / захват выбранной координаты
  - Ctrl+Shift+V: настройка окна
  - Ctrl+Shift+S: старт генерации (подпроцесс)
  - Esc: жёсткая остановка подпроцесса + (опционально) выход из программы
  - остальные хоткеи из v1 (настройки ожиданий, аспектов, режимов и т.д.)

#### Этап 4. Window manager (как в v1)

Цель: фиксированное окно (размер/позиция), чтобы координаты были стабильны.

- [ ] `utils/window_manager.py`:
  - `quick_setup_window()` для Ctrl+Shift+V (находит окно браузера и настраивает)
  - `setup_automation_window()` для автоподготовки перед стартом

#### Этап 5. Site: aistudio/helpers.py (база автоматизации UI)

Цель: все действия UI вынести в helpers, режимы не используют `pyautogui` напрямую.

- [ ] `sites/aistudio/helpers.py`:
  - базовые действия: click/keys/paste через буфер
  - чат: новый чат, переименование
  - формат: выбор aspect ratio
  - генерация: start, ожидание (по скриншоту), сохранение
  - ожидание:
    - если `CHECK_IMAGE_GENERATED = True` → ждём “готово или таймаут”
    - если `CHECK_IMAGE_GENERATED = False` → просто ждём таймаут (без анализа)

#### Этап 6. Режим 1: standard (первый!)

Цель: первый полностью рабочий режим.

- [ ] `sites/aistudio/mode_standard.py`:
  - `load_tasks_from_file(path, settings) -> list[Task]`
  - `get_plan_info(tasks) -> dict`
  - `run_mode(tasks, settings, coordinates, relative_movements) -> None`
  - логирование: `[PLAN] [CARD] [RESULT] [SUMMARY]`

#### Этап 7. Процессы и Esc (жёсткий стоп)

Цель: генерация всегда идёт в подпроцессе, и Esc гарантированно убивает её.

- [ ] `process_control.py`:
  - `start_worker(target_fn, args) -> Process`
  - `stop_worker(process) -> None` (terminate + join)
- [ ] Интеграция с меню и хоткеями:
  - запуск: Ctrl+Shift+S / пункт меню
  - остановка: Esc

#### Этап 8. Режим 2: multiformat

- [ ] `sites/aistudio/mode_multiformat.py`:
  - парсер “лицо/оборот”
  - `FACE_ASPECT_RATIO`, `BACK_ASPECT_RATIO`
  - порядок: лицо, затем оборот
  - сводка в начале и в конце

#### Этап 9. Режим 3: multiformat_with_refs

- [ ] `sites/aistudio/mode_multiformat_with_refs.py`:
  - поиск референсов в `data/images/лицо` и `data/images/оборот`
  - дополнительные координаты (например `PROMPT_INPUT_AFTER_IMAGE`)
  - вставка референса + дальнейшая генерация

#### Этап 10. Полировка (понятность и поддержка)

- [ ] Структурные логи во всех режимах.
- [ ] “Сводка перед стартом” всегда показывает:
  - сколько карточек будет обработано
  - сколько промптов/пар найдено
  - сколько изображений планируется
- [ ] Документация:
  - `HOTKEYS_V2.md` (полный список)
  - `TROUBLESHOOTING.md` (частые проблемы)
