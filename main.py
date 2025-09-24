"""
Главная точка входа в программу автоматизации AI Studio
"""
import pyautogui
from ui.hotkeys import HotkeyManager
from ui.console import ConsoleInterface
from utils.process_manager import ProcessManager
from config.settings import SettingsManager

def check_dependencies():
    """Проверка зависимостей"""
    print("ПРОВЕРКА ЗАВИСИМОСТЕЙ:")
    try:
        import pyperclip
        print("✓ pyperclip установлен")
    except ImportError:
        print("❌ ОШИБКА: Установите pyperclip: pip install pyperclip")
        exit(1)

    try:
        from PIL import Image
        print("✓ Pillow установлен")
        return True
    except ImportError:
        print("⚠️ ВНИМАНИЕ: Pillow не установлен. Проверка изображений будет отключена.")
        print("   Для включения установите: pip install Pillow")
        return False

def main():
    """Главная функция"""
    pillow_available = check_dependencies()
    
    # Инициализация компонентов
    settings_manager = SettingsManager(pillow_available)
    process_manager = ProcessManager()
    console = ConsoleInterface()
    hotkey_manager = HotkeyManager(settings_manager, process_manager, console)
    
    # Загрузка настроек
    settings_manager.load_settings()
    
    # Отображение интерфейса
    console.show_welcome_screen()
    console.show_instructions()
    
    # Регистрация горячих клавиш
    hotkey_manager.register_hotkeys()
    
    try:
        print("[ГЛАВНЫЙ] Ожидание команд... (Esc для выхода)")
        import keyboard
        keyboard.wait('esc')
        
    except KeyboardInterrupt:
        print("\n[ГЛАВНЫЙ] Получен сигнал прерывания")
    
    finally:
        process_manager.stop_automation()
        print("[ГЛАВНЫЙ] Программа завершена")

if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    main()