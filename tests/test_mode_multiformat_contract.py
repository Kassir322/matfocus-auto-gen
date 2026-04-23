"""Focused checks for the active multiformat-mode contract."""

import io
from contextlib import redirect_stdout

from sites.aistudio import mode_multiformat


def test_parse_multiformat_warns_on_invalid_name_conflicts_and_incomplete_pairs(tmp_path):
    """Parser should warn on invalid lines, conflicting names, and incomplete pairs."""
    prompts_file = tmp_path / "multiformat_prompts.txt"
    prompts_file.write_text(
        "\n".join(
            [
                "Карточка 2 лицо Нефть - Промпт 1: Front prompt",
                "Карточка 2 оборот ДругоеНазвание - Промпт 1: Back prompt",
                "Карточка 3 лицо Балтийское море - Промпт 1: Only front",
                "invalid line here",
            ]
        ),
        encoding="utf-8",
    )

    output = io.StringIO()
    with redirect_stdout(output):
        tasks = mode_multiformat.load_tasks_from_file(str(prompts_file))

    rendered = output.getvalue()
    assert any(task["card_number"] == 2 and task["side"] == "лицо" for task in tasks)
    assert any(task["card_number"] == 2 and task["side"] == "оборот" for task in tasks)
    assert any(task["card_number"] == 3 and task["side"] == "лицо" for task in tasks)
    assert "[WARN] Строка 2: название 'ДругоеНазвание' отличается от 'Нефть'" in rendered
    assert "[WARN] Карточка 3, пара 1: отсутствует оборотная сторона" in rendered
    assert "[WARN] Строка 4 не распознана: invalid line here" in rendered


def test_generate_single_side_logs_wait_timeout_warning(monkeypatch):
    """A timed-out image wait should be reflected in the multiformat log."""
    log_lines = []

    monkeypatch.setattr("sites.aistudio.mode_multiformat.write_log_line", lambda log_file, line: log_lines.append(line))
    monkeypatch.setattr("sites.aistudio.mode_multiformat.time.sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat.helpers.click_new_chat", lambda coords: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat.helpers.click_prompt_input", lambda coords: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat.helpers.paste_prompt_text", lambda prompt_text, delay=0.05: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat.helpers.rename_chat", lambda coords, new_name: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat.helpers.select_aspect_ratio", lambda coords, ratio_text: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat.helpers.start_generation", lambda: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat.helpers.wait_until_image_ready", lambda *args, **kwargs: False)
    monkeypatch.setattr("sites.aistudio.mode_multiformat.helpers.save_image", lambda coords, relative_movements, file_name: None)

    ok = mode_multiformat._generate_single_side(
        {
            "card_number": 9,
            "card_name": "Нефть",
            "pair_number": 2,
            "side": "оборот",
            "prompt_text": "Prompt",
        },
        "16:9",
        {
            "PROMPT_INPUT": (1, 1),
            "IMAGE_LOCATION": (2, 2),
            "NEW_CHAT_BUTTON": (3, 3),
            "CHAT_NAME_INPUT": (4, 4),
            "ASPECT_RATIO_SELECTOR": (5, 5),
        },
        {"TO_SAVE_OPTION": (6, 6)},
        {"CHECK_IMAGE_GENERATED": True, "GENERATION_WAIT": 10.0, "IMAGE_WAIT_INTERVAL": 1.0},
        log_file=object(),
    )

    assert ok is True
    assert any("Таймаут ожидания изображения: карточка 9, пара 2, сторона оборот" in line for line in log_lines)


def test_run_mode_prints_success_attempt_and_total_progress(tmp_path, monkeypatch):
    """Console progress should expose successes, attempts, and total planned images."""
    log_path = tmp_path / "multiformat.log"
    update_calls = []
    results = iter([True, False])

    monkeypatch.setattr("sites.aistudio.mode_multiformat._get_log_filepath", lambda: str(log_path))
    monkeypatch.setattr("sites.aistudio.mode_multiformat.time.sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("sites.aistudio.mode_multiformat._generate_single_side", lambda *args, **kwargs: next(results))
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
    }
    relative_movements = {"TO_SAVE_OPTION": (6, 6)}

    output = io.StringIO()
    with redirect_stdout(output):
        mode_multiformat.run_mode(tasks, settings, coordinates, relative_movements)

    rendered = output.getvalue()
    assert "Генерация 1/1 из 2" in rendered
    assert "Генерация 1/2 из 2" in rendered
    assert update_calls == [2]
