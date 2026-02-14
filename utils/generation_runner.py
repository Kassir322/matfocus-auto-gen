"""
Запуск генерации v2: проверки перед стартом и воркеры для режимов standard, multiformat и multiformat_with_refs.
Используется из main.py (Ctrl+Shift+S) и из ui/console_menu.py (пункт 5).
"""
import os


def can_start_generation(settings: dict) -> tuple[bool, str | None]:
    """
    Проверки перед стартом: файл выбран, существует, после фильтра есть задачи.
    Режим берётся из settings["CURRENT_MODE"] (standard, multiformat или multiformat_with_refs).
    Возвращает (ok: bool, error_message: str | None).
    """
    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        return False, "Файл промптов не выбран."
    if not os.path.isfile(path):
        return False, f"Файл не найден: {path}"
    mode = settings.get("CURRENT_MODE", "standard")
    if mode == "multiformat":
        from sites.aistudio import mode_multiformat
        tasks = mode_multiformat.load_tasks_from_file(path)
    elif mode == "multiformat_with_refs":
        from sites.aistudio import mode_multiformat_with_refs
        tasks = mode_multiformat_with_refs.load_tasks_from_file(path)
    else:
        from sites.aistudio import mode_standard
        tasks = mode_standard.load_tasks_from_file(path)
    if not tasks:
        return False, "Файл пустой или не содержит валидных строк."
    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)
    else:
        end_card = max(t["card_number"] for t in tasks)
    filtered = [t for t in tasks if start_card <= t["card_number"] <= end_card]
    if not filtered:
        return False, "Нет задач в выбранном диапазоне карточек."
    return True, None


def run_standard_worker(settings: dict, coordinates: dict, relative_movements: dict) -> None:
    """
    Воркер для режима standard: загрузка задач, фильтр по диапазону, run_mode.
    Вызывается в подпроцессе; принимает (settings, coordinates, relative_movements).
    """
    from sites.aistudio import mode_standard

    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        print("Файл промптов не выбран. Укажите в настройках.")
        return
    tasks = mode_standard.load_tasks_from_file(path)
    if not tasks:
        print("Файл пустой или не содержит валидных строк.")
        return

    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)
    else:
        end_card = max(t["card_number"] for t in tasks)
    tasks = [t for t in tasks if start_card <= t["card_number"] <= end_card]
    if not tasks:
        print("Нет задач в выбранном диапазоне карточек.")
        return

    mode_standard.run_mode(tasks, settings, coordinates, relative_movements)


def run_multiformat_worker(settings: dict, coordinates: dict, relative_movements: dict) -> None:
    """
    Воркер для режима multiformat: загрузка задач, фильтр по диапазону, run_mode.
    Вызывается в подпроцессе; принимает (settings, coordinates, relative_movements).
    """
    from sites.aistudio import mode_multiformat

    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        print("Файл промптов не выбран. Укажите в настройках.")
        return
    tasks = mode_multiformat.load_tasks_from_file(path)
    if not tasks:
        print("Файл пустой или не содержит валидных строк.")
        return

    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)
    else:
        end_card = max(t["card_number"] for t in tasks)
    tasks = [t for t in tasks if start_card <= t["card_number"] <= end_card]
    if not tasks:
        print("Нет задач в выбранном диапазоне карточек.")
        return

    mode_multiformat.run_mode(tasks, settings, coordinates, relative_movements)


def run_multiformat_with_refs_worker(settings: dict, coordinates: dict, relative_movements: dict) -> None:
    """
    Воркер для режима multiformat_with_refs: загрузка задач, фильтр по диапазону, run_mode.
    Вызывается в подпроцессе; принимает (settings, coordinates, relative_movements).
    """
    from sites.aistudio import mode_multiformat_with_refs

    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        print("Файл промптов не выбран. Укажите в настройках.")
        return
    tasks = mode_multiformat_with_refs.load_tasks_from_file(path)
    if not tasks:
        print("Файл пустой или не содержит валидных строк.")
        return

    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)
    else:
        end_card = max(t["card_number"] for t in tasks)
    tasks = [t for t in tasks if start_card <= t["card_number"] <= end_card]
    if not tasks:
        print("Нет задач в выбранном диапазоне карточек.")
        return

    mode_multiformat_with_refs.run_mode(tasks, settings, coordinates, relative_movements)


# --- API режимы генерации ---


def can_start_generation_api(settings: dict) -> tuple[bool, str | None]:
    """
    Проверки перед стартом API-генерации.
    
    Проверяет:
    - API_KEY задан и валиден
    - Файл промптов существует
    - Режим поддерживает API (standard или multiformat)
    
    Args:
        settings: словарь настроек
        
    Returns:
        (ok: bool, error_message: str | None)
    """
    # Проверка API ключа
    api_key = settings.get("API_KEY", "").strip()
    if not api_key:
        return False, "API_KEY не задан. Настройте API ключ в меню."
    
    # Валидация формата API ключа
    from utils import api_client
    key_valid, key_error = api_client.check_api_key_format(api_key)
    if not key_valid:
        return False, key_error
    
    # Проверка файла промптов
    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        return False, "Файл промптов не выбран."
    if not os.path.isfile(path):
        return False, f"Файл не найден: {path}"
    
    # Проверка режима (API поддерживает все режимы: standard, multiformat, multiformat_with_refs)
    mode = settings.get("CURRENT_MODE", "standard")
    
    # Проверка задач
    if mode == "multiformat":
        from sites.aistudio import mode_multiformat_api
        tasks = mode_multiformat_api.load_tasks_from_file(path)
    elif mode == "multiformat_with_refs":
        from sites.aistudio import mode_multiformat_with_refs_api
        tasks = mode_multiformat_with_refs_api.load_tasks_from_file(path)
    else:
        from sites.aistudio import mode_standard_api
        tasks = mode_standard_api.load_tasks_from_file(path)
    
    if not tasks:
        return False, "Файл пустой или не содержит валидных строк."
    
    # Фильтр по диапазону
    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)
    else:
        end_card = max(t["card_number"] for t in tasks)
    filtered = [t for t in tasks if start_card <= t["card_number"] <= end_card]
    if not filtered:
        return False, "Нет задач в выбранном диапазоне карточек."
    
    return True, None


def run_standard_worker_api(settings: dict, coordinates: dict = None, relative_movements: dict = None) -> None:
    """
    Воркер для режима standard через API (без браузера).
    Вызывается в подпроцессе; coordinates и relative_movements не используются.
    
    Args:
        settings: словарь настроек (должен содержать API_KEY, API_MODEL и т.д.)
        coordinates: не используется (совместимость сигнатуры)
        relative_movements: не используется (совместимость сигнатуры)
    """
    from sites.aistudio import mode_standard_api
    from utils import api_client
    
    # Сбросить папку сессии для создания новой папки при каждом запуске генерации
    api_client.reset_session_folder()
    
    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        print("Файл промптов не выбран. Укажите в настройках.")
        return
    
    tasks = mode_standard_api.load_tasks_from_file(path)
    if not tasks:
        print("Файл пустой или не содержит валидных строк.")
        return
    
    # Фильтр по диапазону выполняется внутри run_mode
    mode_standard_api.run_mode(tasks, settings, coordinates, relative_movements)


def run_multiformat_worker_api(settings: dict, coordinates: dict = None, relative_movements: dict = None) -> None:
    """
    Воркер для режима multiformat через API (без браузера).
    Вызывается в подпроцессе; coordinates и relative_movements не используются.
    
    Args:
        settings: словарь настроек (должен содержать API_KEY, API_MODEL и т.д.)
        coordinates: не используется (совместимость сигнатуры)
        relative_movements: не используется (совместимость сигнатуры)
    """
    from sites.aistudio import mode_multiformat_api
    from utils import api_client
    
    # Сбросить папку сессии для создания новой папки при каждом запуске генерации
    api_client.reset_session_folder()
    
    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        print("Файл промптов не выбран. Укажите в настройках.")
        return
    
    tasks = mode_multiformat_api.load_tasks_from_file(path)
    if not tasks:
        print("Файл пустой или не содержит валидных строк.")
        return
    
    # Фильтр по диапазону выполняется внутри run_mode
    mode_multiformat_api.run_mode(tasks, settings, coordinates, relative_movements)


def run_multiformat_with_refs_worker_api(settings: dict, coordinates: dict = None, relative_movements: dict = None) -> None:
    """
    Воркер для режима multiformat_with_refs через API (без браузера).
    Вызывается в подпроцессе; coordinates и relative_movements не используются.
    Поддерживает автоматический выбор модели в зависимости от наличия референса.
    
    Args:
        settings: словарь настроек (должен содержать API_KEY, API_MODEL, API_MODEL_WITH_REFS и т.д.)
        coordinates: не используется (совместимость сигнатуры)
        relative_movements: не используется (совместимость сигнатуры)
    """
    from sites.aistudio import mode_multiformat_with_refs_api
    from utils import api_client
    
    # Сбросить папку сессии для создания новой папки при каждом запуске генерации
    api_client.reset_session_folder()
    
    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        print("Файл промптов не выбран. Укажите в настройках.")
        return
    
    tasks = mode_multiformat_with_refs_api.load_tasks_from_file(path)
    if not tasks:
        print("Файл пустой или не содержит валидных строк.")
        return
    
    # Фильтр по диапазону выполняется внутри run_mode
    mode_multiformat_with_refs_api.run_mode(tasks, settings, coordinates, relative_movements)
