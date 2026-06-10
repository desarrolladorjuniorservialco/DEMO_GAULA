# modules/placas/video/ocr_cache.py
from __future__ import annotations

import threading

_MIN_FRAMES_BEFORE_RETRY = 30  # reintentar OCR si N frames sin resultado


class OcrTrackCache:
    """Por cada track_id, evita repetir OCR si ya se obtuvo una placa."""

    def __init__(self) -> None:
        self._placas: dict[int, str | None] = {}   # track_id -> placa (None = intentado sin resultado)
        self._intentos: dict[int, int] = {}         # track_id -> frames sin placa
        self._lock = threading.Lock()

    def es_nuevo(self, track_id: int) -> bool:
        with self._lock:
            return track_id not in self._placas

    def necesita_ocr(self, track_id: int) -> bool:
        with self._lock:
            if track_id not in self._placas:
                return True
            if self._placas[track_id] is not None:
                return False
            # Tiene None: retry después de N frames
            intentos = self._intentos.get(track_id, 0) + 1
            self._intentos[track_id] = intentos
            return intentos % _MIN_FRAMES_BEFORE_RETRY == 0

    def registrar(self, track_id: int, placa: str | None) -> None:
        with self._lock:
            self._placas[track_id] = placa
            if placa is None and track_id not in self._intentos:
                self._intentos[track_id] = 0

    def obtener(self, track_id: int) -> str | None:
        with self._lock:
            return self._placas.get(track_id)
