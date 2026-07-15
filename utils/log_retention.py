"""Автоматическая очистка устаревших журналов генератора."""

from __future__ import annotations

import time
from pathlib import Path

from utils.paths import LOGS_DIR


LOG_RETENTION_DAYS = 30


def cleanup_old_logs(log_dir: str | Path = LOGS_DIR, now: float | None = None) -> int:
    """Удаляет журналы генератора старше срока хранения и возвращает их количество."""
    cutoff = (time.time() if now is None else now) - LOG_RETENTION_DAYS * 24 * 60 * 60
    removed = 0
    try:
        paths = Path(log_dir).glob("auto-gen_*.log")
        for path in paths:
            try:
                if path.is_file() and path.stat().st_mtime <= cutoff:
                    path.unlink()
                    removed += 1
            except OSError:
                continue
    except OSError:
        return removed
    return removed
