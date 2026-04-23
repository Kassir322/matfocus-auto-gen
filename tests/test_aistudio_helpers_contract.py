"""Focused checks for the active AI Studio helpers contract."""

from sites.aistudio import helpers


def test_paste_prompt_text_restores_clipboard(monkeypatch):
    """Prompt pasting should restore the previous text clipboard contents afterwards."""
    clipboard = {"value": "original-text"}
    hotkeys = []

    monkeypatch.setattr("pyperclip.paste", lambda: clipboard["value"])
    monkeypatch.setattr("pyperclip.copy", lambda value: clipboard.__setitem__("value", value))
    monkeypatch.setattr(
        helpers,
        "press_keys",
        lambda *keys, delay=0.05: hotkeys.append((keys, delay, clipboard["value"])),
    )

    helpers.paste_prompt_text("new prompt", delay=0.2)

    assert hotkeys == [(("ctrl", "v"), 0.2, "new prompt")]
    assert clipboard["value"] == "original-text"


def test_save_image_restores_clipboard_and_uses_relative_save_offset(monkeypatch):
    """Image saving should use IMAGE_LOCATION + TO_SAVE_OPTION and restore clipboard text."""
    clipboard = {"value": "keep-me"}
    actions = []

    monkeypatch.setattr("pyperclip.paste", lambda: clipboard["value"])
    monkeypatch.setattr("pyperclip.copy", lambda value: clipboard.__setitem__("value", value))
    monkeypatch.setattr("pyautogui.rightClick", lambda x, y: actions.append(("rightClick", x, y)))
    monkeypatch.setattr("pyautogui.move", lambda dx, dy: actions.append(("move", dx, dy)))
    monkeypatch.setattr("pyautogui.click", lambda: actions.append(("click",)))
    monkeypatch.setattr("time.sleep", lambda seconds: actions.append(("sleep", seconds)))
    monkeypatch.setattr(
        helpers,
        "press_keys",
        lambda *keys, delay=0.05: actions.append(("hotkey", keys, delay, clipboard["value"])),
    )

    helpers.save_image(
        {"IMAGE_LOCATION": (100, 200)},
        {"TO_SAVE_OPTION": (30, 40)},
        "image_name.png",
    )

    assert actions[0] == ("rightClick", 100, 200)
    assert ("move", 30, 40) in actions
    assert ("hotkey", ("ctrl", "v"), 0.05, "image_name.png") in actions
    assert ("hotkey", ("enter",), 0.05, "image_name.png") in actions
    assert clipboard["value"] == "keep-me"


def test_wait_until_image_ready_returns_true_when_threshold_reached(monkeypatch):
    """Image readiness should return True once the difference threshold is reached."""
    screenshots = ["baseline", "same", "changed"]
    scores = {"same": 0.01, "changed": 0.2}
    current_time = {"value": 0.0}

    monkeypatch.setattr(helpers, "grab_result_area", lambda coords, box_size: screenshots.pop(0))
    monkeypatch.setattr(
        helpers,
        "compute_difference_score",
        lambda base, current: scores[current],
    )
    monkeypatch.setattr("time.sleep", lambda seconds: current_time.__setitem__("value", current_time["value"] + seconds))
    monkeypatch.setattr("time.time", lambda: current_time["value"])

    ready = helpers.wait_until_image_ready({}, 10.0, 2.0, (100, 100), 0.1)

    assert ready is True


def test_wait_until_image_ready_returns_false_on_timeout(monkeypatch):
    """Image readiness should return False when the threshold is never reached before timeout."""
    current_time = {"value": 0.0}

    monkeypatch.setattr(helpers, "grab_result_area", lambda coords, box_size: "baseline")
    monkeypatch.setattr(helpers, "compute_difference_score", lambda base, current: 0.01)
    monkeypatch.setattr("time.sleep", lambda seconds: current_time.__setitem__("value", current_time["value"] + seconds))
    monkeypatch.setattr("time.time", lambda: current_time["value"])

    ready = helpers.wait_until_image_ready({}, 5.0, 2.0, (100, 100), 0.1)

    assert ready is False
