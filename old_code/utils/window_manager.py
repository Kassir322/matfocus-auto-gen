"""
Управление окнами для автоматизации
"""
import time
import pyautogui
import subprocess
import os
import pygetwindow as gw
from utils.logger import Logger

class WindowManager:
    def __init__(self):
        self.logger = Logger()
        self.window_title = "AI Studio Automation Window"
        self.window_width = 1200
        self.window_height = 1000
        self.window_x = 0
        self.window_y = 0
    
    def create_automation_window(self):
        """Создание рабочего окна для автоматизации."""
        try:
            self.logger.log_action("Создание рабочего окна для автоматизации...")
            browsers = self._find_available_browsers()
            if not browsers:
                self.logger.log_action("Не найдено доступных браузеров!")
                return False
            browser_path = browsers[0]
            browser_name = os.path.basename(browser_path)
            self.logger.log_action(f"Используем браузер: {browser_name}")
            if "chrome" in browser_name.lower():
                success = self._create_chrome_window()
            elif "firefox" in browser_name.lower():
                success = self._create_firefox_window()
            elif "edge" in browser_name.lower():
                success = self._create_edge_window()
            else:
                success = self._create_generic_window(browser_path)
            if success:
                self.logger.log_action("Рабочее окно создано успешно!")
            else:
                self.logger.log_action("Не удалось создать рабочее окно")
            return success
        except Exception as e:
            self.logger.log_action(f"ОШИБКА при создании окна: {e}")
            return False
    
    def _find_available_browsers(self):
        browsers = []
        browser_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]
        for path in browser_paths:
            if os.path.exists(path):
                browsers.append(path)
        return browsers
    
    def _create_chrome_window(self):
        try:
            chrome_args = ["--new-window", "--window-size=1200,1000", "--window-position=0,0", "about:blank"]
            subprocess.Popen([r"C:\Program Files\Google\Chrome\Application\chrome.exe", *chrome_args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
            return self._verify_window_created()
        except Exception as e:
            self.logger.log_action(f"Ошибка создания Chrome окна: {e}")
            return False
    
    def _create_firefox_window(self):
        try:
            firefox_args = ["-new-window", "-width", "1200", "-height", "1000", "about:blank"]
            subprocess.Popen([r"C:\Program Files\Mozilla Firefox\firefox.exe", *firefox_args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
            return self._verify_window_created()
        except Exception as e:
            self.logger.log_action(f"Ошибка создания Firefox окна: {e}")
            return False
    
    def _create_edge_window(self):
        try:
            edge_args = ["--new-window", "--window-size=1200,1000", "--window-position=0,0", "about:blank"]
            subprocess.Popen([r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", *edge_args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
            return self._verify_window_created()
        except Exception as e:
            self.logger.log_action(f"Ошибка создания Edge окна: {e}")
            return False
    
    def _create_generic_window(self, browser_path):
        try:
            subprocess.Popen([browser_path, "--new-window", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
            return self._verify_window_created()
        except Exception as e:
            self.logger.log_action(f"Ошибка создания окна браузера: {e}")
            return False
    
    def _verify_window_created(self):
        try:
            time.sleep(2)
            current_pos = pyautogui.position()
            pyautogui.moveTo(current_pos.x + 1, current_pos.y + 1)
            pyautogui.moveTo(current_pos.x, current_pos.y)
            self.logger.log_action("Окно браузера создано и активно")
            return True
        except Exception as e:
            self.logger.log_action(f"Ошибка проверки окна: {e}")
            return False
    
    def find_browser_window(self):
        try:
            browser_titles = ['Google Chrome', 'Mozilla Firefox', 'Microsoft Edge', 'Chrome', 'Firefox', 'Edge']
            all_windows = gw.getAllWindows()
            for window in all_windows:
                if window.title and any(browser in window.title for browser in browser_titles):
                    if not window.isMinimized:
                        self.logger.log_action(f"Найдено окно браузера: {window.title}")
                        return window
            self.logger.log_action("Окно браузера не найдено")
            return None
        except Exception as e:
            self.logger.log_action(f"ОШИБКА при поиске окна браузера: {e}")
            return None
    
    def configure_window(self, window):
        try:
            self.logger.log_action("Настройка окна браузера...")
            window.activate()
            time.sleep(0.5)
            window.resizeTo(self.window_width, self.window_height)
            time.sleep(0.5)
            window.moveTo(self.window_x, self.window_y)
            time.sleep(0.5)
            self.logger.log_action(f"Окно настроено: размер {window.size}, позиция {window.topleft}")
            return True
        except Exception as e:
            self.logger.log_action(f"ОШИБКА при настройке окна: {e}")
            return False
    
    def setup_automation_window(self):
        try:
            self.logger.log_action("=== НАСТРОЙКА РАБОЧЕГО ОКНА ===")
            browser_window = self.find_browser_window()
            if browser_window:
                if self.configure_window(browser_window):
                    self.logger.log_action("Существующее окно браузера настроено!")
                    return True
                self.logger.log_action("Не удалось настроить существующее окно, создаём новое...")
            self.logger.log_action("Создание нового окна браузера...")
            if self.create_automation_window():
                time.sleep(3)
                browser_window = self.find_browser_window()
                if browser_window and self.configure_window(browser_window):
                    self.logger.log_action("Новое окно браузера создано и настроено!")
                    return True
            return False
        except Exception as e:
            self.logger.log_action(f"КРИТИЧЕСКАЯ ОШИБКА при настройке окна: {e}")
            return False
    
    def quick_setup_window(self):
        """Быстрая настройка существующего окна браузера (Ctrl+Shift+V)."""
        try:
            self.logger.log_action("Быстрая настройка окна браузера...")
            browser_window = self.find_browser_window()
            if browser_window and self.configure_window(browser_window):
                self.logger.log_action("Окно браузера настроено быстро!")
                return True
            self.logger.log_action("Окно браузера не найдено.")
            return False
        except Exception as e:
            self.logger.log_action(f"ОШИБКА при быстрой настройке окна: {e}")
            return False
