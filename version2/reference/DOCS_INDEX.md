# Указатель документов v2 (какой файл за что отвечает)

При продолжении разработки используй этот файл: по теме задачи открой нужный документ. Пути — от корня репозитория: `version2/planning/...`, `version2/reference/...`.

| Документ | За что отвечает |
|----------|-----------------|
| **planning/PLAN_V2.md** | ТЗ и архитектура v2: цели, принципы, структура sites/aistudio, что не делаем. |
| **planning/PROJECT_STRUCTURE.md** | Дерево папок/файлов проекта, назначение модулей, примеры кода. |
| **planning/V1_TO_V2.md** | Миграция: что в v1 где лежит, как переносим в v2, что отбрасываем. |
| **reference/PROCESS_MODEL.md** | Модель процессов: главный vs воркер, жёсткий стоп по Esc (terminate), повторный запуск. |
| **reference/SETTINGS_V2.md** | Список настроек v2, типы, значения по умолчанию, настройка координат и окна (Ctrl+0, Ctrl+Shift+V). |
| **reference/COORDINATES_KEYS.md** | Все ключи координат и relative_movements, обязательные по режимам, формат JSON. |
| **reference/COORDINATES_SETUP_GUIDE.md** | Пошаговая настройка координат: Ctrl+0 → выбор → Ctrl+Shift+P, типичные ошибки. |
| **reference/INTERFACE_console_menu.md** | API консольного меню: show_main_menu, выбор сайта/режима/файла, план, запуск/остановка. |
| **reference/INTERFACE_aistudio_helpers.md** | API `sites/aistudio/helpers.py`: клики, вставка текста (Ctrl+V), сохранение изображения, ожидание готовности. |
| **reference/INTERFACE_aistudio_modes.md** | API режимов: load_tasks_from_file, get_plan_info, run_mode; структура Task для standard и multiformat. |
| **reference/MODES_REFERENCE.md** | Краткая справка по трём режимам (назначение, вход, Task, шаги). Прикладывать к промпту при написании кода режимов. |
| **reference/LOGGING.md** | Куда пишем: файл (новый при каждом запуске, имя с датой до секунды) vs консоль; теги капсом, без эмодзи. |
| **reference/ALGO_standard.md** | Пошаговый алгоритм режима standard: координаты, настройки, генерация одного изображения, имена, логи. |
| **reference/ALGO_multiformat.md** | Алгоритм multiformat: лицо/оборот, пары, aspect ratio, имена, логи. |
| **reference/ALGO_multiformat_with_refs.md** | Алгоритм с референсами: поиск референса, вставка в чат, проверка перед стартом. |
| **reference/PROMPTS_standard_format.md** | Формат файла промптов для standard: regex, примеры, результат парсинга. |
| **reference/PROMPTS_multiformat_format.md** | Формат файла промптов для multiformat: лицо/оборот, пары, неполные пары. |
| **reference/REFERENCES_format.md** | Папки data/images/лицо и оборот, формат имени референса, поиск, проверка. |
| **reference/NAMING_RULES.md** | Формат имён чатов и файлов по режимам; единый шаблон `Карточка_{N}_{сторона}_промпт_{M}.png`. |
| **reference/IMAGE_READY_DETECTION.md** | Как определять готовность изображения: скриншот области, различие с baseline, параметры, fallback. |
| **reference/HOTKEYS_V2.md** | Полный список горячих клавиш v2. |
| **reference/USER_FLOW.md** | Сценарий пользователя: установка, первая настройка, запуск, что видно в консоли и в логах. |
| **reference/TROUBLESHOOTING.md** | Частые проблемы и решения (координаты, окно, генерация, файлы промптов, референсы). |
