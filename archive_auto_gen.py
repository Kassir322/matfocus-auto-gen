from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(r"c:\Yandex.Disk\Yandex.Disk\auto-gen")
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
ARCHIVE_PATH = ROOT / f"auto-gen_backup_{TIMESTAMP}.zip"


def is_excluded_dir(path: Path) -> bool:
    normalized = path.name.lower().replace(" ", "").replace("_", "")
    return normalized == "generatedimages"


def main() -> None:
    archived_files = 0
    archived_bytes = 0

    with ZipFile(ARCHIVE_PATH, "w", compression=ZIP_DEFLATED) as archive:
        for path in ROOT.rglob("*"):
            if path == ARCHIVE_PATH:
                continue
            excluded_dirs = list(path.parents)
            if path.is_dir():
                excluded_dirs.append(path)
            if any(is_excluded_dir(parent) for parent in excluded_dirs if parent != ROOT.parent):
                continue
            if path.is_dir():
                continue

            relative_path = path.relative_to(ROOT)
            archive.write(path, relative_path.as_posix())
            archived_files += 1
            archived_bytes += path.stat().st_size

    print(f"archive={ARCHIVE_PATH}")
    print(f"files={archived_files}")
    print(f"bytes={archived_bytes}")


if __name__ == "__main__":
    main()
