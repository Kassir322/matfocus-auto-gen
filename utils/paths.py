"""Repository-rooted paths for the active v2 runtime."""

from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
LOGS_DIR = REPO_ROOT / "logs"
GENERATED_IMAGES_DIR = REPO_ROOT / "generated_images"


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


def resolve_app_path(path: str | os.PathLike | None, default: str | None = None) -> str:
    raw = str(path or default or "").strip()
    if not raw:
        return ""
    candidate = Path(raw)
    if candidate.is_absolute():
        return str(candidate)
    return str(REPO_ROOT / candidate)


def storage_path_value(path: str | os.PathLike | None) -> str:
    raw = str(path or "").strip()
    if not raw:
        return ""
    candidate = Path(raw)
    if not candidate.is_absolute():
        return raw
    try:
        return str(candidate.resolve().relative_to(REPO_ROOT)).replace("/", "\\")
    except ValueError:
        return str(candidate)
