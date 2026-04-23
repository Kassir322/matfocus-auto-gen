"""Focused checks for the active multiformat_with_refs-mode contract."""

import io
from contextlib import redirect_stdout

from sites.aistudio import mode_multiformat_with_refs


def test_generate_single_side_with_ref_logs_wait_timeout_warning(monkeypatch):
    log_lines = []

    monkeypatch.setattr(
        "sites.aistudio.mode_multiformat_with_refs.write_log_line",
        lambda log_file, line: log_lines.append(line),
    )
    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs.time.sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs.get_reference_path", lambda *args, **kwargs: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs.helpers.click_new_chat", lambda coords: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs.helpers.click_prompt_input", lambda coords: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs.helpers.paste_prompt_text", lambda prompt_text, delay=0.05: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs.helpers.rename_chat", lambda coords, new_name: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs.helpers.select_aspect_ratio", lambda coords, ratio_text: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs.helpers.start_generation", lambda: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs.helpers.wait_until_image_ready", lambda *args, **kwargs: False)
    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs.helpers.save_image", lambda coords, relative_movements, file_name: None)

    ok = mode_multiformat_with_refs._generate_single_side_with_ref(
        {
            "card_number": 5,
            "card_name": "Порт",
            "pair_number": 3,
            "side": "лицо",
            "prompt_text": "Prompt",
        },
        "4:3",
        {
            "PROMPT_INPUT": (1, 1),
            "IMAGE_LOCATION": (2, 2),
            "NEW_CHAT_BUTTON": (3, 3),
            "CHAT_NAME_INPUT": (4, 4),
            "ASPECT_RATIO_SELECTOR": (5, 5),
            "PROMPT_INPUT_AFTER_IMAGE": (6, 6),
        },
        {"TO_SAVE_OPTION": (7, 7)},
        {"CHECK_IMAGE_GENERATED": True, "GENERATION_WAIT": 10.0, "IMAGE_WAIT_INTERVAL": 1.0},
        log_file=object(),
    )

    assert ok is True
    assert any("Таймаут ожидания изображения" in line for line in log_lines)


def test_run_mode_continues_without_missing_references_and_prints_extended_progress(tmp_path, monkeypatch):
    log_path = tmp_path / "refs.log"
    update_calls = []
    results = iter([True, False])

    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs._get_log_filepath", lambda: str(log_path))
    monkeypatch.setattr("sites.aistudio.mode_multiformat_with_refs.time.sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "sites.aistudio.mode_multiformat_with_refs.check_all_references",
        lambda tasks: {
            "found_count": 1,
            "missing": [("оборот", 1, "Нефть", "оборот_1_Нефть.png/.jpg")],
        },
    )
    monkeypatch.setattr(
        "sites.aistudio.mode_multiformat_with_refs._generate_single_side_with_ref",
        lambda *args, **kwargs: next(results),
    )
    monkeypatch.setattr("utils.settings_store.update_start_card", lambda card_number: update_calls.append(card_number))

    tasks = [
        {"card_number": 1, "card_name": "Нефть", "pair_number": 1, "side": "лицо", "prompt_text": "A"},
        {"card_number": 1, "card_name": "Нефть", "pair_number": 1, "side": "оборот", "prompt_text": "B"},
    ]
    settings = {"START_FROM_CARD": 1, "END_CARD": 1}
    coordinates = {
        "PROMPT_INPUT": (1, 1),
        "IMAGE_LOCATION": (2, 2),
        "NEW_CHAT_BUTTON": (3, 3),
        "CHAT_NAME_INPUT": (4, 4),
        "ASPECT_RATIO_SELECTOR": (5, 5),
        "PROMPT_INPUT_AFTER_IMAGE": (6, 6),
    }
    relative_movements = {"TO_SAVE_OPTION": (7, 7)}

    output = io.StringIO()
    with redirect_stdout(output):
        mode_multiformat_with_refs.run_mode(tasks, settings, coordinates, relative_movements)

    rendered = output.getvalue()
    assert "[WARN] Отсутствуют референсы для 1 сторон:" in rendered
    assert "[INFO] Продолжаем генерацию без отсутствующих референсов" in rendered
    assert "Примерное время:" in rendered
    assert "Генерация 1/1 из 2 - " in rendered
    assert "Генерация 1/2 из 2 - " in rendered
    assert "Итоги генерации:" in rendered
    assert "Примерная стоимость:" not in rendered
    assert update_calls == [2]

