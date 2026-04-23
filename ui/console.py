"""
Console helpers for the active v2 runtime.

This module stays intentionally narrow: it only prints the current help text
used by `main.py`.
"""


class ConsoleInterface:
    """Thin v2 console wrapper used by the active runtime entrypoint."""

    def show_welcome_screen(self):
        """Print a short banner for manual runs."""
        print("=" * 80)
        print("АВТОМАТИЗАЦИЯ AI STUDIO - ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ (Windows)")
        print("=" * 80)

    def show_instructions(self):
        """Print the current v2 runtime hotkeys and CLI menu entrypoint."""
        print("Горячие клавиши runtime (v2):")
        print("  Ctrl+Shift+P - получить координаты курсора (или сохранить после Ctrl+0)")
        print("  Ctrl+0 - меню настройки координат")
        print("  Ctrl+Shift+V - настройка рабочего окна браузера")
        print("  Ctrl+Shift+S - старт генерации (браузер)")
        print("  Ctrl+Shift+A - старт генерации (API в фоне)")
        print("  Ctrl+Esc - убить консоль (аналог Ctrl+C)")
        print("  Esc - экстренная остановка подпроцесса (только браузер)")
        print("-" * 80)
        print("Настройки через CLI: python main.py --menu")
        print("Координаты: data/coordinates.json")
        print("-" * 80)
        print("Инструкция:")
        print("  1. Откройте CLI-меню: python main.py --menu")
        print("  2. Настройте все рабочие параметры через разделы меню")
        print("  3. Для координат используйте Ctrl+0 и Ctrl+Shift+P")
        print("  4. Browser: Ctrl+Shift+S. API: Ctrl+Shift+A")
        print("=" * 80)
