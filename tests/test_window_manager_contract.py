"""Focused checks for the active v2 window-manager contract."""

from utils.window_manager import WindowManager


class _FakeWindow:
    def __init__(self, title, minimized=False):
        self.title = title
        self.isMinimized = minimized
        self.size = (0, 0)
        self.topleft = (0, 0)
        self.restore_called = False
        self.activate_called = False
        self.resize_calls = []
        self.move_calls = []

    def restore(self):
        self.restore_called = True
        self.isMinimized = False

    def activate(self):
        self.activate_called = True

    def resizeTo(self, width, height):
        self.size = (width, height)
        self.resize_calls.append((width, height))

    def moveTo(self, x, y):
        self.topleft = (x, y)
        self.move_calls.append((x, y))


def test_find_browser_window_prefers_non_minimized_match(monkeypatch):
    """find_browser_window should return a visible browser window when available."""
    visible = _FakeWindow("Google Chrome - AI Studio", minimized=False)
    minimized = _FakeWindow("Google Chrome - Other", minimized=True)
    manager = WindowManager()

    monkeypatch.setattr("pygetwindow.getAllWindows", lambda: [minimized, visible])

    found = manager.find_browser_window()

    assert found is visible


def test_find_browser_window_falls_back_to_minimized_match(monkeypatch):
    """A minimized browser window should still be usable when it is the only match."""
    minimized = _FakeWindow("Mozilla Firefox - Session", minimized=True)
    manager = WindowManager()

    monkeypatch.setattr("pygetwindow.getAllWindows", lambda: [minimized])

    found = manager.find_browser_window()

    assert found is minimized


def test_configure_window_restores_minimized_window(monkeypatch):
    """configure_window should restore minimized windows before activating them."""
    manager = WindowManager()
    window = _FakeWindow("Microsoft Edge", minimized=True)

    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)

    ok = manager.configure_window(window)

    assert ok is True
    assert window.restore_called is True
    assert window.activate_called is True
    assert window.size == (manager.window_width, manager.window_height)
    assert window.topleft == (manager.window_x, manager.window_y)


def test_quick_setup_window_configures_existing_window(monkeypatch):
    """quick_setup_window should only configure an already found browser window."""
    manager = WindowManager()
    window = _FakeWindow("Google Chrome")

    monkeypatch.setattr(manager, "find_browser_window", lambda: window)
    monkeypatch.setattr(manager, "configure_window", lambda candidate: candidate is window)

    assert manager.quick_setup_window() is True


def test_setup_automation_window_creates_and_configures_new_window(monkeypatch):
    """Full setup should create a new browser window when none exists yet."""
    manager = WindowManager()
    created_window = _FakeWindow("Google Chrome")
    state = {"calls": 0}

    def fake_find_browser_window():
        state["calls"] += 1
        if state["calls"] == 1:
            return None
        return created_window

    monkeypatch.setattr(manager, "find_browser_window", fake_find_browser_window)
    monkeypatch.setattr(manager, "create_automation_window", lambda: True)
    monkeypatch.setattr(manager, "configure_window", lambda candidate: candidate is created_window)
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)

    assert manager.setup_automation_window() is True
