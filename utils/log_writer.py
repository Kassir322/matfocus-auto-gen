"""
Хелпер записи логов в файл v2 (LOGGING.md).
Формат строки: YYYY-MM-DD HH:MM:SS message
"""
from datetime import datetime


def write_log_line(file_handle, message: str) -> None:
    """
    Пишет в файл лога одну строку с временем и сообщением, затем flush.
    message уже содержит тег, например "[PLAN] Режим: standard. ..."
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_handle.write(f"{ts} {message}\n")
    file_handle.flush()
