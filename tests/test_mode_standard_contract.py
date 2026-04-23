"""Focused checks for the active standard-mode contract."""

import io
from contextlib import redirect_stdout

from sites.aistudio import mode_standard


def test_load_tasks_from_file_warns_on_invalid_lines(tmp_path):
    prompts_file = tmp_path / "standard_prompts.txt"
    prompts_file.write_text(
        "\n".join(
            [
                "Карточка 2 - Промпт 1: Second card",
                "invalid line here",
                "Карточка 1 - Промпт 2: First card second prompt",
                "Карточка 1 - Промпт 1: First card first prompt",
            ]
        ),
        encoding="utf-8",
    )

    output = io.StringIO()
    with redirect_stdout(output):
        tasks = mode_standard.load_tasks_from_file(str(prompts_file))

    assert [task["card_number"] for task in tasks] == [1, 1, 2]
    assert [task["generation_number"] for task in tasks] == [1, 2, 1]
    assert "[WARN]" in output.getvalue()


def test_generate_single_image_logs_wait_timeout_warning(monkeypatch):
    log_lines = []

    monkeypatch.setattr("sites.aistudio.mode_standard.write_log_line", lambda log_file, line: log_lines.append(line))
    monkeypatch.setattr("sites.aistudio.mode_standard.time.sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("sites.aistudio.mode_standard.helpers.click_new_chat", lambda coords: None)
    monkeypatch.setattr("sites.aistudio.mode_standard.helpers.click_prompt_input", lambda coords: None)
    monkeypatch.setattr("sites.aistudio.mode_standard.helpers.paste_prompt_text", lambda prompt_text, delay=0.05: None)
    monkeypatch.setattr("sites.aistudio.mode_standard.helpers.rename_chat", lambda coords, new_name: None)
    monkeypatch.setattr("sites.aistudio.mode_standard.helpers.start_generation", lambda: None)
    monkeypatch.setattr("sites.aistudio.mode_standard.helpers.wait_until_image_ready", lambda *args, **kwargs: False)
    monkeypatch.setattr("sites.aistudio.mode_standard.helpers.save_image", lambda coords, relative_movements, file_name: None)

    ok = mode_standard._generate_single_image(
        {"card_number": 7, "generation_number": 2, "prompt_text": "Prompt"},
        {"PROMPT_INPUT": (1, 1), "IMAGE_LOCATION": (2, 2), "NEW_CHAT_BUTTON": (3, 3), "CHAT_NAME_INPUT": (4, 4)},
        {"TO_SAVE_OPTION": (5, 5)},
        {"CHECK_IMAGE_GENERATED": True, "GENERATION_WAIT": 10.0, "IMAGE_WAIT_INTERVAL": 1.0},
        log_file=object(),
    )

    assert ok is True
    assert any("Таймаут ожидания изображения" in line for line in log_lines)


def test_run_mode_prints_extended_progress_and_summary(tmp_path, monkeypatch):
    log_path = tmp_path / "standard.log"
    update_calls = []
    results = iter([True, False])

    monkeypatch.setattr("sites.aistudio.mode_standard._get_log_filepath", lambda: str(log_path))
    monkeypatch.setattr("sites.aistudio.mode_standard.time.sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("sites.aistudio.mode_standard._generate_single_image", lambda *args, **kwargs: next(results))
    monkeypatch.setattr("utils.settings_store.update_start_card", lambda card_number: update_calls.append(card_number))

    tasks = [
        {"card_number": 1, "generation_number": 1, "prompt_text": "A"},
        {"card_number": 1, "generation_number": 2, "prompt_text": "B"},
    ]
    settings = {"START_FROM_CARD": 1, "END_CARD": 1}
    coordinates = {"PROMPT_INPUT": (1, 1), "IMAGE_LOCATION": (2, 2), "NEW_CHAT_BUTTON": (3, 3), "CHAT_NAME_INPUT": (4, 4)}
    relative_movements = {"TO_SAVE_OPTION": (5, 5)}

    output = io.StringIO()
    with redirect_stdout(output):
        mode_standard.run_mode(tasks, settings, coordinates, relative_movements)

    rendered = output.getvalue()
    assert "Примерное время:" in rendered
    assert "Генерация 1/1 из 2 - " in rendered
    assert "avg " in rendered
    assert "fail 1" in rendered
    assert "Итоги генерации:" in rendered
    assert "Не удалось сгенерировать:" in rendered
    assert "Примерная стоимость:" not in rendered
    assert update_calls == [2]

