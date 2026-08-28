from __future__ import annotations

import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

import httpx
from fastapi import UploadFile

from . import config
from .config import MEDIA_DIR

_ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def _suffix_for(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in _ALLOWED_SUFFIXES else ".jpg"


def _upload_to_supabase(
    data: bytes, subdir: str, name: str, base_url: str, service_key: str, bucket: str
) -> str:
    url = f"{base_url}/storage/v1/object/{bucket}/{subdir}/{name}"
    resp = httpx.post(
        url,
        content=data,
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": "application/octet-stream",
            "x-upsert": "true",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return f"{base_url}/storage/v1/object/public/{bucket}/{subdir}/{name}"


@contextmanager
def staged_file(data: bytes, subdir: str, filename: str | None = None, *, target: str = "normal"):
    """Stage uploaded bytes for AI processing, and persist them either to
    local disk (dev) or Supabase Storage (when configured), depending on
    `target` ("normal" -> case evidence, in SUPABASE_URL's project; "govern"
    -> GovPerson media, in GOVERN_SUPABASE_URL's separate project).

    Yields (stored_ref, local_path):
      - stored_ref is what gets persisted in the DB column: a path relative
        to MEDIA_DIR locally, or a full public Supabase Storage URL in
        production.
      - local_path is always a real filesystem path — the AI modules
        (fp_ai/face_ai/obj_ai, all cv2.imread-based) read from it directly,
        so they need no changes for either mode. Only valid inside the
        `with` block; the temp file is deleted on exit.
    """
    suffix = _suffix_for(filename)
    name = f"{uuid.uuid4().hex}{suffix}"

    if target == "govern":
        base_url = config.GOVERN_SUPABASE_URL
        service_key = config.GOVERN_SUPABASE_SERVICE_KEY
        bucket = config.GOVERN_STORAGE_BUCKET
    else:
        base_url = config.SUPABASE_URL
        service_key = config.SUPABASE_SERVICE_KEY
        bucket = config.STORAGE_BUCKET

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        if base_url and service_key:
            stored_ref = _upload_to_supabase(data, subdir, name, base_url, service_key, bucket)
        else:
            target_dir = MEDIA_DIR / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(tmp_path, target_dir / name)
            stored_ref = f"{subdir}/{name}"
        yield stored_ref, str(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def save_upload(upload: UploadFile, subdir: str, *, target: str = "normal"):
    """Context manager: with save_upload(file, subdir) as (stored_ref, local_path): ..."""
    upload.file.seek(0)
    data = upload.file.read()
    return staged_file(data, subdir, upload.filename, target=target)


def save_bytes(data: bytes, subdir: str, suffix: str = ".jpg", *, target: str = "normal"):
    """Context manager variant of save_upload for raw bytes (used by seed scripts)."""
    return staged_file(data, subdir, f"file{suffix}", target=target)


def abs_path(relative: str) -> Path:
    """Resolve a locally-stored relative path (local dev mode only)."""
    return MEDIA_DIR / relative
