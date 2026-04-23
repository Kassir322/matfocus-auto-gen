"""
Legacy console logger kept only for backward compatibility.

The active v2 runtime writes detailed logs through `utils.log_writer` into files
under `logs/`. This module is not part of the active v2 logging contract.
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
