"""
Низкоуровневый контроль воркер-процесса v2.
Запуск в подпроцессе, жёсткий стоп по Esc (terminate), без проверок флагов в воркере.
"""
from multiprocessing import Process

# Текущий процесс генерации (для Esc и stop_worker без аргумента)
_current_worker: Process | None = None
# Тип текущего воркера: "browser" или "api" (для поведения Esc и хоткеев)
_current_worker_type: str | None = None


def start_worker(target_fn, args=(), worker_type: str | None = None):
    """
    Запускает воркер в отдельном процессе.
    Возвращает Process или None, если воркер уже запущен.
    """
    global _current_worker, _current_worker_type

    if _current_worker is not None and _current_worker.is_alive():
        print("[ПРОЦЕСС] Воркер уже запущен. Сначала остановите (Esc)")
        return None

    process = Process(target=target_fn, args=args)
    process.start()
    _current_worker = process
    # По умолчанию считаем браузерным воркером, если тип не передан явно
    _current_worker_type = worker_type or "browser"
    print(f"[ПРОЦЕСС] Воркер запущен (PID: {process.pid})")
    return process


def stop_worker(process=None):
    """
    Жёсткий стоп воркера: terminate() + join(timeout).
    Если process не передан — останавливается _current_worker.
    """
    global _current_worker, _current_worker_type

    proc = process if process is not None else _current_worker

    if proc is None:
        print("[ПРОЦЕСС] Воркер не запущен")
        return

    if not proc.is_alive():
        print("[ПРОЦЕСС] Воркер уже завершён")
        _current_worker = None
        _current_worker_type = None
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
        _current_worker_type = None


def wait_worker(process=None):
    """
    Дождаться завершения воркера и очистить текущий tracked process.
    Используется CLI-меню, чтобы не читать stdin параллельно с генерацией.
    """
    global _current_worker, _current_worker_type

    proc = process if process is not None else _current_worker
    if proc is None:
        return

    proc.join()
    if _current_worker is proc:
        _current_worker = None
        _current_worker_type = None


def get_current_worker():
    """Возвращает текущий воркер-процесс или None."""
    return _current_worker


def get_current_worker_type() -> str | None:
    """Возвращает тип текущего воркера: 'browser', 'api' или None, если воркер не запущен."""
    return _current_worker_type
