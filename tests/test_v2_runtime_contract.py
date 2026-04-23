"""Focused checks for the active v2 runtime contract."""

from contextlib import redirect_stdout
import inspect
import io
import builtins
from unittest.mock import Mock

import main
from ui import console_menu
from ui.console import ConsoleInterface
from ui.hotkeys import HotkeyManager
import utils
from utils import process_control
from utils import process_manager


def test_main_uses_v2_runtime_contract():
    """`main.py` should depend on v2 runtime pieces, not the legacy manager layer."""
    source = inspect.getsource(main)

    assert "from utils import process_control" in source
    assert "from utils.generation_runner import" in source
    assert "from utils.process_manager import" not in source
    assert "from utils import process_manager" not in source
    assert "from config.settings import SettingsManager" not in source
    assert "SettingsManager(" not in source


def test_console_interface_is_instruction_only():
    """`ConsoleInterface` should remain a thin help printer."""
    console = ConsoleInterface()
    output = io.StringIO()

    with redirect_stdout(output):
        console.show_instructions()

    rendered = output.getvalue()
    assert "Ctrl+Shift+S" in rendered
    assert "Ctrl+7" in rendered
    assert not hasattr(console, "show_current_settings")


def test_hotkey_manager_constructor_stays_callback_based():
    """Hotkeys in v2 should be wired through callbacks, not manager objects."""

    def noop():
        return None

    hotkeys = HotkeyManager(noop, noop, noop)

    assert hotkeys.on_start_generation is noop
    assert hotkeys.on_setup_window is noop
    assert hotkeys.on_show_plan is noop
    assert hasattr(hotkeys, "register_hotkeys")


def test_legacy_process_manager_is_marked_as_legacy():
    """The old process manager should stay available only as a documented shim."""
    module_doc = process_manager.__doc__ or ""
    class_doc = process_manager.ProcessManager.__doc__ or ""

    assert "legacy" in module_doc.lower()
    assert "legacy" in class_doc.lower()


def test_utils_package_exports_only_active_helpers():
    """The legacy process manager should not be advertised by the package root."""
    assert "ProcessManager" not in getattr(utils, "__all__", [])


def test_console_menu_starts_browser_worker_with_explicit_type(monkeypatch):
    """Console-menu browser launches should mark the worker type explicitly."""
    settings = {
        "CURRENT_SITE": "aistudio",
        "CURRENT_MODE": "standard",
        "PROMPTS_FILE": "data/prompts.txt",
        "START_FROM_CARD": 1,
        "END_CARD": 1,
    }
    coordinates = {"PROMPT_INPUT": (1, 1)}
    relative_movements = {"TO_SAVE_OPTION": (0, 1)}
    start_worker = Mock()

    monkeypatch.setattr(builtins, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr("utils.process_control.start_worker", start_worker)
    monkeypatch.setattr("utils.generation_runner.can_start_generation", lambda settings: (True, None))
    monkeypatch.setattr("utils.generation_runner.run_standard_worker", "standard-worker")
    monkeypatch.setattr(
        "sites.aistudio.mode_standard.load_tasks_from_file",
        lambda path: [{"card_number": 1}],
    )
    monkeypatch.setattr(
        "sites.aistudio.mode_standard.get_plan_info",
        lambda tasks: {"cards_count": 1, "generations_count": 1, "images_planned": 1},
    )

    console_menu.start_generation_with_process(settings, coordinates, relative_movements)

    start_worker.assert_called_once_with(
        "standard-worker",
        (settings, coordinates, relative_movements),
        worker_type="browser",
    )


def test_hotkey_esc_ignores_api_worker(monkeypatch):
    """Esc should not stop the worker while the API worker is active."""

    def noop():
        return None

    hotkeys = HotkeyManager(noop, noop, noop)
    stop_worker = Mock()

    monkeypatch.setattr("utils.process_control.get_current_worker_type", lambda: "api")
    monkeypatch.setattr("utils.process_control.stop_worker", stop_worker)

    hotkeys.on_esc_stop_worker()

    stop_worker.assert_not_called()


def test_hotkey_esc_stops_browser_worker(monkeypatch):
    """Esc should stop the browser worker through process_control."""

    def noop():
        return None

    hotkeys = HotkeyManager(noop, noop, noop)
    stop_worker = Mock()

    monkeypatch.setattr("utils.process_control.get_current_worker_type", lambda: "browser")
    monkeypatch.setattr("utils.process_control.stop_worker", stop_worker)

    hotkeys.on_esc_stop_worker()

    stop_worker.assert_called_once_with()


class _FakeProcess:
    """Simple in-memory Process stub for process-control tests."""

    next_pid = 1000

    def __init__(self, target=None, args=()):
        self.target = target
        self.args = args
        self.alive = False
        self.pid = _FakeProcess.next_pid
        _FakeProcess.next_pid += 1
        self.terminate_called = False
        self.kill_called = False
        self.join_calls = []

    def start(self):
        self.alive = True

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminate_called = True
        self.alive = False

    def kill(self):
        self.kill_called = True
        self.alive = False

    def join(self, timeout=None):
        self.join_calls.append(timeout)


def test_process_control_blocks_second_start_while_worker_alive(monkeypatch):
    """start_worker should refuse a second launch while the current worker lives."""
    monkeypatch.setattr(process_control, "Process", _FakeProcess)
    monkeypatch.setattr(process_control, "_current_worker", None)
    monkeypatch.setattr(process_control, "_current_worker_type", None)

    first = process_control.start_worker(lambda: None, worker_type="browser")
    second = process_control.start_worker(lambda: None, worker_type="browser")

    assert first is not None
    assert second is None
    assert process_control.get_current_worker() is first
    assert process_control.get_current_worker_type() == "browser"

    process_control.stop_worker(first)


def test_process_control_stop_clears_current_worker_and_type(monkeypatch):
    """stop_worker should clear the tracked worker and its type after shutdown."""
    monkeypatch.setattr(process_control, "Process", _FakeProcess)
    monkeypatch.setattr(process_control, "_current_worker", None)
    monkeypatch.setattr(process_control, "_current_worker_type", None)

    worker = process_control.start_worker(lambda: None, worker_type="api")

    assert worker is not None
    assert process_control.get_current_worker_type() == "api"

    process_control.stop_worker()

    assert worker.terminate_called is True
    assert process_control.get_current_worker() is None
    assert process_control.get_current_worker_type() is None
