"""Консольное меню единственного API-режима."""

import builtins

from sites.aistudio import mode_multiformat_with_refs_api as mode_module
from utils import api_client
from utils.generation_runner import MODE_NAME, can_start_generation_api, load_tasks, run_api
from utils.paths import DATA_DIR, resolve_app_path


def _read(prompt: str = "Выбор: ") -> str:
    return builtins.input(prompt).strip()


def _save(settings: dict) -> None:
    from utils.settings_store import save_settings
    save_settings(settings)


def _set_text(settings: dict, key: str, label: str) -> None:
    value = _read(f"{label} [{settings.get(key, '')}]: ")
    if value:
        settings[key] = value
        _save(settings)


def _set_int(settings: dict, key: str, label: str) -> None:
    raw = _read(f"{label} [{settings.get(key, '')}]: ")
    if not raw:
        return
    try:
        value = int(raw)
        if value < 1:
            raise ValueError
    except ValueError:
        print("Введите положительное целое число.")
        return
    settings[key] = value
    if key == "START_FROM_CARD" and settings.get("END_CARD") is not None:
        settings["END_CARD"] = max(value, int(settings["END_CARD"]))
    _save(settings)


def select_prompts_file(settings: dict) -> None:
    try:
        names = sorted((item.name for item in DATA_DIR.iterdir() if item.suffix.lower() == ".txt"), reverse=True)
    except OSError:
        names = []
    if not names:
        print("В папке data/ нет файлов промптов.")
        return
    for number, name in enumerate(names, 1):
        print(f"{number}. {name}")
    try:
        settings["PROMPTS_FILE"] = str(DATA_DIR / names[int(_read("Номер файла: ")) - 1])
    except (ValueError, IndexError):
        print("Неверный номер.")
        return
    _save(settings)


def configure_api(settings: dict) -> None:
    fields = {
        "1": ("API_PROVIDER", "Провайдер без референса"),
        "2": ("API_PROVIDER_WITH_REFS", "Провайдер с референсом"),
        "3": ("API_MODEL", "Модель без референса"),
        "4": ("API_MODEL_WITH_REFS", "Модель с референсом"),
        "5": ("API_MODEL_CHATGPT", "Модель ChatGPT"),
        "6": ("API_CHATGPT_QUALITY", "Качество ChatGPT"),
        "7": ("API_IMAGE_SIZE", "Размер изображения"),
        "8": ("FACE_ASPECT_RATIO", "Соотношение лица X:Y"),
        "9": ("BACK_ASPECT_RATIO", "Соотношение оборота X:Y"),
        "10": ("API_TIMEOUT", "Таймаут API"),
    }
    for number, (_key, label) in fields.items():
        print(f"{number}. {label}")
    selected = fields.get(_read("Номер: "))
    if selected:
        _set_text(settings, *selected)


def configure_output(settings: dict) -> None:
    choice = _read("1. Базовая папка\n2. Имя проекта\nНомер: ")
    if choice == "1":
        _set_text(settings, "OUTPUT_BASE_DIR", "Базовая папка")
    elif choice == "2":
        _set_text(settings, "OUTPUT_PROJECT_NAME", "Имя проекта")


def configure_style_reference(settings: dict) -> None:
    value = _read("Путь к стилевому референсу (Enter — очистить): ")
    settings["API_STYLE_REFERENCE_IMAGE"] = resolve_app_path(value) if value else ""
    _save(settings)


def show_current_config(settings: dict) -> None:
    print("Режим: multiformat_with_refs, метод: API")
    print(f"Файл: {settings.get('PROMPTS_FILE') or 'не выбран'}")
    print(f"Карточки: {settings.get('START_FROM_CARD')}–{settings.get('END_CARD')}")
    print(f"Провайдеры: {api_client.get_api_provider(settings, False)} / {api_client.get_api_provider(settings, True)}")
    print(f"Папка вывода: {settings.get('OUTPUT_BASE_DIR')}")
    print(f"Стилевой референс: {settings.get('API_STYLE_REFERENCE_IMAGE') or 'нет'}")


def show_generation_plan(settings: dict) -> None:
    tasks = load_tasks(settings)
    if not tasks:
        print("Нет задач в выбранном диапазоне.")
        return
    plan = mode_module.get_plan_info(tasks)
    refs = mode_module.get_references_summary(tasks, settings)
    print(f"План: карточек {plan['cards_count']}, пар {plan['pairs_count']}, изображений {plan['images_planned']}.")
    print(f"Контентных референсов: {refs['content_refs_found']}; стилевой: {refs['style_reference_enabled']}.")


def start_generation(settings: dict) -> None:
    ok, error = can_start_generation_api(settings)
    if not ok:
        print(error)
        return
    print("Запуск API-генерации. Для остановки используйте Ctrl+C.")
    result = run_api(settings)
    print(f"Готово: успешно {result.get('succeeded', 0)}, ошибок {result.get('failed', 0)}.")


def show_main_menu(settings: dict) -> None:
    actions = {
        "1": lambda: select_prompts_file(settings),
        "2": lambda: _set_int(settings, "START_FROM_CARD", "Начальная карточка"),
        "3": lambda: _set_int(settings, "END_CARD", "Конечная карточка"),
        "4": lambda: configure_api(settings),
        "5": lambda: configure_output(settings),
        "6": lambda: configure_style_reference(settings),
        "7": lambda: show_current_config(settings),
        "8": lambda: show_generation_plan(settings),
        "9": lambda: start_generation(settings),
    }
    while True:
        print("\n=== API: multiformat_with_refs ===")
        print("1. Файл промптов\n2. Начальная карточка\n3. Конечная карточка\n4. Параметры API\n5. Папка вывода и проект\n6. Стилевой референс\n7. Конфигурация\n8. План\n9. Запуск\n0. Выход")
        choice = _read()
        if choice == "0":
            return
        action = actions.get(choice)
        if action:
            action()
