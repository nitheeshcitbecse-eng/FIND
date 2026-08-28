import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_DIR = BASE_DIR / "sample_data"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'ubis.db'}")

# Separate physical database for government identity records (Aadhaar number,
# fingerprint, face, address). Read-only from the app — the only writer is
# seed_govern_db.py. Never share a connection/engine with DATABASE_URL above.
GOVERN_DATABASE_URL = os.getenv("GOVERN_DATABASE_URL", f"sqlite:///{BASE_DIR / 'govern.db'}")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "720"))

# Supabase Storage for the normal_db side (case evidence photos). Empty by
# default: storage.py falls back to local disk (MEDIA_DIR) unless both a URL
# and service key are set, so local development needs no cloud account.
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "evidence")

# Supabase Storage for the govern_db side (GovPerson source images). Deliberately
# separate credentials/bucket from the ones above, same isolation reasoning as
# GOVERN_DATABASE_URL vs DATABASE_URL. Only ever used server-side by
# seed_govern_db.py — no API response ever returns a GovPerson image.
GOVERN_SUPABASE_URL = os.getenv("GOVERN_SUPABASE_URL", "")
GOVERN_SUPABASE_SERVICE_KEY = os.getenv("GOVERN_SUPABASE_SERVICE_KEY", "")
GOVERN_STORAGE_BUCKET = os.getenv("GOVERN_STORAGE_BUCKET", "govern-media")

USE_INSIGHTFACE = os.getenv("USE_INSIGHTFACE", "1") == "1"
USE_YOLO = os.getenv("USE_YOLO", "1") == "1"
FACE_MODEL = os.getenv("FACE_MODEL", "buffalo_l")

# Fusion weights for the biometric comparison against govern_db. Hand-set for
# the prototype; a learned ranker replaces them once you have labelled
# confirmed-identification data.
FUSION_WEIGHTS = {
    "fingerprint": 0.45,
    "face": 0.30,
}

# Minimum fused biometric score (fingerprint, optionally + face) to treat a
# probe as a match against a govern_db record. Shared by both identification
# entry points — routers/persons.py::identify_by_fingerprint (an ad-hoc
# share-intent capture) and routers/cases.py::run_match (a case's stored
# evidence) — since both perform the identical govern_db comparison and only
# differ in what triggers them and where the result is recorded.
IDENTIFY_MATCH_THRESHOLD = float(os.getenv("IDENTIFY_MATCH_THRESHOLD", "0.5"))