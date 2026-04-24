"""Focused checks for API-mode console progress formatting."""

import io
from contextlib import redirect_stdout

from sites.aistudio import mode_multiformat_api
from sites.aistudio import mode_multiformat_with_refs_api
from sites.aistudio import mode_standard_api


def _base_settings():
    return {
        "API_KEY": "AIzaSyDUMMY_KEY_FOR_TESTS_123456789012345",
        "START_FROM_CARD": 1,
        "END_CARD": 1,
        "API_PROVIDER": "nanobanana",
        "API_PROVIDER_WITH_REFS": "nanobanana",
        "FACE_ASPECT_RATIO": "4:3",
        "BACK_ASPECT_RATIO": "16:9",
    }


def _patch_api_runtime(monkeypatch, module, log_path):
    monkeypatch.setattr(module, "_get_log_filepath", lambda: str(log_path))
    monkeypatch.setattr(module.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module.api_client, "check_api_key_format", lambda api_key, provider="nanobanana": (True, None))
    monkeypatch.setattr(module.api_client, "init_client", lambda api_key, provider="nanobanana": object())
    monkeypatch.setattr(module.api_client, "get_session_output_folder", lambda: "generated_images/session")


def test_standard_api_run_mode_prints_extended_progress_and_summary(tmp_path, monkeypatch):
    log_path = tmp_path / "standard_api.log"
    update_calls = []
    results = iter([True, False])

    _patch_api_runtime(monkeypatch, mode_standard_api, log_path)
    monkeypatch.setattr(mode_standard_api, "_generate_single_image_api", lambda *args, **kwargs: next(results))
    monkeypatch.setattr("utils.settings_store.update_start_card", lambda card_number: update_calls.append(card_number))

    tasks = [
        {"card_number": 1, "generation_number": 1, "prompt_text": "A"},
        {"card_number": 1, "generation_number": 2, "prompt_text": "B"},
    ]

    output = io.StringIO()
    with redirect_stdout(output):
        mode_standard_api.run_mode(tasks, _base_settings())

    rendered = output.getvalue()
    assert "Примерное время:" in rendered
    assert "Примерная стоимость:" in rendered
    assert "Генерация 1/1 из 2 - " in rendered
    assert "avg " in rendered
    assert "fail 1" in rendered
    assert "Итоги генерации:" in rendered
    assert "Не удалось сгенерировать:" in rendered
    assert update_calls == [2]


def test_standard_api_run_mode_prints_actual_chatgpt_cost_when_available(tmp_path, monkeypatch):
    log_path = tmp_path / "standard_api_chatgpt.log"
    update_calls = []
    results = iter([True, True])

    _patch_api_runtime(monkeypatch, mode_standard_api, log_path)
    monkeypatch.setattr(mode_standard_api, "_generate_single_image_api", lambda *args, **kwargs: next(results))
    monkeypatch.setattr(mode_standard_api.api_client, "fetch_openai_costs", lambda *args, **kwargs: (1.49, None))
    monkeypatch.setattr("utils.settings_store.update_start_card", lambda card_number: update_calls.append(card_number))

    settings = _base_settings()
    settings["API_PROVIDER"] = "chatgpt"
    settings["API_KEY_CHATGPT"] = "sk-test-12345678901234567890"
    tasks = [
        {"card_number": 1, "generation_number": 1, "prompt_text": "A"},
        {"card_number": 1, "generation_number": 2, "prompt_text": "B"},
    ]

    output = io.StringIO()
    with redirect_stdout(output):
        mode_standard_api.run_mode(tasks, settings)

    rendered = output.getvalue()
    assert "Фактические расходы ChatGPT: $1.490" in rendered
    assert "Оценка стоимости по попыткам:" in rendered
    assert update_calls == [2]


def test_multiformat_api_run_mode_prints_extended_progress_and_summary(tmp_path, monkeypatch):
    log_path = tmp_path / "multiformat_api.log"
    update_calls = []
    results = iter([True, False])

    _patch_api_runtime(monkeypatch, mode_multiformat_api, log_path)
    monkeypatch.setattr(mode_multiformat_api, "_generate_single_image_api", lambda *args, **kwargs: next(results))
    monkeypatch.setattr("utils.settings_store.update_start_card", lambda card_number: update_calls.append(card_number))

    tasks = [
        {"card_number": 1, "card_name": "Нефть", "pair_number": 1, "side": "лицо", "prompt_text": "A"},
        {"card_number": 1, "card_name": "Нефть", "pair_number": 1, "side": "оборот", "prompt_text": "B"},
    ]

    output = io.StringIO()
    with redirect_stdout(output):
        mode_multiformat_api.run_mode(tasks, _base_settings())

    rendered = output.getvalue()
    assert "Примерное время:" in rendered
    assert "Примерная стоимость:" in rendered
    assert "Генерация 1/1 из 2 - " in rendered
    assert "Генерация 1/2 из 2 - " in rendered
    assert "Итоги генерации:" in rendered
    assert update_calls == [2]


def test_multiformat_with_refs_api_run_mode_prints_extended_progress_and_summary(tmp_path, monkeypatch):
    log_path = tmp_path / "multiformat_with_refs_api.log"
    update_calls = []
    results = iter([True, False])

    _patch_api_runtime(monkeypatch, mode_multiformat_with_refs_api, log_path)
    monkeypatch.setattr(
        mode_multiformat_with_refs_api,
        "_generate_single_image_api",
        lambda *args, **kwargs: next(results),
    )
    monkeypatch.setattr(mode_multiformat_with_refs_api, "get_reference_path", lambda *args, **kwargs: None)
    monkeypatch.setattr("utils.settings_store.update_start_card", lambda card_number: update_calls.append(card_number))

    tasks = [
        {"card_number": 1, "card_name": "Нефть", "pair_number": 1, "side": "лицо", "prompt_text": "A"},
        {"card_number": 1, "card_name": "Нефть", "pair_number": 1, "side": "оборот", "prompt_text": "B"},
    ]

    output = io.StringIO()
    with redirect_stdout(output):
        mode_multiformat_with_refs_api.run_mode(tasks, _base_settings())

    rendered = output.getvalue()
    assert "Примерное время:" in rendered
    assert "Примерная стоимость:" in rendered
    assert "Генерация 1/1 из 2 - " in rendered
    assert "Генерация 1/2 из 2 - " in rendered
    assert "Итоги генерации:" in rendered
    assert update_calls == [2]
