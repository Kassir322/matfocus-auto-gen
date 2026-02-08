"""
Управление горячими клавишами
"""
import keyboard
import pyautogui
import os
import signal
from config.coordinates import get_coordinates_manager

class HotkeyManager:
    def __init__(self, settings_manager, process_manager, console):
        self.settings_manager = settings_manager
        self.process_manager = process_manager
        self.console = console
        self.coordinates_manager = get_coordinates_manager()
        self.coordinate_capture_mode = False
        self.coordinate_to_set = None
        self.should_exit = False
    
    def get_mouse_position(self):
        """Получение координат курсора"""
        x, y = pyautogui.position()
        
        if self.coordinate_capture_mode and self.coordinate_to_set:
            self.coordinates_manager.update_coordinate(self.coordinate_to_set, x, y)
            self.coordinate_capture_mode = False
            self.coordinate_to_set = None
            print(f"Координата установлена и сохранена!")
        else:
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
        
        coord_descriptions = {
            'PROMPT_INPUT': 'Поле ввода промпта',
            'IMAGE_LOCATION': 'Место клика на сгенерированное изображение',
            'NEW_CHAT_BUTTON': 'Кнопка создания нового чата',
            'CHAT_NAME_INPUT': 'Поле ввода названия чата',
            'CHAT_NAME_POPUP': 'Поле ввода в попапе (если есть)',
            'CHAT_NAME_CONFIRM': 'Кнопка подтверждения в попапе (если есть)',
            'ASPECT_RATIO_SELECTOR': 'Выпадающий список выбора соотношения сторон',
            'PROMPT_INPUT_AFTER_IMAGE': 'Поле ввода промпта после вставки изображения',
            'TO_SAVE_OPTION': 'Относительное движение к пункту "сохранить изображение"'
        }
        
        for i, coord_name in enumerate(all_coords, 1):
            description = coord_descriptions.get(coord_name, '')
            status = "не задана" if self.coordinates_manager.get_coordinate(coord_name) == (0, 0) else "задана"
            print(f"  {i}. {coord_name} - {description} [{status}]")
        
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
                description = coord_descriptions.get(coord_name, '')
                print(f"\nВыбрана координата: {coord_name}")
                print(f"Описание: {description}")
                print("Наведите курсор на нужный элемент и нажмите Ctrl+Shift+P")
                self.coordinate_capture_mode = True
                self.coordinate_to_set = coord_name
            else:
                print("Неверный номер!")
        except ValueError:
            print("Введите число!")
        except KeyboardInterrupt:
            print("\nНастройка отменена")
    
    def kill_console(self):
        """Убить консоль (эмуляция Ctrl+C)"""
        os.kill(os.getpid(), signal.SIGINT)
    
    def exit_program(self):
        """Выход из программы"""
        print("\nПолучен сигнал выхода (Esc)")
        if self.process_manager.automation_process and self.process_manager.automation_process.is_alive():
            print("Остановка автоматизации...")
            self.process_manager.stop_automation()
        self.should_exit = True
    
    def register_hotkeys(self):
        """Регистрация всех горячих клавиш"""
        keyboard.add_hotkey('ctrl+shift+p', self.get_mouse_position)
        keyboard.add_hotkey('ctrl+0', self.show_coordinates_menu)
        keyboard.add_hotkey('ctrl+1', self.settings_manager.configure_start_card)
        keyboard.add_hotkey('ctrl+2', self.settings_manager.configure_generations_per_card)
        keyboard.add_hotkey('ctrl+3', self.settings_manager.configure_generation_wait)
        keyboard.add_hotkey('ctrl+4', self.settings_manager.toggle_image_check)
        keyboard.add_hotkey('ctrl+5', lambda: self.console.show_current_settings(self.settings_manager))
        keyboard.add_hotkey('ctrl+6', self.settings_manager.configure_end_card)
        keyboard.add_hotkey('ctrl+7', self.settings_manager.change_generation_mode)
        keyboard.add_hotkey('ctrl+8', self.settings_manager.configure_image_wait_time)
        keyboard.add_hotkey('ctrl+9', self.settings_manager.configure_aspect_ratios)
        keyboard.add_hotkey('ctrl+shift+v', self.process_manager.setup_window)
        keyboard.add_hotkey('ctrl+shift+s', lambda: self.process_manager.start_automation(self.settings_manager))
        keyboard.add_hotkey('ctrl+shift+q', self.process_manager.stop_automation)
        keyboard.add_hotkey('ctrl+esc', self.kill_console)
        keyboard.add_hotkey('esc', self.exit_program)
