"""
Управление окнами для автоматизации.
Логирование по LOGGING.md: тег [WINDOW], без эмодзи. Логгер опциональный.
"""
import time
import pyautogui
import subprocess
import os
import pygetwindow as gw


class WindowManager:
    def __init__(self, logger=None):
        self.logger = logger
        self.window_title = "AI Studio Automation Window"
        self.window_width = 1200
        self.window_height = 1000
        self.window_x = 0
        self.window_y = 0
        self.browser_titles = [
            "Google Chrome",
            "Mozilla Firefox",
            "Microsoft Edge",
            "Chrome",
            "Firefox",
            "Edge",
        ]

    def _log(self, message):
        """Пишем в лог только если передан логгер (v2: тег [WINDOW], без эмодзи)."""
        if self.logger is not None:
            self.logger.log_action(f"[WINDOW] {message}")

    def create_automation_window(self):
        """
        Создание рабочего окна для автоматизации.
        Создаёт окно браузера с фиксированным размером и позицией.
        """
        try:
            self._log("Создание рабочего окна для автоматизации...")

            # Проверяем доступность браузеров
            browsers = self._find_available_browsers()

            if not browsers:
                self._log("Не найдено доступных браузеров")
                return False

            # Выбираем первый доступный браузер (единый источник путей)
            browser_path = browsers[0]
            browser_name = os.path.basename(browser_path).lower()

            self._log(f"Используем браузер: {os.path.basename(browser_path)}")

            # Создаём окно браузера с нужными параметрами (путь из _find_available_browsers)
            if "chrome" in browser_name:
                success = self._create_chrome_window(browser_path)
            elif "firefox" in browser_name:
                success = self._create_firefox_window(browser_path)
            elif "edge" in browser_name or "msedge" in browser_name:
                success = self._create_edge_window(browser_path)
            else:
                success = self._create_generic_window(browser_path)

            if success:
                self._log("Рабочее окно создано успешно")
                return True
            else:
                self._log("Не удалось создать рабочее окно")
                return False

        except Exception as e:
            self._log(f"Ошибка при создании окна: {e}")
            return False
    
    def _find_available_browsers(self):
        """Поиск доступных браузеров в системе"""
        browsers = []
        
        # Пути к браузерам (Windows)
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
    
    def _create_chrome_window(self, browser_path):
        """Создание окна Chrome с нужными параметрами (путь из _find_available_browsers)."""
        try:
            chrome_args = [
                "--new-window",
                f"--window-size={self.window_width},{self.window_height}",
                f"--window-position={self.window_x},{self.window_y}",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "about:blank"
            ]
            subprocess.Popen([browser_path, *chrome_args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)  # Ждём запуска
            return self._verify_window_created()
        except Exception as e:
            self._log(f"Ошибка создания Chrome окна: {e}")
            return False

    def _create_firefox_window(self, browser_path):
        """Создание окна Firefox с нужными параметрами (путь из _find_available_browsers)."""
        try:
            firefox_args = [
                "-new-window",
                "-width", str(self.window_width),
                "-height", str(self.window_height),
                "about:blank"
            ]
            subprocess.Popen([browser_path, *firefox_args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)  # Ждём запуска
            return self._verify_window_created()
        except Exception as e:
            self._log(f"Ошибка создания Firefox окна: {e}")
            return False

    def _create_edge_window(self, browser_path):
        """Создание окна Edge с нужными параметрами (путь из _find_available_browsers)."""
        try:
            edge_args = [
                "--new-window",
                f"--window-size={self.window_width},{self.window_height}",
                f"--window-position={self.window_x},{self.window_y}",
                "about:blank"
            ]
            subprocess.Popen([browser_path, *edge_args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)  # Ждём запуска
            return self._verify_window_created()
        except Exception as e:
            self._log(f"Ошибка создания Edge окна: {e}")
            return False

    def _create_generic_window(self, browser_path):
        """Универсальное создание окна браузера"""
        try:
            subprocess.Popen([browser_path, "--new-window", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)  # Ждём запуска
            return self._verify_window_created()
        except Exception as e:
            self._log(f"Ошибка создания окна браузера: {e}")
            return False
    
    def _verify_window_created(self):
        """Проверка что окно браузера создалось"""
        try:
            time.sleep(2)
            # Простая проверка: курсор двигается — окно есть
            current_pos = pyautogui.position()
            pyautogui.moveTo(current_pos.x + 1, current_pos.y + 1)
            pyautogui.moveTo(current_pos.x, current_pos.y)
            self._log("Окно браузера создано и активно")
            return True
        except Exception as e:
            self._log(f"Ошибка проверки окна: {e}")
            return False

    def find_browser_window(self):
        """Поиск окна браузера среди открытых окон с предпочтением уже развёрнутых окон."""
        try:
            all_windows = gw.getAllWindows()
            minimized_match = None
            for window in all_windows:
                if window.title and any(browser in window.title for browser in self.browser_titles):
                    if not getattr(window, "isMinimized", False):
                        self._log(f"Найдено окно браузера: {window.title}")
                        return window
                    if minimized_match is None:
                        minimized_match = window
            if minimized_match is not None:
                self._log(f"Найдено минимизированное окно браузера: {minimized_match.title}")
                return minimized_match
            self._log("Окно браузера не найдено")
            return None
        except Exception as e:
            self._log(f"Ошибка при поиске окна браузера: {e}")
            return None

    def configure_window(self, window):
        """Настройка окна: активация, размер 1200x1000, позиция (0,0)."""
        try:
            self._log("Настройка окна браузера...")
            if getattr(window, "isMinimized", False) and hasattr(window, "restore"):
                window.restore()
                time.sleep(0.5)
            window.activate()
            time.sleep(0.5)
            window.resizeTo(self.window_width, self.window_height)
            time.sleep(0.5)
            window.moveTo(self.window_x, self.window_y)
            time.sleep(0.5)
            current_size = window.size
            current_pos = window.topleft
            self._log(f"Окно настроено: размер {current_size}, позиция {current_pos}")
            return True
        except Exception as e:
            self._log(f"Ошибка при настройке окна: {e}")
            return False

    def setup_automation_window(self):
        """Полная настройка рабочего окна: поиск существующего или создание нового (автоподготовка перед стартом)."""
        try:
            self._log("Настройка рабочего окна")
            browser_window = self.find_browser_window()
            if browser_window:
                if self.configure_window(browser_window):
                    self._log("Существующее окно браузера настроено")
                    return True
                self._log("Не удалось настроить существующее окно, создаём новое")
            else:
                self._log("Создание нового окна браузера")
            if self.create_automation_window():
                time.sleep(3)
                browser_window = self.find_browser_window()
                if browser_window:
                    if self.configure_window(browser_window):
                        self._log("Новое окно браузера создано и настроено")
                        return True
                    self._log("Окно создано, но не удалось настроить")
                    return False
                self._log("Не удалось найти созданное окно")
                return False
            self._log("Не удалось создать новое окно")
            return False
        except Exception as e:
            self._log(f"Критическая ошибка при настройке окна: {e}")
            return False

    def quick_setup_window(self):
        """Быстрая настройка существующего окна (для Ctrl+Shift+V): найти и настроить размер/позицию."""
        try:
            self._log("Быстрая настройка окна браузера")
            browser_window = self.find_browser_window()
            if browser_window:
                if self.configure_window(browser_window):
                    self._log("Окно браузера настроено")
                    return True
                self._log("Не удалось настроить окно")
                return False
            self._log("Окно браузера не найдено. Используйте Ctrl+Shift+S для создания нового.")
            return False
        except Exception as e:
            self._log(f"Ошибка при быстрой настройке окна: {e}")
            return False
