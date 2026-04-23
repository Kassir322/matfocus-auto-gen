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


def test_show_generation_plan_handles_expected_read_errors(monkeypatch):
    """File/import/read problems should be turned into a user-facing message."""
    settings = {
        "CURRENT_SITE": "aistudio",
        "CURRENT_MODE": "standard",
        "PROMPTS_FILE": "data/missing.txt",
    }

    monkeypatch.setattr(
        "sites.aistudio.mode_standard.load_tasks_from_file",
        lambda path: (_ for _ in ()).throw(OSError("boom")),
    )

    output = io.StringIO()
    with redirect_stdout(output):
        console_menu.show_generation_plan(settings)

    assert "Ошибка при чтении файла или файл не найден." in output.getvalue()


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
