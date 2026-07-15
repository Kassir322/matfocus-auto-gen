import os
import time

from utils.log_retention import LOG_RETENTION_DAYS, cleanup_old_logs


def test_cleanup_old_logs_removes_only_expired_generator_logs(tmp_path):
    now = time.time()
    expired = tmp_path / "auto-gen_expired.log"
    fresh = tmp_path / "auto-gen_fresh.log"
    other = tmp_path / "other.log"
    for path in (expired, fresh, other):
        path.write_text("log", encoding="utf-8")

    os.utime(expired, (now - (LOG_RETENTION_DAYS + 1) * 24 * 60 * 60,) * 2)
    os.utime(fresh, (now - 24 * 60 * 60,) * 2)
    os.utime(other, (now - (LOG_RETENTION_DAYS + 1) * 24 * 60 * 60,) * 2)

    assert cleanup_old_logs(tmp_path, now=now) == 1
    assert not expired.exists()
    assert fresh.exists()
    assert other.exists()
