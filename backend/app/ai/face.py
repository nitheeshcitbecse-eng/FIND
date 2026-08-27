"""Face pipeline: detection -> alignment -> ArcFace embedding.

Primary path uses InsightFace (`buffalo_l`), whose recognition model is
ArcFace-trained. If InsightFace/onnxruntime are not installed, a classical
OpenCV fallback keeps the whole system runnable — it is much weaker and is
only there so you can build and test the app before setting up models.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

from ..config import FACE_MODEL, USE_INSIGHTFACE

log = logging.getLogger(__name__)

_app = None
_mode = "unloaded"


def _load():
    global _app, _mode
    if _mode != "unloaded":
        return
    if not USE_INSIGHTFACE:
        _mode = "fallback"
        return
    try:
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(name=FACE_MODEL, providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=-1, det_size=(640, 640))
        _app = app
        _mode = "arcface"
        log.info("Face engine: InsightFace ArcFace (%s)", FACE_MODEL)
    except Exception as exc:  # noqa: BLE001
        log.warning("InsightFace unavailable (%s). Using fallback face encoder.", exc)
        _mode = "fallback"


def engine_name() -> str:
    _load()
    return "insightface-arcface" if _mode == "arcface" else "opencv-fallback"


def _read(image_path: str) -> np.ndarray:
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    return img


def _fallback_embedding(img: np.ndarray) -> tuple[np.ndarray, list[int] | None, float]:
    """Detect with Haar cascade, then build a simple appearance descriptor."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

    if len(faces) > 0:
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        bbox = [int(x), int(y), int(x + w), int(y + h)]
        crop = gray[y : y + h, x : x + w]
    else:
        bbox = None
        crop = gray

    crop = cv2.resize(crop, (32, 32), interpolation=cv2.INTER_AREA)
    crop = cv2.equalizeHist(crop)
    vec = crop.astype(np.float32).flatten()
    vec -= vec.mean()
    norm = np.linalg.norm(vec)
    vec = vec / norm if norm > 0 else vec

    sharpness = float(cv2.Laplacian(crop, cv2.CV_64F).var())
    quality = float(np.clip(sharpness / 500.0, 0.0, 1.0)) * (1.0 if bbox else 0.4)
    return vec, bbox, quality


def embed_face(image_path: str) -> dict:
    """Return {embedding, bbox, quality, faces_found, engine}."""
    _load()
    img = _read(image_path)

    if _mode == "arcface" and _app is not None:
        faces = _app.get(img)
        if faces:
            face = max(
                faces,
                key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            )
            emb = np.asarray(face.normed_embedding, dtype=np.float32)
            x1, y1, x2, y2 = [int(v) for v in face.bbox]
            area_ratio = ((x2 - x1) * (y2 - y1)) / float(img.shape[0] * img.shape[1])
            quality = float(np.clip(float(face.det_score) * 0.7 + area_ratio * 3.0, 0.0, 1.0))
            return {
                "embedding": emb.tolist(),
                "bbox": [x1, y1, x2, y2],
                "quality": quality,
                "faces_found": len(faces),
                "engine": "insightface-arcface",
            }
        return {
            "embedding": None,
            "bbox": None,
            "quality": 0.0,
            "faces_found": 0,
            "engine": "insightface-arcface",
        }

    vec, bbox, quality = _fallback_embedding(img)
    return {
        "embedding": vec.tolist(),
        "bbox": bbox,
        "quality": quality,
        "faces_found": 1 if bbox else 0,
        "engine": "opencv-fallback",
    }


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))