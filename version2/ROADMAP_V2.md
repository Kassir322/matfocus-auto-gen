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

**Как пользоваться:** для разработки по промпту достаточно ссылаться на этот файл. В каждом этапе указаны документы (жирным), которые нужно открыть для деталей. Полный указатель «какой файл за что отвечает» — в конце файла (таблица «Сводка по документам»).

#### Этап 0. Создать новый проект и положить v1 в `old_code/`

- [ ] Создать новый репозиторий/папку проекта.
- [ ] Добавить папку `old_code/` и скопировать туда v1 код (из текущего проекта) как reference.
- [ ] Создать `README.md` для v2: что делает программа, быстрый старт, хоткеи.
- [ ] Создать `data/` и положить туда:
  - `settings.json` (если нет — создаём автоматически)
  - `coordinates.json` (если нет — создаём автоматически)
  - файлы промптов
  - (для режима с референсами) `data/images/лицо` и `data/images/оборот`

Структура папок → **PROJECT_STRUCTURE.md**.

#### Этап 1. Процессы и Esc (жёсткий стоп) — база программы

Цель: заложить в основу программы запуск работы в подпроцессе и гарантированную остановку по Esc. Вся генерация потом будет опираться на этот слой.

- [ ] `utils/process_control.py` (или аналог):
  - `start_worker(target_fn, args) -> Process` — запуск воркера в отдельном процессе
  - `stop_worker(process) -> None` — жёсткий стоп: `terminate()` + `join(timeout)`
- [ ] Регистрация Esc: при нажатии вызывается `stop_worker` для текущего процесса генерации.
- [ ] Интеграция с точкой входа: при «запуск генерации» всегда создаётся подпроцесс; консоль/меню остаются в главном процессе и слушают Esc.

Подробно: **PROCESS_MODEL.md**.

#### Этап 2. Хранилища данных (без UI и без pyautogui)

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

Настройки и координаты: **SETTINGS_V2.md**, **COORDINATES_KEYS.md**.

#### Этап 3. Консольное меню (пока без генерации)

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

Контракт меню: **INTERFACE_console_menu.md**.

#### Этап 4. Hotkeys (полный набор, как в v1)

Цель: управление привычными клавишами, но с новой архитектурой.

- [ ] `ui/hotkeys.py` (функции + минимум состояния):
  - Ctrl+0: меню координат (как в v1)
  - Ctrl+Shift+P: получить координаты мыши / захват выбранной координаты
  - Ctrl+Shift+V: настройка окна
  - Ctrl+Shift+S: старт генерации (подпроцесс)
  - Esc: вызов `stop_worker()` (жёсткая остановка подпроцесса; база заложена в Этапе 1)
  - остальные хоткеи из v1 (настройки ожиданий, аспектов, режимов и т.д.)

Список хоткеев: **HOTKEYS_V2.md**.

#### Этап 5. Window manager (как в v1)

Цель: фиксированное окно (размер/позиция), чтобы координаты были стабильны.

- [ ] `utils/window_manager.py`:
  - `quick_setup_window()` для Ctrl+Shift+V (находит окно браузера и настраивает)
  - `setup_automation_window()` для автоподготовки перед стартом

Настройка координат (UX): **COORDINATES_SETUP_GUIDE.md**.

#### Этап 6. Site: aistudio/helpers.py (база автоматизации UI)

Цель: все действия UI вынести в helpers, режимы не используют `pyautogui` напрямую.

- [ ] `sites/aistudio/helpers.py`:
  - базовые действия: click/keys/paste через буфер
  - чат: новый чат, переименование
  - формат: выбор aspect ratio
  - генерация: start, ожидание (по скриншоту), сохранение
  - ожидание:
    - если `CHECK_IMAGE_GENERATED = True` → ждём “готово или таймаут”
    - если `CHECK_IMAGE_GENERATED = False` → просто ждём таймаут (без анализа)

Интерфейс helpers: **INTERFACE_aistudio_helpers.md**. Ожидание готовности изображения: **IMAGE_READY_DETECTION.md**.

#### Этап 7. Режим 1: standard (первый!)

Цель: первый полностью рабочий режим.

- [ ] `sites/aistudio/mode_standard.py`:
  - `load_tasks_from_file(path, settings) -> list[Task]`
  - `get_plan_info(tasks) -> dict`
  - `run_mode(tasks, settings, coordinates, relative_movements) -> None`
  - логирование: в файл с тегами `[PLAN]` `[CARD]` `[OK]` `[SUMMARY]` и др., консоль — только основные шаги

Алгоритм и контракт: **ALGO_standard.md**, **INTERFACE_aistudio_modes.md**. Формат промптов: **PROMPTS_standard_format.md**. Имена чатов/файлов: **NAMING_RULES.md**. Логи: **LOGGING.md**.

#### Этап 8. Режим 2: multiformat

- [ ] `sites/aistudio/mode_multiformat.py`:
  - парсер “лицо/оборот”
  - `FACE_ASPECT_RATIO`, `BACK_ASPECT_RATIO`
  - порядок: лицо, затем оборот
  - сводка в начале и в конце

Алгоритм: **ALGO_multiformat.md**. Формат промптов: **PROMPTS_multiformat_format.md**.

#### Этап 9. Режим 3: multiformat_with_refs

- [ ] `sites/aistudio/mode_multiformat_with_refs.py`:
  - поиск референсов в `data/images/лицо` и `data/images/оборот`
  - дополнительные координаты (например `PROMPT_INPUT_AFTER_IMAGE`)
  - вставка референса + дальнейшая генерация

Алгоритм: **ALGO_multiformat_with_refs.md**. Формат референсов: **REFERENCES_format.md**.

#### Этап 10. Полировка (понятность и поддержка)

- [ ] Логи в файл во всех режимах (теги капсом, без эмодзи); консоль — минимум (LOGGING.md).
- [ ] “Сводка перед стартом” всегда показывает:
  - сколько карточек будет обработано
  - сколько промптов/пар найдено
  - сколько изображений планируется
- [ ] Документация: сверить с **HOTKEYS_V2.md**, **TROUBLESHOOTING.md**.

---

### Сводка по документам (какой файл за что отвечает)

Разработку можно вести, опираясь на этот ROADMAP: для каждого этапа указаны ссылки на нужные документы. Ниже — краткий указатель по всем файлам в `version2/`.

| Документ | За что отвечает |
|----------|-----------------|
| **ROADMAP_V2.md** (этот файл) | Порядок работ (этапы 0–10), ключевые решения, указатель по документам. **Главная точка входа для промпта.** |
| **PLAN_V2.md** | ТЗ и архитектура v2: цели, принципы, структура sites/aistudio, что не делаем. |
| **PROJECT_STRUCTURE.md** | Дерево папок/файлов проекта, назначение модулей, примеры кода. |
| **PROCESS_MODEL.md** | Модель процессов: главный vs воркер, жёсткий стоп по Esc (terminate), повторный запуск. |
| **SETTINGS_V2.md** | Список настроек v2, типы, значения по умолчанию, настройка координат и окна (Ctrl+0, Ctrl+Shift+V). |
| **COORDINATES_KEYS.md** | Все ключи координат и relative_movements, обязательные по режимам, формат JSON. |
| **COORDINATES_SETUP_GUIDE.md** | Пошаговая настройка координат: Ctrl+0 → выбор → Ctrl+Shift+P, типичные ошибки. |
| **INTERFACE_console_menu.md** | API консольного меню: show_main_menu, выбор сайта/режима/файла, план, запуск/остановка. |
| **INTERFACE_aistudio_helpers.md** | API `sites/aistudio/helpers.py`: клики, вставка текста (Ctrl+V), сохранение изображения, ожидание готовности. |
| **INTERFACE_aistudio_modes.md** | API режимов: load_tasks_from_file, get_plan_info, run_mode; структура Task для standard и multiformat. |
| **LOGGING.md** | Куда пишем: файл (новый при каждом запуске, имя с датой до секунды) vs консоль; теги капсом, без эмодзи. |
| **ALGO_standard.md** | Пошаговый алгоритм режима standard: координаты, настройки, генерация одного изображения, имена, логи. |
| **ALGO_multiformat.md** | Алгоритм multiformat: лицо/оборот, пары, aspect ratio, имена, логи. |
| **ALGO_multiformat_with_refs.md** | Алгоритм с референсами: поиск референса, вставка в чат, проверка перед стартом. |
| **PROMPTS_standard_format.md** | Формат файла промптов для standard: regex, примеры, результат парсинга. |
| **PROMPTS_multiformat_format.md** | Формат файла промптов для multiformat: лицо/оборот, пары, неполные пары. |
| **REFERENCES_format.md** | Папки data/images/лицо и оборот, формат имени референса, поиск, проверка. |
| **NAMING_RULES.md** | Формат имён чатов и файлов по режимам; единый шаблон `Карточка_{N}_{сторона}_промпт_{M}.png`. |
| **IMAGE_READY_DETECTION.md** | Как определять готовность изображения: скриншот области, различие с baseline, параметры, fallback. |
| **HOTKEYS_V2.md** | Полный список горячих клавиш v2. |
| **USER_FLOW.md** | Сценарий пользователя: установка, первая настройка, запуск, что видно в консоли и в логах. |
| **TROUBLESHOOTING.md** | Частые проблемы и решения (координаты, окно, генерация, файлы промптов, референсы). |
| **V1_TO_V2.md** | Миграция: что в v1 где лежит, как переносим в v2, что отбрасываем. |
