import time

from utils import chatgpt_parallel
from utils import generation_stats


def test_rate_limiter_blocks_sixth_launch_inside_window():
    limiter = chatgpt_parallel.ApiLaunchLimiter(capacity=5, window_seconds=60)

    for _ in range(5):
        snapshot = limiter.acquire_slot()
        assert snapshot.wait_seconds == 0

    blocked = limiter.snapshot()
    assert blocked.used == 5
    assert blocked.capacity == 5
    assert blocked.wait_seconds > 0


def test_parallel_progress_line_contains_runtime_tail():
    stats = generation_stats.GenerationRunStats(
        planned_total=10,
        generation_method="api",
        mode_name="standard",
        estimated_total_seconds=120.0,
    )
    stats.register_attempt("card 1", True, 20.0)
    stats.update_parallel_status(
        active_workers=2,
        rate_limit_used=5,
        rate_limit_capacity=5,
        rate_limit_wait_seconds=8.2,
        queued_remaining=7,
    )

    rendered = stats.progress_line(22.0)
    assert "в работе 2" in rendered
    assert "лимит 5/5" in rendered
    assert "ожидание 8с" in rendered


def test_parallel_estimate_uses_workers_and_rate_limit():
    estimate = chatgpt_parallel.estimate_parallel_total_seconds(
        task_count=6,
        baseline_seconds=22.0,
        settings={
            "API_CHATGPT_MAX_WORKERS": 2,
            "API_CHATGPT_RATE_LIMIT_IPM": 5,
            "API_CHATGPT_RATE_LIMIT_WINDOW_SECONDS": 60,
        },
    )

    assert estimate == 82.0


def test_extract_rate_limit_backoff_uses_retry_after_when_present():
    seconds = chatgpt_parallel.extract_rate_limit_wait_seconds(
        "RateLimitError 429 Retry-After: 17",
        {
            "API_CHATGPT_RATE_LIMIT_IPM": 5,
            "API_CHATGPT_RATE_LIMIT_WINDOW_SECONDS": 60,
        },
    )
    assert seconds == 17.0
