"""
Управление буфером обмена
"""
import pyperclip
import pyautogui
import time
import os
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
    
    def copy_image_to_clipboard(self, image_path):
        """
        Копирование файла изображения в буфер обмена Windows
        
        Args:
            image_path: путь к файлу изображения
            
        Returns:
            bool: успешность операции
        """
        try:
            if not os.path.exists(image_path):
                self.logger.log_action(f"✗ Файл изображения не найден: {image_path}")
                return False
            
            # Используем PowerShell для копирования файла изображения в буфер обмена
            import subprocess
            
            # PowerShell команда для копирования изображения в буфер обмена
            # Абсолютный путь к файлу для надежности
            abs_path = os.path.abspath(image_path).replace('\\', '\\\\')
            
            ps_command = f'''
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            $image = [System.Drawing.Image]::FromFile("{abs_path}")
            $dataObject = New-Object System.Windows.Forms.DataObject
            $dataObject.SetImage($image)
            [System.Windows.Forms.Clipboard]::SetDataObject($dataObject, $true)
            '''
            
            # Запускаем PowerShell команду
            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.log_action(f"✓ Изображение скопировано в буфер обмена: {image_path}")
                return True
            else:
                self.logger.log_action(f"✗ ОШИБКА при копировании изображения через PowerShell: {result.stderr}")
                return False
                    
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при копировании изображения в буфер обмена: {e}")
            return False
    
    def paste_image_from_clipboard(self):
        """
        Вставка изображения из буфера обмена через Ctrl+V
        
        Returns:
            bool: успешность операции
        """
        try:
            self.logger.log_action("Вставка изображения из буфера обмена (Ctrl+V)")
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(DELAYS['AFTER_PASTE'])  # Даём больше времени на вставку изображения
            return True
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при вставке изображения: {e}")
            return False