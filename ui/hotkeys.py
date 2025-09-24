"""
Управление горячими клавишами
"""
import keyboard
import pyautogui
from config.coordinates import get_coordinates_manager

class HotkeyManager:
    def __init__(self, settings_manager, process_manager, console):
        self.settings_manager = settings_manager
        self.process_manager = process_manager
        self.console = console
        self.coordinates_manager = get_coordinates_manager()
        self.coordinate_capture_mode = False
        self.coordinate_to_set = None
    
    def get_mouse_position(self):
        """Получение координат курсора"""
        x, y = pyautogui.position()
        
        if self.coordinate_capture_mode and self.coordinate_to_set:
            # Режим захвата координаты для конкретного элемента
            self.coordinates_manager.update_coordinate(self.coordinate_to_set, x, y)
            self.coordinate_capture_mode = False
            self.coordinate_to_set = None
            print(f"✓ Координата установлена и сохранена!")
        else:
            # Обычный режим - просто показать координаты
            print(f"[КООРДИНАТЫ] Курсор: X={x}, Y={y}")
    
    def show_coordinates_menu(self):
        """Показать меню для настройки координат"""
        print("-" * 60)
        print("МЕНЮ НАСТРОЙКИ КООРДИНАТ")
        print("-" * 60)
        print(self.coordinates_manager.list_coordinates())
        print("-" * 60)
        print("Выберите координату для настройки:")
        
        all_coords = list(self.coordinates_manager.coordinates.keys()) + list(self.coordinates_manager.relative_movements.keys())
        for i, coord_name in enumerate(all_coords, 1):
            print(f"  {i}. {coord_name}")
        
        print("  0. Отмена")
        print("-" * 60)
        
        try:
            choice = input("Введите номер координаты: ").strip()
            if not choice or choice == '0':
                print("Настройка отменена")
                return
            
            choice = int(choice)
            if 1 <= choice <= len(all_coords):
                coord_name = all_coords[choice - 1]
                print(f"\nВыбрана координата: {coord_name}")
                print("Наведите курсор на нужный элемент и нажмите Ctrl+Shift+P")
                self.coordinate_capture_mode = True
                self.coordinate_to_set = coord_name
            else:
                print("Неверный номер!")
        except ValueError:
            print("Введите число!")
        except KeyboardInterrupt:
            print("\nНастройка отменена")
    
    def register_hotkeys(self):
        """Регистрация всех горячих клавиш"""
        keyboard.add_hotkey('ctrl+shift+p', self.get_mouse_position)
        keyboard.add_hotkey('ctrl+0', self.show_coordinates_menu)  # Новая горячая клавиша
        keyboard.add_hotkey('ctrl+1', self.settings_manager.configure_start_card)
        keyboard.add_hotkey('ctrl+2', self.settings_manager.configure_generations_per_card)
        keyboard.add_hotkey('ctrl+3', self.settings_manager.configure_generation_wait)
        keyboard.add_hotkey('ctrl+4', self.settings_manager.toggle_image_check)
        keyboard.add_hotkey('ctrl+5', lambda: self.console.show_current_settings(self.settings_manager))
        keyboard.add_hotkey('ctrl+6', self.settings_manager.configure_cards_limit)
        keyboard.add_hotkey('ctrl+shift+s', lambda: self.process_manager.start_automation(self.settings_manager))
        keyboard.add_hotkey('ctrl+shift+q', self.process_manager.stop_automation)