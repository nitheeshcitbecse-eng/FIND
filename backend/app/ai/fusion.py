"""Biometric fusion for the govern_db fingerprint+face comparison.

Weights are renormalised over the modalities that actually have evidence, so
a probe with only a fingerprint is not penalised for having no face photo —
its score just carries lower confidence.

Shared by both identification entry points: routers/persons.py::identify_by_fingerprint
(an ad-hoc share-intent capture) and routers/cases.py::run_match (a case's
stored evidence). Neither exposes a ranked list — this always resolves to a
single matched/not-matched verdict, which is decision support only: a human
verifier still confirms before a case is marked identified.
"""

from __future__ import annotations

from ..config import FUSION_WEIGHTS


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


def simple_confidence_band(score: float, threshold: float) -> str:
    """Confidence label for a single matched/not-matched biometric verdict.

    Shared by identify_by_fingerprint and run_match so both endpoints label
    the same score the same way.
    """
    if score >= 0.75:
        return "high"
    if score >= threshold:
        return "medium"
    return "low"