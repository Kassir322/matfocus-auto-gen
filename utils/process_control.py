"""
Низкоуровневый контроль воркер-процесса v2.
Запуск в подпроцессе, жёсткий стоп по Esc (terminate), без проверок флагов в воркере.
"""
from multiprocessing import Process

# Текущий процесс генерации (для Esc и stop_worker без аргумента)
_current_worker: Process | None = None


def start_worker(target_fn, args=()):
    """
    Запускает воркер в отдельном процессе.
    Возвращает Process или None, если воркер уже запущен.
    """
    global _current_worker

    if _current_worker is not None and _current_worker.is_alive():
        print("[ПРОЦЕСС] Воркер уже запущен. Сначала остановите (Esc)")
        return None

    process = Process(target=target_fn, args=args)
    process.start()
    _current_worker = process
    print(f"[ПРОЦЕСС] Воркер запущен (PID: {process.pid})")
    return process


def stop_worker(process=None):
    """
    Жёсткий стоп воркера: terminate() + join(timeout).
    Если process не передан — останавливается _current_worker.
    """
    global _current_worker

    proc = process if process is not None else _current_worker

    if proc is None:
        print("[ПРОЦЕСС] Воркер не запущен")
        return

    if not proc.is_alive():
        print("[ПРОЦЕСС] Воркер уже завершён")
        _current_worker = None
        return

    print("Остановлено пользователем.")
    proc.terminate()
    proc.join(timeout=1.0)

    if proc.is_alive():
        proc.kill()
        proc.join(timeout=0.5)

    print("[ПРОЦЕСС] Воркер завершён")
    if _current_worker is proc:
        _current_worker = None


def get_current_worker():
    """Возвращает текущий воркер-процесс или None."""
    return _current_worker
