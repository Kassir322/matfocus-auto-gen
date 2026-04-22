"""
Console helpers for the active v2 runtime.

This module is intentionally narrow: it only prints the current hotkey/help
text used by `main.py`. Runtime state, settings inspection, and prompt-plan
logic live elsewhere in v2 (`ui.console_menu`, `utils.settings_store`,
`utils.coordinates_store`).
"""


class ConsoleInterface:
    """Thin v2 console wrapper used by the active runtime entrypoint."""

    def show_welcome_screen(self):
        """Print a short banner for manual runs."""
        print("=" * 80)
        print("АВТОМАТИЗАЦИЯ AI STUDIO - ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ (Windows)")
        print("=" * 80)

    def show_instructions(self):
        """Print the current v2 hotkeys and startup notes."""
        print("Горячие клавиши (v2):")
        print("  Ctrl+Shift+P - получить координаты курсора (или сохранить после Ctrl+0)")
        print("  Ctrl+0 - меню настройки координат")
        print("  Ctrl+1 - настроить START_FROM_CARD")
        print("  Ctrl+3 - настроить GENERATION_WAIT")
        print("  Ctrl+4 - переключить CHECK_IMAGE_GENERATED")
        print("  Ctrl+5 - показать текущие настройки и план")
        print("  Ctrl+6 - настроить END_CARD")
        print("  Ctrl+7 - выбрать метод генерации (browser/api) и режим")
        print("  Ctrl+8 - настроить IMAGE_WAIT_INTERVAL")
        print("  Ctrl+9 - настроить FACE_ASPECT_RATIO и BACK_ASPECT_RATIO")
        print("  Ctrl+Shift+V - настройка рабочего окна браузера")
        print("  Ctrl+Shift+S - старт генерации (браузер)")
        print("  Ctrl+Shift+A - старт генерации (API в фоне)")
        print("  Ctrl+Esc - убить консоль (аналог Ctrl+C)")
        print("  Esc - экстренная остановка подпроцесса (только браузер)")
        print("-" * 80)
        print("Настройки: data/settings.json. Координаты: data/coordinates.json")
        print("-" * 80)
        print("ИНСТРУКЦИЯ:")
        print("  Browser режим (через браузер):")
        print("    1. Настройте рабочее окно (Ctrl+Shift+V)")
        print("    2. Настройте координаты (Ctrl+0, затем Ctrl+Shift+P)")
        print("    3. Выберите метод browser в Ctrl+7")
        print("  API режим (через Gemini API):")
        print("    1. Нажмите Ctrl+7, выберите api")
        print("    2. Введите API ключ (получить на https://aistudio.google.com/apikey)")
        print("  Общие шаги:")
        print("    3. Настройте параметры (Ctrl+1, 3, 4, 6, 7, 8, 9)")
        print("    4. Проверьте настройки и план (Ctrl+5)")
        print("    5. Браузер: Ctrl+Shift+S. API: Ctrl+Shift+A")
        print("=" * 80)
