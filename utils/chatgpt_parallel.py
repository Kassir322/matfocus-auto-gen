"""
Параллельный runtime для ChatGPT image API с глобальным rate limiter.
"""
from __future__ import annotations

import queue
import re
import threading
import time
from collections import deque
from dataclasses import dataclass

from utils.log_writer import write_log_line


RATE_LIMIT_RE = re.compile(r"\b429\b|rate.?limit", re.IGNORECASE)
RETRY_AFTER_RE = re.compile(r"retry[- ]after[^0-9]*(\d+(?:\.\d+)?)", re.IGNORECASE)


@dataclass
class LimiterSnapshot:
    used: int
    capacity: int
    wait_seconds: float


@dataclass
class ParallelTaskResult:
    task: dict
    result: object
    duration_seconds: float
    worker_id: int


class ApiLaunchLimiter:
    def __init__(self, capacity: int, window_seconds: float) -> None:
        self.capacity = max(1, int(capacity))
        self.window_seconds = max(1.0, float(window_seconds))
        self._launch_times: deque[float] = deque()
        self._blocked_until = 0.0
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        while self._launch_times and (now - self._launch_times[0]) >= self.window_seconds:
            self._launch_times.popleft()

    def snapshot(self) -> LimiterSnapshot:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            wait_seconds = 0.0
            if self._blocked_until > now:
                wait_seconds = self._blocked_until - now
            elif len(self._launch_times) >= self.capacity:
                wait_seconds = self.window_seconds - (now - self._launch_times[0])
            return LimiterSnapshot(
                used=len(self._launch_times),
                capacity=self.capacity,
                wait_seconds=max(0.0, wait_seconds),
            )

    def block_for(self, seconds: float) -> None:
        seconds = max(0.0, float(seconds))
        if seconds <= 0:
            return
        with self._lock:
            self._blocked_until = max(self._blocked_until, time.monotonic() + seconds)

    def acquire_slot(self, on_wait=None) -> LimiterSnapshot:
        notified_wait = None
        while True:
            now = time.monotonic()
            with self._lock:
                self._prune(now)
                wait_seconds = 0.0
                if self._blocked_until > now:
                    wait_seconds = self._blocked_until - now
                elif len(self._launch_times) >= self.capacity:
                    wait_seconds = self.window_seconds - (now - self._launch_times[0])
                else:
                    self._launch_times.append(now)
                    return LimiterSnapshot(
                        used=len(self._launch_times),
                        capacity=self.capacity,
                        wait_seconds=0.0,
                    )

            wait_seconds = max(0.0, wait_seconds)
            rounded_wait = round(wait_seconds, 3)
            if on_wait is not None and rounded_wait != notified_wait:
                notified_wait = rounded_wait
                on_wait(
                    LimiterSnapshot(
                        used=self.snapshot().used,
                        capacity=self.capacity,
                        wait_seconds=wait_seconds,
                    )
                )
            time.sleep(wait_seconds if wait_seconds > 0 else 0.05)


class ParallelRuntimeState:
    def __init__(self, total_tasks: int, capacity: int) -> None:
        self.total_tasks = max(0, int(total_tasks))
        self.capacity = max(1, int(capacity))
        self._lock = threading.Lock()
        self._active_workers = 0
        self._started_tasks = 0
        self._rate_limit_wait_seconds = 0.0
        self._rate_limit_used = 0

    def update_wait(self, snapshot: LimiterSnapshot) -> None:
        with self._lock:
            self._rate_limit_used = snapshot.used
            self._rate_limit_wait_seconds = max(0.0, snapshot.wait_seconds)

    def mark_started(self, snapshot: LimiterSnapshot) -> None:
        with self._lock:
            self._started_tasks += 1
            self._active_workers += 1
            self._rate_limit_used = snapshot.used
            self._rate_limit_wait_seconds = 0.0

    def mark_finished(self) -> None:
        with self._lock:
            self._active_workers = max(0, self._active_workers - 1)

    def snapshot(self, attempted: int) -> dict:
        with self._lock:
            queued_remaining = max(0, self.total_tasks - attempted - self._active_workers)
            return {
                "active_workers": self._active_workers,
                "rate_limit_used": self._rate_limit_used,
                "rate_limit_capacity": self.capacity,
                "rate_limit_wait_seconds": self._rate_limit_wait_seconds,
                "queued_remaining": queued_remaining,
            }


def is_parallel_enabled(settings: dict, provider: str) -> bool:
    return str(provider or "").strip().lower() == "chatgpt" and bool(settings.get("API_CHATGPT_PARALLEL_ENABLED", True))


def get_parallel_config(settings: dict) -> dict:
    return {
        "max_workers": max(1, int(settings.get("API_CHATGPT_MAX_WORKERS", 2))),
        "rate_limit_ipm": max(1, int(settings.get("API_CHATGPT_RATE_LIMIT_IPM", 5))),
        "window_seconds": max(1, int(settings.get("API_CHATGPT_RATE_LIMIT_WINDOW_SECONDS", 60))),
    }


def estimate_parallel_total_seconds(task_count: int, baseline_seconds: float, settings: dict) -> float:
    task_count = max(0, int(task_count))
    if task_count == 0:
        return 0.0

    config = get_parallel_config(settings)
    workers = config["max_workers"]
    rate_limit_ipm = config["rate_limit_ipm"]
    window_seconds = config["window_seconds"]

    worker_limited = baseline_seconds * ((task_count + workers - 1) // workers)
    rate_limited = baseline_seconds + max(0, task_count - 1) * (window_seconds / rate_limit_ipm)
    return max(worker_limited, rate_limited)


def extract_rate_limit_wait_seconds(reason: str, settings: dict) -> float | None:
    text = str(reason or "").strip()
    if not text or RATE_LIMIT_RE.search(text) is None:
        return None

    retry_match = RETRY_AFTER_RE.search(text)
    if retry_match:
        try:
            return max(0.0, float(retry_match.group(1)))
        except ValueError:
            pass

    config = get_parallel_config(settings)
    return max(1.0, float(config["window_seconds"]) / float(config["rate_limit_ipm"]))


def run_parallel_chatgpt_tasks(
    *,
    tasks: list[dict],
    settings: dict,
    stats,
    log_file,
    execute_task,
    normalize_result,
    label_for_task,
    on_task_completed,
    print_fn=print,
) -> None:
    if not tasks:
        return

    config = get_parallel_config(settings)
    limiter = ApiLaunchLimiter(
        capacity=config["rate_limit_ipm"],
        window_seconds=config["window_seconds"],
    )
    runtime_state = ParallelRuntimeState(
        total_tasks=len(tasks),
        capacity=config["rate_limit_ipm"],
    )
    task_queue: queue.Queue[dict | None] = queue.Queue()
    result_queue: queue.Queue[ParallelTaskResult] = queue.Queue()

    for task in tasks:
        task_queue.put(task)

    def refresh_parallel_status() -> None:
        stats.update_parallel_status(**runtime_state.snapshot(stats.attempted))

    def worker_loop(worker_id: int) -> None:
        while True:
            task = task_queue.get()
            if task is None:
                task_queue.task_done()
                break

            label = label_for_task(task)

            def on_wait(snapshot: LimiterSnapshot) -> None:
                runtime_state.update_wait(snapshot)
                write_log_line(
                    log_file,
                    f"[RATE] waiting {snapshot.wait_seconds:.1f}s worker={worker_id} used={snapshot.used}/{snapshot.capacity}",
                )

            snapshot = limiter.acquire_slot(on_wait=on_wait)
            runtime_state.mark_started(snapshot)
            write_log_line(log_file, f"[RATE] slot granted worker={worker_id} used={snapshot.used}/{snapshot.capacity}")
            write_log_line(log_file, f"[WORKER] started worker={worker_id} label={label}")
            write_log_line(
                log_file,
                f"[QUEUE] remaining={max(0, len(tasks) - stats.attempted - runtime_state.snapshot(stats.attempted)['active_workers'])}",
            )

            started = time.monotonic()
            try:
                result = execute_task(task, worker_id)
            finally:
                duration_seconds = time.monotonic() - started
                runtime_state.mark_finished()

            write_log_line(log_file, f"[WORKER] finished worker={worker_id} label={label}")
            result_queue.put(
                ParallelTaskResult(
                    task=task,
                    result=result,
                    duration_seconds=duration_seconds,
                    worker_id=worker_id,
                )
            )
            task_queue.task_done()

    workers = []
    for worker_id in range(1, config["max_workers"] + 1):
        thread = threading.Thread(target=worker_loop, args=(worker_id,), daemon=True)
        thread.start()
        workers.append(thread)

    completed = 0
    while completed < len(tasks):
        refresh_parallel_status()
        item = result_queue.get()
        completed += 1
        ok, reason = normalize_result(item.task, item.result)
        label = label_for_task(item.task)
        stats.register_attempt(label, ok, item.duration_seconds, reason)

        backoff_seconds = extract_rate_limit_wait_seconds(reason, settings) if not ok else None
        if backoff_seconds:
            limiter.block_for(backoff_seconds)
            snapshot = limiter.snapshot()
            runtime_state.update_wait(snapshot)
            write_log_line(log_file, f"[RATE] backoff {backoff_seconds:.1f}s after worker={item.worker_id} label={label}")

        on_task_completed(item.task, ok, reason)
        refresh_parallel_status()
        print_fn(stats.progress_line(item.duration_seconds))
        write_log_line(log_file, stats.progress_log_line(label, item.duration_seconds, ok, reason))

    for _ in workers:
        task_queue.put(None)
    for thread in workers:
        thread.join(timeout=1.0)

    stats.clear_parallel_status()
