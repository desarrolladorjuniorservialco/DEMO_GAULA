# modules/placas/video/detector.py
from __future__ import annotations

import logging
import os
from typing import NamedTuple

log = logging.getLogger(__name__)

_YOLO = None
_DEPS_OK: bool | None = None
_MODO: str | None = None  # "placas" | "fallback"
MISSING_CMD = "pip install ultralytics"

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODELO_PLACAS = os.getenv(
    "PLACAS_YOLO_MODEL", os.path.join(_ROOT, "models", "placas-yolov8n.pt")
)
_MODELO_COCO = "yolov8n.pt"
_CLASES_VEHICULO = {2, 3, 5, 7}  # COCO: car, motorcycle, bus, truck


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


def modo() -> str:
    """"placas" si existe el modelo fine-tuned; "fallback" (COCO + máscara amarilla)."""
    global _MODO
    if _MODO is None:
        _MODO = "placas" if os.path.exists(MODELO_PLACAS) else "fallback"
        if _MODO == "fallback":
            log.warning(
                "Modelo de placas no encontrado en %s — usando fallback COCO. "
                "Ejecuta: python scripts/descargar_modelo_placas.py",
                MODELO_PLACAS,
            )
    return _MODO


def get_model():
    global _YOLO
    if _YOLO is None:
        from ultralytics import YOLO
        nombre = MODELO_PLACAS if modo() == "placas" else _MODELO_COCO
        _YOLO = YOLO(nombre)
        log.info("YOLO cargado: %s (modo %s)", nombre, modo())
    return _YOLO


def detectar_frame(frame_bgr, conf_threshold: float = 0.30) -> list[Detection]:
    """Devuelve bounding boxes de PLACAS.

    Modo "placas": el modelo detecta placas directamente.
    Modo "fallback": COCO detecta vehículos; dentro de cada bbox se localiza la
    placa con la máscara amarilla HSV; si no hay región amarilla, se devuelve el
    bbox del vehículo completo.
    """
    if not check_deps():
        return []
    model = get_model()
    results = model.predict(frame_bgr, conf=conf_threshold, verbose=False)
    boxes = results[0].boxes
    if modo() == "placas":
        return [
            Detection(*(int(v) for v in b.xyxy[0]), float(b.conf[0])) for b in boxes
        ]
    return _placas_fallback(frame_bgr, boxes)


def _placas_fallback(frame_bgr, boxes) -> list[Detection]:
    from modules.placas.engine import _mask_amarilla, _regiones_desde_mask

    out: list[Detection] = []
    for b in boxes:
        if int(b.cls[0]) not in _CLASES_VEHICULO:
            continue
        x1, y1, x2, y2 = (int(v) for v in b.xyxy[0])
        conf = float(b.conf[0])
        roi = frame_bgr[y1:y2, x1:x2]
        if roi.size == 0:
            continue
        regiones = _regiones_desde_mask(_mask_amarilla(roi))
        if regiones:
            rx1, ry1, rx2, ry2 = max(
                regiones, key=lambda r: (r[2] - r[0]) * (r[3] - r[1])
            )
            out.append(Detection(x1 + rx1, y1 + ry1, x1 + rx2, y1 + ry2, conf))
        else:
            out.append(Detection(x1, y1, x2, y2, conf))
    return out
