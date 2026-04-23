"""
Запуск генерации v2: проверки перед стартом и воркеры для режимов
standard, multiformat и multiformat_with_refs.
"""
import os


def can_start_generation(settings: dict) -> tuple[bool, str | None]:
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


def can_start_generation_api(settings: dict) -> tuple[bool, str | None]:
    from utils import api_client

    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        return False, "Файл промптов не выбран."
    if not os.path.isfile(path):
        return False, f"Файл не найден: {path}"

    mode = settings.get("CURRENT_MODE", "standard")

    providers_to_check = {api_client.get_api_provider(settings, with_reference=False)}
    if mode == "multiformat_with_refs":
        providers_to_check.add(api_client.get_api_provider(settings, with_reference=True))

    for provider in providers_to_check:
        api_key = api_client.get_api_key(settings, provider)
        if not api_key:
            provider_name = api_client.get_provider_display_name(provider)
            return False, f"Не задан API ключ для провайдера {provider_name}. Настройте его в меню."
        key_valid, key_error = api_client.check_api_key_format(api_key, provider=provider)
        if not key_valid:
            provider_name = api_client.get_provider_display_name(provider)
            return False, f"{provider_name}: {key_error}"

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
    from sites.aistudio import mode_standard_api
    from utils import api_client

    api_client.reset_session_folder()

    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        print("Файл промптов не выбран. Укажите в настройках.")
        return

    tasks = mode_standard_api.load_tasks_from_file(path)
    if not tasks:
        print("Файл пустой или не содержит валидных строк.")
        return

    mode_standard_api.run_mode(tasks, settings, coordinates, relative_movements)


def run_multiformat_worker_api(settings: dict, coordinates: dict = None, relative_movements: dict = None) -> None:
    from sites.aistudio import mode_multiformat_api
    from utils import api_client

    api_client.reset_session_folder()

    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        print("Файл промптов не выбран. Укажите в настройках.")
        return

    tasks = mode_multiformat_api.load_tasks_from_file(path)
    if not tasks:
        print("Файл пустой или не содержит валидных строк.")
        return

    mode_multiformat_api.run_mode(tasks, settings, coordinates, relative_movements)


def run_multiformat_with_refs_worker_api(
    settings: dict,
    coordinates: dict = None,
    relative_movements: dict = None,
) -> None:
    from sites.aistudio import mode_multiformat_with_refs_api
    from utils import api_client

    api_client.reset_session_folder()

    path = settings.get("PROMPTS_FILE") or ""
    if not path or not path.strip():
        print("Файл промптов не выбран. Укажите в настройках.")
        return

    tasks = mode_multiformat_with_refs_api.load_tasks_from_file(path)
    if not tasks:
        print("Файл пустой или не содержит валидных строк.")
        return

    mode_multiformat_with_refs_api.run_mode(tasks, settings, coordinates, relative_movements)
