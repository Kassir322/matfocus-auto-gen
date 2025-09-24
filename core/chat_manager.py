"""
Управление чатами в AI Studio
"""
import time
import pyautogui
from config.coordinates import COORDINATES, DELAYS
from utils.clipboard import ClipboardManager
from utils.logger import Logger

class ChatManager:
    def __init__(self):
        self.clipboard = ClipboardManager()
        self.logger = Logger()
    
    def click_coordinate(self, coord_name, description=""):
        """Безопасный клик по координатам с логированием"""
        if coord_name not in COORDINATES:
            self.logger.log_action(f"ОШИБКА: Неизвестная координата {coord_name}")
            return False
        
        x, y = COORDINATES[coord_name]
        if x == 0 and y == 0:
            self.logger.log_action(f"ВНИМАНИЕ: Координаты {coord_name} не заданы!")
            return False
        
        self.logger.log_action(f"Клик {description}: {coord_name} ({x}, {y})")
        pyautogui.click(x, y)
        return True
    
    def create_new_chat_only(self):
        """Создание нового чата без переименования"""
        try:
            if not self.click_coordinate('NEW_CHAT_BUTTON', "создание нового чата"):
                return False
            time.sleep(DELAYS['NEW_CHAT_WAIT'])
            
            self.logger.log_action("✓ Создан новый чат")
            return True
            
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при создании нового чата: {e}")
            return False
    
    def rename_current_chat(self, chat_name):
        """Переименование текущего чата"""
        try:
            if not self.click_coordinate('CHAT_NAME_INPUT', "поле названия чата"):
                return False
            time.sleep(DELAYS['POPUP_OPEN_WAIT'])
            
            popup_x, popup_y = COORDINATES['CHAT_NAME_POPUP']
            if popup_x != 0 or popup_y != 0:
                if not self.click_coordinate('CHAT_NAME_POPUP', "поле ввода в попапе"):
                    return False
                time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            self.logger.log_action(f"Ввод названия чата: {chat_name}")
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            
            if not self.clipboard.safe_paste_text(chat_name):
                return False
            time.sleep(DELAYS['CHAT_RENAME_WAIT'])
            
            confirm_x, confirm_y = COORDINATES['CHAT_NAME_CONFIRM']
            if confirm_x != 0 or confirm_y != 0:
                if not self.click_coordinate('CHAT_NAME_CONFIRM', "подтверждение названия"):
                    return False
            else:
                pyautogui.press('enter')
            
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            self.logger.log_action(f"✓ Чат переименован в: {chat_name}")
            return True
            
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при переименовании чата: {e}")
            return False
    
    def create_new_chat(self, chat_name):
        """Создание нового чата с указанным названием (старый метод для совместимости)"""
        if self.create_new_chat_only():
            return self.rename_current_chat(chat_name)
        return False