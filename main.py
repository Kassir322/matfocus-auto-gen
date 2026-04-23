"""
Главная точка входа в программу автоматизации AI Studio.
"""
import sys
import time

from ui.console import ConsoleInterface
from ui.hotkeys import HotkeyManager
from utils import process_control
from utils.coordinates_store import load_coordinates
from utils.generation_runner import (
    can_start_generation,
    run_multiformat_with_refs_worker,
    run_multiformat_worker,
    run_standard_worker,
)
from utils.settings_store import load_settings
from utils.window_manager import WindowManager


def main():
    """Главная функция активного v2 runtime."""
    print("Запуск AI Studio Automation (v2)...")

    if "--menu" in sys.argv:
        from ui.console_menu import show_main_menu

        settings = load_settings()
        coordinates, relative_movements = load_coordinates()
        show_main_menu(settings, coordinates, relative_movements)
        return

    def start_api_generation_from_settings(settings: dict) -> None:
        site = settings.get("CURRENT_SITE")
        mode = settings.get("CURRENT_MODE")

        if site != "aistudio":
            print("Запуск генерации поддерживается только для сайта aistudio.")
            return
        if mode not in ("standard", "multiformat", "multiformat_with_refs"):
            print(
                "Запуск генерации поддерживается только для режимов "
                "standard, multiformat и multiformat_with_refs."
            )
            return

        from utils.generation_runner import (
            can_start_generation_api,
            run_multiformat_with_refs_worker_api,
            run_multiformat_worker_api,
            run_standard_worker_api,
        )

        ok, err = can_start_generation_api(settings)
        if not ok:
            print(err)
            return

        if mode == "standard":
            worker = run_standard_worker_api
        elif mode == "multiformat":
            worker = run_multiformat_worker_api
        else:
            worker = run_multiformat_with_refs_worker_api

        process_control.start_worker(worker, (settings,), worker_type="api")

    def on_setup_window():
        wm = WindowManager()
        if wm.quick_setup_window():
            print("[ГЛАВНЫЙ] Рабочее окно настроено.")
        else:
            print("[ГЛАВНЫЙ] Не удалось настроить рабочее окно.")

    def on_show_plan(settings):
        from ui.console_menu import show_generation_plan

        show_generation_plan(settings)

    def on_start_generation():
        settings = load_settings()
        site = settings.get("CURRENT_SITE")
        mode = settings.get("CURRENT_MODE")
        generation_method = settings.get("GENERATION_METHOD", "browser")

        if site != "aistudio":
            print("Запуск генерации поддерживается только для сайта aistudio.")
            return
        if mode not in ("standard", "multiformat", "multiformat_with_refs"):
            print(
                "Запуск генерации поддерживается только для режимов "
                "standard, multiformat и multiformat_with_refs."
            )
            return

        if generation_method == "api":
            print("Метод генерации: api. Для запуска API нажмите Ctrl+Shift+A.")
            return

        coordinates, relative_movements = load_coordinates()
        ok, err = can_start_generation(settings)
        if not ok:
            print(err)
            return

        if not WindowManager().setup_automation_window():
            print("[ГЛАВНЫЙ] Не удалось настроить рабочее окно, но продолжаем.")

        if mode == "standard":
            worker = run_standard_worker
        elif mode == "multiformat":
            worker = run_multiformat_worker
        else:
            worker = run_multiformat_with_refs_worker

        process_control.start_worker(
            worker,
            (settings, coordinates, relative_movements),
            worker_type="browser",
        )

    def on_start_api():
        settings = load_settings()
        if settings.get("GENERATION_METHOD") != "api":
            print("Сейчас выбран не метод 'api'. Откройте CLI-меню или настройте метод заранее.")
            return
        start_api_generation_from_settings(settings)

    console = ConsoleInterface()
    console.show_instructions()

    hotkey_manager = HotkeyManager(
        on_start_generation,
        on_setup_window,
        on_show_plan,
        on_start_api=on_start_api,
    )
    hotkey_manager.register_hotkeys()

    print(
        "Программа запущена. Горячие клавиши активны. "
        "CLI-меню: python main.py --menu. "
        "Браузер: Ctrl+Shift+S. API: Ctrl+Shift+A."
    )

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nПрограмма завершена пользователем")
        input("Нажмите Enter для выхода...")
    except Exception as e:
        print(f"\nОшибка в главном цикле: {e}")
        input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()
