"""Focused checks for the active v2 runtime contract."""

from contextlib import redirect_stdout
import inspect
import io

import main
from ui.console import ConsoleInterface
from ui.hotkeys import HotkeyManager
import utils
from utils import process_manager


def test_main_uses_v2_runtime_contract():
    """`main.py` should depend on v2 runtime pieces, not the legacy manager layer."""
    source = inspect.getsource(main)

    assert "from utils import process_control" in source
    assert "from utils.generation_runner import" in source
    assert "ProcessManager" not in source
    assert "SettingsManager" not in source


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
