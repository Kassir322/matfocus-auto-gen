"""
Small Windows console safeguards for long-running automation.
"""
import os


def disable_quick_edit_mode() -> bool:
    """
    Disable Windows console QuickEdit mode when possible.

    QuickEdit selection pauses console output until Enter/Esc. During generation
    that can look like the whole program is stuck even though the worker is only
    blocked on print().
    """
    if os.name != "nt":
        return False

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        stdin_handle = kernel32.GetStdHandle(-10)
        if stdin_handle in (0, -1):
            return False

        mode = ctypes.c_uint()
        if not kernel32.GetConsoleMode(stdin_handle, ctypes.byref(mode)):
            return False

        enable_quick_edit = 0x0040
        enable_extended_flags = 0x0080
        new_mode = (mode.value | enable_extended_flags) & ~enable_quick_edit
        return bool(kernel32.SetConsoleMode(stdin_handle, new_mode))
    except Exception:
        return False
