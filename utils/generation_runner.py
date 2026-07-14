"""Проверка и синхронный запуск единственного API-режима."""

import os

from sites.aistudio import mode_multiformat_with_refs_api
from utils import api_client
from utils.paths import resolve_app_path
from utils.prompt_parsers import filter_tasks_by_range


MODE_NAME = "multiformat_with_refs"


def _prompt_path(settings: dict) -> str:
    return resolve_app_path(settings.get("PROMPTS_FILE") or "")


def load_tasks(settings: dict) -> list[dict]:
    path = _prompt_path(settings)
    tasks = mode_multiformat_with_refs_api.load_tasks_from_file(path)
    return filter_tasks_by_range(
        tasks,
        int(settings.get("START_FROM_CARD", 1)),
        settings.get("END_CARD"),
    )


def can_start_generation_api(settings: dict) -> tuple[bool, str | None]:
    path = _prompt_path(settings)
    if not path or not path.strip():
        return False, "Файл промптов не выбран."
    if not os.path.isfile(path):
        return False, f"Файл не найден: {path}"

    style_error = mode_multiformat_with_refs_api.validate_style_reference_settings(settings)
    if style_error:
        return False, style_error

    providers = {
        api_client.get_api_provider(settings, with_reference=False),
        api_client.get_api_provider(settings, with_reference=True),
    }
    for provider in providers:
        api_key = api_client.get_api_key(settings, provider)
        if not api_key:
            return False, f"Не задан API ключ для {api_client.get_provider_display_name(provider)}."
        valid, error = api_client.check_api_key_format(api_key, provider=provider)
        if not valid:
            return False, f"{api_client.get_provider_display_name(provider)}: {error}"

    if not load_tasks(settings):
        return False, "Нет задач в выбранном диапазоне карточек."
    return True, None


def run_api(settings: dict) -> dict:
    ok, error = can_start_generation_api(settings)
    if not ok:
        return {"ok": False, "mode": MODE_NAME, "errors": [error or "Запуск невозможен."]}

    api_client.reset_session_folder()
    return mode_multiformat_with_refs_api.run_mode(load_tasks(settings), settings)
