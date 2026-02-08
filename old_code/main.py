"""
Главная точка входа в программу автоматизации AI Studio
"""
import pyautogui
from ui.hotkeys import HotkeyManager
from ui.console import ConsoleInterface
from utils.process_manager import ProcessManager
from config.settings import SettingsManager
from tests import run_all_tests


def main():
    """Главная функция"""
    # Упрощённый запуск без проверки зависимостей
    print("🚀 Запуск AI Studio Automation...")
    
    # Инициализация компонентов
    settings_manager = SettingsManager()
    process_manager = ProcessManager()
    console = ConsoleInterface()
    hotkey_manager = HotkeyManager(settings_manager, process_manager, console)
    
    # Загрузка настроек
    settings_manager.load_settings()
    
    # Показ инструкций
    console.show_instructions()
    
    # Регистрация горячих клавиш
    hotkey_manager.register_hotkeys()
    
    print("Программа запущена! Используйте горячие клавиши для управления.")
    print("Нажмите Esc для выхода...")
    
    try:
        # Основной цикл программы
        while True:
            # Проверяем флаг завершения
            if hotkey_manager.should_exit:
                print("👋 Программа завершена")
                # Ждём нажатия Enter перед закрытием консоли
                input("Нажмите Enter для выхода...")
                break
            
            import time
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nПрограмма завершена пользователем")
        # Ждём нажатия Enter перед закрытием консоли
        input("Нажмите Enter для выхода...")
    except Exception as e:
        print(f"\nОшибка в главном цикле: {e}")
        # Ждём нажатия Enter перед закрытием консоли
        input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()
