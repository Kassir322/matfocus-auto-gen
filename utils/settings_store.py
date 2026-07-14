"""
Хранилище настроек v2.

`data/settings.json` хранит только безопасные общие настройки. API-ключи
загружаются из окружения или локального `.env` и присутствуют только в памяти
для совместимости со старым runtime-контрактом.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from utils.paths import repo_path, resolve_app_path, storage_path_value


SETTINGS_PATH = str(repo_path("data", "settings.json"))
ENV_PATH = str(repo_path(".env"))

SECRET_KEYS = {"API_KEY", "API_KEY_NANOBANANA", "API_KEY_CHATGPT"}
TRANSIENT_KEYS = {"API_FACE_IMAGE_SIZE", "API_BACK_IMAGE_SIZE", "SAVE_PROGRESS_TO_SETTINGS"}
PATH_KEYS = {"PROMPTS_FILE", "OUTPUT_BASE_DIR", "API_STYLE_REFERENCE_IMAGE"}

ENV_KEY_BY_FIELD = {
    "API_KEY_NANOBANANA": "GOOGLE_API_KEY",
    "API_KEY_CHATGPT": "OPENAI_API_KEY",
}

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
    "API_MODEL": "imagen-4.0-generate-001",
    "API_MODEL_WITH_REFS": "gemini-2.5-flash-image",
    "API_MODEL_CHATGPT": "gpt-image-2",
    "API_CHATGPT_QUALITY": "low",
    "API_STYLE_REFERENCE_IMAGE": "",
    "API_LOG_PROMPTS": True,
    "API_CHATGPT_PARALLEL_ENABLED": True,
    "API_CHATGPT_RATE_LIMIT_PROFILE": "tier3",
    "API_CHATGPT_MAX_WORKERS": 50,
    "API_CHATGPT_RATE_LIMIT_IPM": 50,
    "API_CHATGPT_RATE_LIMIT_WINDOW_SECONDS": 60,
    "API_CHATGPT_RATE_LIMIT_TPM": 800000,
    "API_CHATGPT_MONTHLY_USAGE_LIMIT_USD": 1000,
    "API_IMAGE_SIZE": "2K",
    "API_TIMEOUT": 60.0,
}

SAVED_SETTINGS_KEYS = set(DEFAULT_SETTINGS)


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_env_file(path: str | os.PathLike | None = None) -> dict[str, str]:
    env_path = Path(path or ENV_PATH)
    values: dict[str, str] = {}
    try:
        if not env_path.is_file():
            return values
        for line in env_path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(line)
            if parsed is None:
                continue
            key, value = parsed
            values[key] = value
            os.environ.setdefault(key, value)
    except OSError:
        return values
    return values


def _env_value(name: str, env_values: dict[str, str]) -> str:
    return str(os.environ.get(name) or env_values.get(name) or "").strip()


def _apply_secret_env(settings: dict, env_values: dict[str, str] | None = None) -> None:
    env_values = env_values if env_values is not None else load_env_file()
    google_key = _env_value("GOOGLE_API_KEY", env_values)
    openai_key = _env_value("OPENAI_API_KEY", env_values)

    if not google_key:
        google_key = str(settings.get("API_KEY_NANOBANANA") or settings.get("API_KEY") or "").strip()
    if not openai_key:
        openai_key = str(settings.get("API_KEY_CHATGPT") or "").strip()

    settings["API_KEY_NANOBANANA"] = google_key
    settings["API_KEY_CHATGPT"] = openai_key
    settings["API_KEY"] = google_key


def _resolve_runtime_paths(settings: dict) -> None:
    for key in PATH_KEYS:
        value = str(settings.get(key, "") or "").strip()
        if value:
            settings[key] = resolve_app_path(value)


def apply_defaults(settings: dict) -> dict:
    """
    Дополняет словарь недостающими ключами и вычисляет совместимые поля.
    Изменяет переданный словарь и возвращает тот же объект.
    """
    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value

    start = settings.get("START_FROM_CARD", 1)
    end = settings.get("END_CARD")
    if end is not None and isinstance(start, (int, float)) and isinstance(end, (int, float)):
        settings["CARDS_TO_PROCESS"] = max(0, int(end) - int(start) + 1)

    _resolve_runtime_paths(settings)
    _apply_secret_env(settings)
    return settings


def load_settings() -> dict:
    """
    Читает безопасные настройки из data/settings.json и дополняет ключами из
    окружения или `.env` только в памяти.
    """
    env_values = load_env_file()
    try:
        if not os.path.isfile(SETTINGS_PATH):
            settings = {}
        else:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            settings = loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        settings = {}

    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value

    start = settings.get("START_FROM_CARD", 1)
    end = settings.get("END_CARD")
    if end is not None and isinstance(start, (int, float)) and isinstance(end, (int, float)):
        settings["CARDS_TO_PROCESS"] = max(0, int(end) - int(start) + 1)

    _resolve_runtime_paths(settings)
    _apply_secret_env(settings, env_values)
    return settings


def sanitize_for_storage(settings: dict) -> dict:
    storage = {}
    merged = dict(DEFAULT_SETTINGS)
    merged.update(settings)
    start = merged.get("START_FROM_CARD", 1)
    end = merged.get("END_CARD")
    if end is not None and isinstance(start, (int, float)) and isinstance(end, (int, float)):
        merged["CARDS_TO_PROCESS"] = max(0, int(end) - int(start) + 1)

    for key in sorted(SAVED_SETTINGS_KEYS):
        if key in SECRET_KEYS or key in TRANSIENT_KEYS:
            continue
        value = merged.get(key)
        if key in PATH_KEYS:
            value = storage_path_value(value)
        storage[key] = value
    return storage


def _atomic_write_text(path: str | os.PathLike, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.replace(temp_name, target)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def save_settings(settings: dict) -> None:
    """Записывает в data/settings.json только безопасные общие настройки."""
    storage = sanitize_for_storage(settings)
    content = json.dumps(storage, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_text(SETTINGS_PATH, content)


def save_secret(provider: str, api_key: str) -> None:
    from utils import api_client

    normalized = api_client.normalize_provider(provider)
    env_key = "OPENAI_API_KEY" if normalized == api_client.PROVIDER_CHATGPT else "GOOGLE_API_KEY"
    api_key = str(api_key or "").strip()
    if not api_key:
        raise ValueError("API ключ не может быть пустым")

    env_path = Path(ENV_PATH)
    lines: list[str] = []
    replaced = False
    try:
        if env_path.is_file():
            lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []

    for index, line in enumerate(lines):
        parsed = _parse_env_line(line)
        if parsed is None:
            continue
        key, _value = parsed
        if key == env_key:
            lines[index] = f"{env_key}={api_key}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{env_key}={api_key}")

    _atomic_write_text(env_path, "\n".join(lines).rstrip() + "\n")
    os.environ[env_key] = api_key


def update_start_card(card_number: int) -> None:
    settings = load_settings()
    settings["START_FROM_CARD"] = card_number
    end_card = settings.get("END_CARD")
    if isinstance(end_card, (int, float)) and int(end_card) < int(card_number):
        settings["END_CARD"] = int(card_number)
    save_settings(settings)
