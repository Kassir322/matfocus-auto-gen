"""
Хранилище настроек v2: чтение/запись data/settings.json.
Без UI и без pyautogui — только JSON.
"""
import json
import os


SETTINGS_PATH = "data/settings.json"

DEFAULT_SETTINGS = {
    "CURRENT_SITE": "aistudio",
    "CURRENT_MODE": "standard",
    "PROMPTS_FILE": "data/all_card_prompts.txt",
    "START_FROM_CARD": 1,
    "END_CARD": 50,
    "CARDS_TO_PROCESS": 50,
    "GENERATION_WAIT": 20.0,
    "IMAGE_WAIT_INTERVAL": 2.0,
    "CHECK_IMAGE_GENERATED": True,
    "FACE_ASPECT_RATIO": "4:3",
    "BACK_ASPECT_RATIO": "16:9",
    "OUTPUT_BASE_DIR": "generated_images",
    "OUTPUT_PROJECT_NAME": "project",
    "GENERATION_METHOD": "browser",
    "API_PROVIDER": "nanobanana",
    "API_PROVIDER_WITH_REFS": "nanobanana",
    "API_KEY": "",
    "API_KEY_NANOBANANA": "",
    "API_KEY_CHATGPT": "",
    "API_MODEL": "imagen-4.0-generate-001",
    "API_MODEL_WITH_REFS": "gemini-2.5-flash-image",
    "API_MODEL_CHATGPT": "gpt-image-2",
    "API_CHATGPT_QUALITY": "low",
    "API_STYLE_REFERENCE_IMAGE": "",
    "API_LOG_PROMPTS": True,
    "API_CHATGPT_PARALLEL_ENABLED": True,
    "API_CHATGPT_MAX_WORKERS": 2,
    "API_CHATGPT_RATE_LIMIT_IPM": 5,
    "API_CHATGPT_RATE_LIMIT_WINDOW_SECONDS": 60,
    "API_IMAGE_SIZE": "2K",
    "API_TIMEOUT": 60.0,
}


def apply_defaults(settings: dict) -> dict:
    """
    Дополняет словарь недостающими ключами значениями по умолчанию.
    Изменяет переданный словарь и возвращает тот же объект.
    """
    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value

    legacy_api_key = str(settings.get("API_KEY", "") or "").strip()
    if legacy_api_key and not str(settings.get("API_KEY_NANOBANANA", "") or "").strip():
        settings["API_KEY_NANOBANANA"] = legacy_api_key

    # Сохраняем совместимость со старым полем API_KEY.
    settings["API_KEY"] = str(settings.get("API_KEY_NANOBANANA", "") or "").strip()

    start = settings.get("START_FROM_CARD", 1)
    end = settings.get("END_CARD")
    if end is not None and isinstance(start, (int, float)) and isinstance(end, (int, float)):
        settings["CARDS_TO_PROCESS"] = max(0, int(end) - int(start) + 1)
    return settings


def load_settings() -> dict:
    """
    Читает настройки из data/settings.json.
    Если файла нет или произошла ошибка — возвращает apply_defaults({}).
    """
    try:
        if not os.path.isfile(SETTINGS_PATH):
            return apply_defaults({})
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, dict):
            return apply_defaults({})
        apply_defaults(loaded)
        return loaded
    except (OSError, json.JSONDecodeError):
        return apply_defaults({})


def save_settings(settings: dict) -> None:
    """
    Записывает настройки в data/settings.json.
    Перед записью дополняет дефолтами. Создаёт папку data/ при необходимости.
    """
    apply_defaults(settings)
    dir_path = os.path.dirname(SETTINGS_PATH)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def update_start_card(card_number: int) -> None:
    """
    Обновляет START_FROM_CARD в настройках до указанного номера карточки.

    Args:
        card_number: номер карточки для установки в START_FROM_CARD
    """
    settings = load_settings()
    settings["START_FROM_CARD"] = card_number
    end_card = settings.get("END_CARD")
    if isinstance(end_card, (int, float)) and int(end_card) < int(card_number):
        settings["END_CARD"] = int(card_number)
    save_settings(settings)
