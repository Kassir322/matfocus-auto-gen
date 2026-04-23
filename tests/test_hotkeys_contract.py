"""Focused checks for the active v2 hotkeys contract."""

from unittest.mock import Mock

from ui.hotkeys import HotkeyManager


def _noop():
    return None


def test_hotkey_registration_includes_active_v2_bindings(monkeypatch):
    """The hotkey manager should register only runtime v2 bindings."""
    registered = []

    def fake_add_hotkey(binding, callback):
        registered.append((binding, callback))

    manager = HotkeyManager(_noop, _noop, _noop, on_start_api=_noop)
    monkeypatch.setattr("keyboard.add_hotkey", fake_add_hotkey)

    manager.register_hotkeys()

    bindings = [binding for binding, _ in registered]
    assert "ctrl+shift+p" in bindings
    assert "ctrl+0" in bindings
    assert "ctrl+shift+v" in bindings
    assert "ctrl+shift+s" in bindings
    assert "ctrl+shift+a" in bindings
    assert "ctrl+esc" in bindings
    assert "esc" in bindings
    assert "ctrl+1" not in bindings
    assert "ctrl+3" not in bindings
    assert "ctrl+4" not in bindings
    assert "ctrl+5" not in bindings
    assert "ctrl+6" not in bindings
    assert "ctrl+7" not in bindings
    assert "ctrl+8" not in bindings
    assert "ctrl+9" not in bindings
    assert "ctrl+2" not in bindings
    assert "ctrl+shift+q" not in bindings


def test_hotkey_registration_skips_api_launcher_without_callback(monkeypatch):
    """Ctrl+Shift+A should not be registered when the API callback is absent."""
    registered = []

    def fake_add_hotkey(binding, callback):
        registered.append(binding)

    manager = HotkeyManager(_noop, _noop, _noop)
    monkeypatch.setattr("keyboard.add_hotkey", fake_add_hotkey)

    manager.register_hotkeys()

    assert "ctrl+shift+a" not in registered


def test_setup_and_generation_hotkeys_are_blocked_while_api_worker_runs(monkeypatch):
    """Foreground-affecting hotkeys should be ignored while an API worker runs."""
    on_setup_window = Mock()
    on_start_generation = Mock()
    on_start_api = Mock()
    manager = HotkeyManager(on_start_generation, on_setup_window, _noop, on_start_api=on_start_api)

    monkeypatch.setattr("utils.process_control.get_current_worker_type", lambda: "api")

    manager._wrapped_on_setup_window()
    manager._wrapped_on_start_generation()
    manager._wrapped_on_start_api()

    on_setup_window.assert_not_called()
    on_start_generation.assert_not_called()
    on_start_api.assert_not_called()


def test_ctrl_esc_kills_console_via_sigint(monkeypatch):
    """Ctrl+Esc should signal the current console process with SIGINT."""
    kill = Mock()
    monkeypatch.setattr("os.kill", kill)
    monkeypatch.setattr("os.getpid", lambda: 4321)

    manager = HotkeyManager(_noop, _noop, _noop)
    manager.kill_console()

    kill.assert_called_once()
    pid, sig = kill.call_args.args
    assert pid == 4321
    assert getattr(sig, "name", None) == "SIGINT"
