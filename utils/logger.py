"""
Система логирования
"""
import datetime

class Logger:
    def __init__(self, enabled=True):
        self.enabled = enabled
    
    def log_action(self, action):
        """Логирование действий с временной меткой"""
        if self.enabled:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {action}")
    
    def enable_logging(self):
        """Включение логирования"""
        self.enabled = True
    
    def disable_logging(self):
        """Отключение логирования"""
        self.enabled = False