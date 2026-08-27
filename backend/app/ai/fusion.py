"""Multimodal fusion and explainable ranking.

Weights are renormalised over the modalities that actually have evidence, so a
case with only a face photo is not penalised for having no fingerprint — its
score just carries lower confidence.

The output is a ranked candidate list with a per-modality breakdown. It is
decision support: the final identification is a human decision recorded
separately.
"""

from __future__ import annotations

import math
import re

from ..config import FUSION_WEIGHTS

_STOP = {"a", "an", "the", "on", "of", "and", "with", "left", "right", "small", "large"}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in _STOP and len(w) > 2}


def text_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def label_similarity(labels: list[str], text: str) -> float:
    tb = _tokens(text)
    if not labels or not tb:
        return 0.0
    ta = set()
    for label in labels:
        ta |= _tokens(label)
    if not ta:
        return 0.0
    return len(ta & tb) / len(ta)


def geo_similarity(
    case_lat: float | None,
    case_lng: float | None,
    person_lat: float | None,
    person_lng: float | None,
    half_life_km: float = 300.0,
) -> tuple[float, float | None]:
    if None in (case_lat, case_lng, person_lat, person_lng):
        return 0.0, None
    r = 6371.0
    p1, p2 = math.radians(case_lat), math.radians(person_lat)
    dp = p2 - p1
    dl = math.radians(person_lng - case_lng)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    dist = 2 * r * math.asin(min(1.0, math.sqrt(a)))
    return math.exp(-dist / half_life_km), dist


def demographic_similarity(
    case_sex: str,
    age_min: int | None,
    age_max: int | None,
    person_sex: str,
    person_age: int | None,
) -> tuple[float, str]:
    parts, notes = [], []

    cs, ps = (case_sex or "unknown").lower(), (person_sex or "unknown").lower()
    if cs != "unknown" and ps != "unknown":
        if cs == ps:
            parts.append(1.0)
            notes.append("sex consistent")
        else:
            parts.append(0.0)
            notes.append("SEX MISMATCH")

    if person_age is not None and (age_min is not None or age_max is not None):
        lo = age_min if age_min is not None else 0
        hi = age_max if age_max is not None else 120
        if lo <= person_age <= hi:
            parts.append(1.0)
            notes.append("age within estimated range")
        else:
            gap = min(abs(person_age - lo), abs(person_age - hi))
            parts.append(max(0.0, 1.0 - gap / 20.0))
            notes.append(f"age {gap}y outside estimated range")

    if not parts:
        return 0.0, "no demographic data"
    return sum(parts) / len(parts), "; ".join(notes)


def fuse(signals: dict[str, dict]) -> dict:
    """signals: {modality: {"score": float, "detail": str}} for available modalities only."""
    available = {m: s for m, s in signals.items() if m in FUSION_WEIGHTS}
    if not available:
        return {"score": 0.0, "components": [], "coverage": 0.0}

    total_weight = sum(FUSION_WEIGHTS[m] for m in available)
    components, score = [], 0.0

    for modality, sig in sorted(
        available.items(), key=lambda kv: -FUSION_WEIGHTS[kv[0]]
    ):
        weight = FUSION_WEIGHTS[modality] / total_weight
        raw = float(max(0.0, min(1.0, sig.get("score", 0.0))))
        contribution = weight * raw
        score += contribution
        components.append(
            {
                "modality": modality,
                "score": round(raw, 4),
                "weight": round(weight, 4),
                "contribution": round(contribution, 4),
                "detail": sig.get("detail", ""),
            }
        )

    coverage = total_weight / sum(FUSION_WEIGHTS.values())
    return {"score": round(score, 4), "components": components, "coverage": round(coverage, 3)}


def confidence_band(score: float, margin: float, coverage: float, has_biometric: bool) -> str:
    """Deliberately conservative: 'high' requires a biometric signal."""
    if has_biometric and score >= 0.75 and margin >= 0.12 and coverage >= 0.6:
        return "high"
    if score >= 0.55 and margin >= 0.05:
        return "medium"
    return "low"


def build_notes(
    signals: dict[str, dict], coverage: float, confidence: str, components: list[dict]
) -> list[str]:
    notes: list[str] = []
    if "fingerprint" not in signals:
        notes.append("No fingerprint evidence — ranking relies on weaker signals.")
    if "face" not in signals:
        notes.append("No usable face embedding — no facial comparison was performed.")
    if coverage < 0.5:
        notes.append(
            "Less than half of the evidence weight was available for this case."
        )
    for comp in components:
        if comp["modality"] == "demographics" and "MISMATCH" in comp["detail"]:
            notes.append("Recorded sex does not match the estimate for this case.")
    if confidence == "low":
        notes.append(
            "Low confidence: treat this as a lead requiring independent verification."
        )
    notes.append(
        "This ranking is decision support only and is not a legal identification."
    )
    return notes