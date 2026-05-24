"""Small helpers for machine-readable agent run results."""

import glob
import os


def list_png_images(folder: str | None) -> list[str]:
    """Return generated PNG files in a stable order."""
    if not folder or not os.path.isdir(folder):
        return []
    return sorted(glob.glob(os.path.join(folder, "*.png")))


def make_error_result(mode: str, message: str, output_dir: str | None = None, log_file: str | None = None) -> dict:
    return {
        "ok": False,
        "mode": mode,
        "planned": 0,
        "succeeded": 0,
        "failed": 0,
        "output_dir": output_dir,
        "log_file": log_file,
        "images": list_png_images(output_dir),
        "errors": [message],
    }


def make_success_result(
    mode: str,
    planned: int,
    succeeded: int,
    output_dir: str | None,
    log_file: str | None,
    errors: list[str] | None = None,
) -> dict:
    errors = errors or []
    return {
        "ok": succeeded == planned and not errors,
        "mode": mode,
        "planned": planned,
        "succeeded": succeeded,
        "failed": max(0, planned - succeeded),
        "output_dir": output_dir,
        "log_file": log_file,
        "images": list_png_images(output_dir),
        "errors": errors,
    }
