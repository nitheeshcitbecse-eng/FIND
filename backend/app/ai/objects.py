"""Visual evidence: belongings / tattoo-region detection with YOLO.

YOLOv8n pretrained on COCO already recognises many belongings that matter in
these cases (backpack, handbag, cell phone, bottle, umbrella, shoes...).
Tattoo and scar detection needs a custom-trained model; until you train one,
tattoos are handled as officer-entered text plus the stored photo.
"""

from __future__ import annotations

import logging

from ..config import USE_YOLO

log = logging.getLogger(__name__)

_model = None
_mode = "unloaded"

BELONGING_CLASSES = {
    "backpack", "handbag", "suitcase", "cell phone", "bottle", "umbrella",
    "tie", "book", "clock", "watch", "wallet", "shoe", "cup", "knife",
    "scissors", "laptop", "remote", "keyboard",
}


def _load():
    global _model, _mode
    if _mode != "unloaded":
        return
    if not USE_YOLO:
        _mode = "disabled"
        return
    try:
        from ultralytics import YOLO

        _model = YOLO("yolov8n.pt")
        _mode = "yolo"
        log.info("Object detector: YOLOv8n")
    except Exception as exc:  # noqa: BLE001
        log.warning("Ultralytics unavailable (%s). Object detection disabled.", exc)
        _mode = "disabled"


def engine_name() -> str:
    _load()
    return "yolov8n" if _mode == "yolo" else "disabled"


def detect_objects(image_path: str, conf: float = 0.35) -> dict:
    _load()
    if _mode != "yolo" or _model is None:
        return {"labels": [], "detections": [], "engine": "disabled"}

    try:
        results = _model.predict(source=str(image_path), conf=conf, verbose=False)
    except Exception as exc:  # noqa: BLE001
        log.warning("YOLO inference failed: %s", exc)
        return {"labels": [], "detections": [], "engine": "yolov8n"}

    detections = []
    for result in results:
        names = result.names
        for box in result.boxes:
            label = names[int(box.cls)]
            detections.append(
                {
                    "label": label,
                    "confidence": round(float(box.conf), 3),
                    "bbox": [round(float(v), 1) for v in box.xyxy[0].tolist()],
                    "is_belonging": label in BELONGING_CLASSES,
                }
            )

    detections.sort(key=lambda d: d["confidence"], reverse=True)
    labels = sorted({d["label"] for d in detections})
    return {"labels": labels, "detections": detections[:20], "engine": "yolov8n"}