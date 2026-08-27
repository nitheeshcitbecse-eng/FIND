"""Fingerprint pipeline: quality -> enhancement -> feature extraction -> 1:N match.

Stages, and where the deep models plug in later:
  1. quality assessment  -> classical ridge-clarity metric now; a CNN regressor
     can replace `assess_quality` and return the same 0..1 score.
  2. enhancement         -> CLAHE + Gabor filter bank + binarise + thin.
     A U-Net can replace `enhance` and return the same binary ridge image.
  3. feature extraction  -> ORB keypoints on the thinned ridge map (a practical
     stand-in for minutiae; a real minutiae extractor returns the same template
     dict shape).
  4. matching            -> Hamming BFMatcher with Lowe ratio test.
"""

from __future__ import annotations

import base64

import cv2
import numpy as np

_ORB = cv2.ORB_create(nfeatures=500, scaleFactor=1.2, edgeThreshold=8, fastThreshold=8)


def _read_gray(path: str) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read fingerprint image: {path}")
    h, w = img.shape
    scale = 400.0 / max(h, w)
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def assess_quality(gray: np.ndarray) -> float:
    """0..1 usability score. Combines contrast, sharpness and ridge coverage."""
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    sharpness = float(cv2.Laplacian(blur, cv2.CV_64F).var())
    contrast = float(gray.std())

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    coverage = float((mag > mag.mean()).mean())

    score = (
        0.40 * np.clip(sharpness / 300.0, 0, 1)
        + 0.35 * np.clip(contrast / 60.0, 0, 1)
        + 0.25 * np.clip(coverage / 0.45, 0, 1)
    )
    return float(np.clip(score, 0.0, 1.0))


def _gabor_bank(gray: np.ndarray) -> np.ndarray:
    accum = np.zeros_like(gray, dtype=np.float32)
    for theta in np.arange(0, np.pi, np.pi / 8):
        kernel = cv2.getGaborKernel((15, 15), 4.0, theta, 8.0, 0.5, 0, ktype=cv2.CV_32F)
        kernel /= 1.5 * kernel.sum() if kernel.sum() != 0 else 1.0
        filtered = cv2.filter2D(gray, cv2.CV_32F, kernel)
        accum = np.maximum(accum, filtered)
    return cv2.normalize(accum, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def enhance(gray: np.ndarray) -> np.ndarray:
    """Return a thinned binary ridge image."""
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    eq = clahe.apply(gray)
    gab = _gabor_bank(eq)

    binary = cv2.adaptiveThreshold(
        gab, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 4
    )
    binary = cv2.morphologyEx(
        binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    )

    try:  # requires opencv-contrib
        thin = cv2.ximgproc.thinning(binary, thinningType=cv2.ximgproc.THINNING_GUOHALL)
    except Exception:  # noqa: BLE001
        thin = binary
    return thin


def extract_template(image_path: str) -> dict:
    """Full pipeline for one fingerprint image -> serialisable template."""
    gray = _read_gray(image_path)
    quality = assess_quality(gray)
    ridges = enhance(gray)

    keypoints, descriptors = _ORB.detectAndCompute(ridges, None)
    if descriptors is None or len(keypoints) == 0:
        keypoints, descriptors = _ORB.detectAndCompute(
            cv2.createCLAHE(3.0, (8, 8)).apply(gray), None
        )

    if descriptors is None:
        return {
            "quality": quality,
            "keypoint_count": 0,
            "descriptors_b64": None,
            "descriptor_shape": None,
        }

    return {
        "quality": quality,
        "keypoint_count": int(len(keypoints)),
        "descriptors_b64": base64.b64encode(descriptors.tobytes()).decode(),
        "descriptor_shape": list(descriptors.shape),
    }


def _restore(template: dict | None) -> np.ndarray | None:
    if not template or not template.get("descriptors_b64"):
        return None
    raw = base64.b64decode(template["descriptors_b64"])
    shape = tuple(template["descriptor_shape"])
    return np.frombuffer(raw, dtype=np.uint8).reshape(shape)


def match_templates(probe: dict | None, gallery: dict | None) -> tuple[float, int]:
    """Return (similarity 0..1, number of good matches)."""
    d1, d2 = _restore(probe), _restore(gallery)
    if d1 is None or d2 is None or len(d1) < 2 or len(d2) < 2:
        return 0.0, 0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    pairs = bf.knnMatch(d1, d2, k=2)

    good = [m for m in pairs if len(m) == 2 and m[0].distance < 0.75 * m[1].distance]
    denom = max(1, min(len(d1), len(d2)))
    raw = len(good) / denom

    # Squash so that ~35% good matches maps near 1.0 (typical for same finger
    # on the SOCOFing dataset). Tune this on your own data.
    similarity = float(np.clip(raw / 0.35, 0.0, 1.0))
    return similarity, len(good)