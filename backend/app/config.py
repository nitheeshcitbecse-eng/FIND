import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_DIR = BASE_DIR / "sample_data"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'ubis.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "720"))

USE_INSIGHTFACE = os.getenv("USE_INSIGHTFACE", "1") == "1"
USE_YOLO = os.getenv("USE_YOLO", "1") == "1"
FACE_MODEL = os.getenv("FACE_MODEL", "buffalo_l")

# Fusion weights. These are hand-set for the prototype; a learned ranker
# replaces them once you have labelled confirmed-identification data.
FUSION_WEIGHTS = {
    "fingerprint": 0.45,
    "face": 0.30,
    "tattoo": 0.10,
    "belongings": 0.05,
    "geo": 0.07,
    "demographics": 0.03,
}

TOP_K = 10