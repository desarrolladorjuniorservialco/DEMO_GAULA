# modules/placas/video/detector.py
from __future__ import annotations

import logging
from typing import NamedTuple

log = logging.getLogger(__name__)

_YOLO = None
_DEPS_OK: bool | None = None
MISSING_CMD = "pip install ultralytics"
_MODEL_NAME = "yolov8n.pt"  # nano — mínimo costo; reemplazar por modelo fine-tuned de placas


class Detection(NamedTuple):
    x1: int
    y1: int
    x2: int
    y2: int
    conf: float


def check_deps() -> bool:
    global _DEPS_OK
    if _DEPS_OK is None:
        try:
            from ultralytics import YOLO  # noqa: F401
            _DEPS_OK = True
        except ImportError:
            _DEPS_OK = False
    return _DEPS_OK


def get_model():
    global _YOLO
    if _YOLO is None:
        from ultralytics import YOLO
        _YOLO = YOLO(_MODEL_NAME)
        log.info("YOLO cargado: %s", _MODEL_NAME)
    return _YOLO


def detectar_frame(frame_bgr, conf_threshold: float = 0.35) -> list[Detection]:
    """Ejecuta YOLO sobre un frame BGR; devuelve lista de bounding boxes."""
    if not check_deps():
        return []
    model = get_model()
    results = model.predict(frame_bgr, conf=conf_threshold, verbose=False)
    out: list[Detection] = []
    for box in results[0].boxes:
        x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
        conf = float(box.conf[0])
        out.append(Detection(x1, y1, x2, y2, conf))
    return out
