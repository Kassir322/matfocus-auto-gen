"""
Управление буфером обмена
"""
import pyperclip
import pyautogui
import time
from config.coordinates import DELAYS
from .logger import Logger

class ClipboardManager:
    def __init__(self):
        self.logger = Logger()
    
    def get_clipboard_content(self):
        """Получение содержимого буфера обмена"""
        try:
            return pyperclip.paste()
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при получении содержимого буфера: {e}")
            return ""
    
    def copy_to_clipboard(self, text):
        """Копирование текста в буфер обмена"""
        try:
            pyperclip.copy(text)
            self.logger.log_action(f"Скопировано в буфер: {text}")
            return True
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при копировании в буфер: {e}")
            return False
    
    def restore_clipboard(self, original_content):
        """Восстановление оригинального содержимого буфера"""
        try:
            pyperclip.copy(original_content)
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при восстановлении буфера: {e}")
    
    def safe_paste_text(self, text):
        """Безопасная вставка текста через буфер обмена с сохранением предыдущего содержимого"""
        try:
            original_clipboard = self.get_clipboard_content()
            
            if not self.copy_to_clipboard(text):
                return False
                
            self.logger.log_action(f"Подготовлен для вставки: {text}")
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            self.restore_clipboard(original_clipboard)
            return True
            
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при вставке текста: {e}")
            return False