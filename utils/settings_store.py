"""
Хранилище настроек v2: чтение/запись data/settings.json.
Без UI и без pyautogui — только JSON.
"""
import json
import os

# Путь к файлу настроек (относительно рабочей директории)
SETTINGS_PATH = "data/settings.json"

# Настройки по умолчанию (SETTINGS_V2, раздел 9). SAVE_FOLDER, LOG_ENABLED, GENERATIONS_PER_CARD не добавляем.
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
    "BACK_ASPECT_RATIO": "3:2",
    # Настройки API (интеграция Gemini API)
    "GENERATION_METHOD": "browser",  # "browser" или "api"
    "API_KEY": "",
    "API_MODEL": "imagen-4.0-generate-001",  # imagen-4.0-fast/generate/ultra или gemini-2.5-flash-image
    "API_IMAGE_SIZE": "2K",  # "1K" или "2K" для Imagen 4; "1K", "2K", "4K" для старых моделей
    "API_TIMEOUT": 60.0,  # таймаут API запросов в секундах
}


def apply_defaults(settings: dict) -> dict:
    """
    Дополняет словарь недостающими ключами значениями по умолчанию.
    Изменяет переданный словарь, возвращает тот же объект.
    """
    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value
    # Пересчёт CARDS_TO_PROCESS по диапазону
    start = settings.get("START_FROM_CARD", 1)
    end = settings.get("END_CARD")
    if end is not None and isinstance(start, (int, float)) and isinstance(end, (int, float)):
        settings["CARDS_TO_PROCESS"] = max(0, int(end) - int(start) + 1)
    return settings


def load_settings() -> dict:
    """
    Читает настройки из data/settings.json.
    Если файла нет или ошибка — возвращает apply_defaults({}).
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
