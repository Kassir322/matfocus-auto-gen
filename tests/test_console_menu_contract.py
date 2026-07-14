"""Focused checks for the active v2 console-menu contract."""

import builtins
import io
from contextlib import redirect_stdout
from unittest.mock import Mock

import pytest

from ui import console_menu


def test_show_main_menu_stops_active_worker_before_exit(monkeypatch):
    """Menu exit should stop a running worker before leaving the loop."""
    settings = {"CURRENT_SITE": "aistudio", "CURRENT_MODE": "standard", "PROMPTS_FILE": "data/prompts.txt"}
    worker = Mock()
    worker.is_alive.return_value = True
    stop_worker = Mock()
    save_settings = Mock()

    monkeypatch.setattr(builtins, "input", lambda prompt="": "0")
    monkeypatch.setattr(console_menu, "show_current_config", lambda settings: None)
    monkeypatch.setattr("utils.process_control.get_current_worker", lambda: worker)
    monkeypatch.setattr("utils.process_control.stop_worker", stop_worker)
    monkeypatch.setattr("utils.settings_store.save_settings", save_settings)

    output = io.StringIO()
    with redirect_stdout(output):
        console_menu.show_main_menu(settings, {}, {})

    stop_worker.assert_called_once_with(worker)
    save_settings.assert_called_once_with(settings)
    rendered = output.getvalue()
    assert "Перед выходом останавливаем активный воркер." in rendered
    assert "Выход." in rendered


def test_show_generation_plan_bubbles_expected_read_errors(monkeypatch):
    """Read/import problems should stay visible instead of being silently masked."""
    settings = {
        "CURRENT_SITE": "aistudio",
        "CURRENT_MODE": "standard",
        "PROMPTS_FILE": "data/missing.txt",
    }

    monkeypatch.setattr(
        "sites.aistudio.mode_standard.load_tasks_from_file",
        lambda path: (_ for _ in ()).throw(OSError("boom")),
    )

    with pytest.raises(OSError):
        console_menu.show_generation_plan(settings)


def test_show_generation_plan_does_not_mask_unexpected_runtime_errors(monkeypatch):
    """Unexpected bugs in plan generation should not be swallowed by a broad except."""
    settings = {
        "CURRENT_SITE": "aistudio",
        "CURRENT_MODE": "standard",
        "PROMPTS_FILE": "data/prompts.txt",
    }

    monkeypatch.setattr(
        "sites.aistudio.mode_standard.load_tasks_from_file",
        lambda path: [{"card_number": 1}],
    )
    monkeypatch.setattr(
        "sites.aistudio.mode_standard.get_plan_info",
        lambda tasks: (_ for _ in ()).throw(RuntimeError("unexpected")),
    )

    with pytest.raises(RuntimeError):
        console_menu.show_generation_plan(settings)


def test_show_main_menu_routes_into_files_section(monkeypatch):
    """Root CLI menu should route into the files section by numeric choice."""
    settings = {
        "CURRENT_SITE": "aistudio",
        "CURRENT_MODE": "standard",
        "PROMPTS_FILE": "data/prompts.txt",
        "START_FROM_CARD": 1,
        "END_CARD": 5,
    }
    calls = []

    answers = iter(["2", "0", "0"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(answers))
    monkeypatch.setattr(console_menu, "show_files_menu", lambda current_settings: calls.append(current_settings))
    monkeypatch.setattr(console_menu, "show_current_config", lambda current_settings: None)
    monkeypatch.setattr("utils.process_control.get_current_worker", lambda: None)
    monkeypatch.setattr("utils.settings_store.save_settings", lambda current_settings: None)

    console_menu.show_main_menu(settings, {}, {})

    assert calls == [settings]


def test_select_prompts_file_persists_choice_from_data_directory(monkeypatch):
    """Prompt file selection should persist a file chosen from data/."""
    settings = {"PROMPTS_FILE": "data/old.txt"}
    saved = []

    monkeypatch.setattr("os.path.isdir", lambda path: True)
    monkeypatch.setattr("os.listdir", lambda path: ["notes.md", "older.txt", "newer.txt"])
    monkeypatch.setattr("os.path.isfile", lambda path: True)
    monkeypatch.setattr(
        "os.path.getctime",
        lambda path: {
            str(console_menu.DATA_DIR / "older.txt"): 100.0,
            str(console_menu.DATA_DIR / "newer.txt"): 200.0,
        }[path],
    )
    monkeypatch.setattr(builtins, "input", lambda prompt="": "1")
    monkeypatch.setattr("utils.settings_store.save_settings", lambda current_settings: saved.append(dict(current_settings)))

    console_menu.select_prompts_file(settings)

    assert settings["PROMPTS_FILE"].endswith("data\\newer.txt")
    assert saved[-1]["PROMPTS_FILE"].endswith("data\\newer.txt")


def test_start_generation_from_menu_uses_api_worker_and_waits(monkeypatch):
    """When GENERATION_METHOD=api, --menu should not start the browser worker or keep reading stdin."""
    settings = {
        "CURRENT_SITE": "aistudio",
        "CURRENT_MODE": "standard",
        "GENERATION_METHOD": "api",
        "PROMPTS_FILE": "data/prompts.txt",
        "START_FROM_CARD": 1,
        "END_CARD": 1,
    }
    started = []
    waited = []
    fake_process = object()

    def fake_start_worker(worker, args, worker_type=None):
        started.append((worker, args, worker_type))
        return fake_process

    monkeypatch.setattr("utils.generation_runner.can_start_generation_api", lambda current_settings: (True, None))
    monkeypatch.setattr("utils.generation_runner.run_standard_worker_api", "api-worker")
    monkeypatch.setattr("utils.process_control.start_worker", fake_start_worker)
    monkeypatch.setattr("utils.process_control.wait_worker", lambda process: waited.append(process))
    monkeypatch.setattr(
        "sites.aistudio.mode_standard.load_tasks_from_file",
        lambda path: [{"card_number": 1, "generation_number": 1, "prompt_text": "A"}],
    )
    monkeypatch.setattr(
        "sites.aistudio.mode_standard.get_plan_info",
        lambda tasks: {"cards_count": 1, "generations_count": 1, "images_planned": 1},
    )

    console_menu.start_generation_with_process(settings, {}, {})

    assert started == [("api-worker", (settings,), "api")]
    assert waited == [fake_process]
