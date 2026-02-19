"""
Главная точка входа в программу автоматизации AI Studio
"""
import time

from ui.console import ConsoleInterface
from ui.hotkeys import HotkeyManager
from utils import process_control
from utils.coordinates_store import load_coordinates
from utils.generation_runner import (
    can_start_generation,
    run_standard_worker,
    run_multiformat_worker,
    run_multiformat_with_refs_worker,
)
from utils.settings_store import load_settings
from utils.window_manager import WindowManager


def main():
    """Главная функция (v2 hotkeys: callback'и, без SettingsManager/ProcessManager для хоткеев)."""
    print("Запуск AI Studio Automation (v2)...")

    def start_api_generation_from_settings(settings: dict) -> None:
        """Запуск API-воркера по настройкам (вызывается по Ctrl+Shift+A, чтобы не конкурировать с input() в меню настроек)."""
        site = settings.get("CURRENT_SITE")
        mode = settings.get("CURRENT_MODE")

        if site != "aistudio":
            print("Запуск генерации поддерживается только для сайта aistudio.")
            return
        if mode not in ("standard", "multiformat", "multiformat_with_refs"):
            print("Запуск генерации поддерживается только для режимов standard, multiformat и multiformat_with_refs.")
            return

        from utils.generation_runner import (
            can_start_generation_api,
            run_standard_worker_api,
            run_multiformat_worker_api,
            run_multiformat_with_refs_worker_api,
        )

        ok, err = can_start_generation_api(settings)
        if not ok:
            print(err)
            return

        if mode == "standard":
            worker = run_standard_worker_api
        elif mode == "multiformat":
            worker = run_multiformat_worker_api
        elif mode == "multiformat_with_refs":
            worker = run_multiformat_with_refs_worker_api
        else:
            print("Неизвестный режим. Выберите standard, multiformat или multiformat_with_refs.")
            return

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
            print("Запуск генерации поддерживается только для режимов standard, multiformat и multiformat_with_refs.")
            return

        # Выбор метода генерации: browser или api (API запускается по Ctrl+Shift+A, чтобы не занимать stdin)
        if generation_method == "api":
            print("Метод генерации: api. Для запуска API нажмите Ctrl+Shift+A.")
            return
        else:
            # Браузерная генерация (существующий код)
            coordinates, relative_movements = load_coordinates()

            ok, err = can_start_generation(settings)
            if not ok:
                print(err)
                return

            # Автоподготовка окна перед стартом (этап 5)
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
        """Запуск только API-воркера (Ctrl+Shift+A), без чтения stdin — меню настроек работают корректно."""
        settings = load_settings()
        if settings.get("GENERATION_METHOD") != "api":
            print("Сейчас выбран не метод 'api'. Нажмите Ctrl+7 и выберите api, затем Ctrl+Shift+A.")
            return
        start_api_generation_from_settings(settings)

    console = ConsoleInterface()
    console.show_instructions()

    hotkey_manager = HotkeyManager(
        on_start_generation, on_setup_window, on_show_plan, on_start_api=on_start_api
    )
    hotkey_manager.register_hotkeys()

    print(
        "Программа запущена. Горячие клавиши активны. "
        "Браузер: Ctrl+Shift+S. API: Ctrl+Shift+A (в API-режиме хоткеи отключены)."
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
