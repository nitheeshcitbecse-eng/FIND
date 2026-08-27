import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from .config import MEDIA_DIR


def save_upload(upload: UploadFile, subdir: str) -> str:
    """Save an uploaded file and return a path relative to MEDIA_DIR."""
    target_dir = MEDIA_DIR / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(upload.filename or "").suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}:
        suffix = ".jpg"

    name = f"{uuid.uuid4().hex}{suffix}"
    dest = target_dir / name
    with dest.open("wb") as f:
        upload.file.seek(0)
        shutil.copyfileobj(upload.file, f)
    return f"{subdir}/{name}"


def save_bytes(data: bytes, subdir: str, suffix: str = ".jpg") -> str:
    target_dir = MEDIA_DIR / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{suffix}"
    (target_dir / name).write_bytes(data)
    return f"{subdir}/{name}"


def abs_path(relative: str) -> Path:
    return MEDIA_DIR / relative