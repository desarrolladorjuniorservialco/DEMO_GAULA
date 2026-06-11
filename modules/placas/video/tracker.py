# modules/placas/video/tracker.py
from __future__ import annotations

import logging

import numpy as np

from .detector import Detection

log = logging.getLogger(__name__)

MISSING_CMD = "pip install supervision"


class TrackedObject:
    __slots__ = ("track_id", "x1", "y1", "x2", "y2", "conf")

    def __init__(self, track_id: int, x1: int, y1: int, x2: int, y2: int, conf: float):
        self.track_id = track_id
        self.x1, self.y1, self.x2, self.y2, self.conf = x1, y1, x2, y2, conf


MIN_HITS_CONFIRMACION = 3


class ContadorHits:
    """Cuenta apariciones por track_id; un track se confirma tras min_hits."""

    def __init__(self, min_hits: int = MIN_HITS_CONFIRMACION) -> None:
        self._min = min_hits
        self._hits: dict[int, int] = {}

    def registrar(self, track_ids: list[int]) -> None:
        for tid in track_ids:
            self._hits[tid] = self._hits.get(tid, 0) + 1

    def es_confirmado(self, track_id: int) -> bool:
        return self._hits.get(track_id, 0) >= self._min


class PlacaTracker:
    """Wrapper sobre supervision ByteTrack. Stateful — una instancia por job de video."""

    def __init__(self) -> None:
        self.hits = ContadorHits()
        self._ok = False
        self._next_id = 0
        try:
            from supervision import ByteTrack, Detections  # noqa: F401
            self._ByteTrack = ByteTrack
            self._Detections = Detections
            self._tracker = ByteTrack()
            self._ok = True
        except ImportError:
            log.warning("supervision no instalado — tracking desactivado. %s", MISSING_CMD)

    def update(self, detections: list[Detection], frame_shape: tuple) -> list[TrackedObject]:
        if not self._ok:
            return self._fallback(detections)
        if not detections:
            return []

        xyxy = np.array([[d.x1, d.y1, d.x2, d.y2] for d in detections], dtype=float)
        confs = np.array([d.conf for d in detections])
        class_ids = np.zeros(len(detections), dtype=int)

        sv_dets = self._Detections(xyxy=xyxy, confidence=confs, class_id=class_ids)
        tracked = self._tracker.update_with_detections(sv_dets)

        out: list[TrackedObject] = []
        for i, tid in enumerate(tracked.tracker_id):
            x1, y1, x2, y2 = (int(v) for v in tracked.xyxy[i])
            conf = float(tracked.confidence[i]) if tracked.confidence is not None else 0.5
            out.append(TrackedObject(int(tid), x1, y1, x2, y2, conf))
        self.hits.registrar([o.track_id for o in out])
        return out

    def _fallback(self, detections: list[Detection]) -> list[TrackedObject]:
        """Sin tracker: IDs secuenciales sin persistencia entre frames."""
        out = []
        for d in detections:
            self._next_id += 1
            out.append(TrackedObject(self._next_id, d.x1, d.y1, d.x2, d.y2, d.conf))
        return out
