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
