from __future__ import annotations

import cv2
import numpy as np

K_MEJORES_DEFAULT = 5
MIN_ALTO_PX = 12


def puntuar_recorte(crop_bgr: np.ndarray) -> float:
    """Score de calidad = área × varianza del Laplaciano (tamaño × nitidez)."""
    if crop_bgr is None or crop_bgr.size == 0:
        return 0.0
    h, w = crop_bgr.shape[:2]
    if h < MIN_ALTO_PX:
        return 0.0
    gris = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY) if crop_bgr.ndim == 3 else crop_bgr
    nitidez = float(cv2.Laplacian(gris, cv2.CV_64F).var())
    return float(h * w) * max(nitidez, 1.0)


class TrackCropBuffer:
    """Por cada track_id conserva los K mejores recortes de placa vistos."""

    def __init__(self, k: int = K_MEJORES_DEFAULT) -> None:
        self._k = k
        self._crops: dict[int, list[tuple[float, np.ndarray]]] = {}

    def agregar(self, track_id: int, crop_bgr: np.ndarray) -> None:
        score = puntuar_recorte(crop_bgr)
        if score <= 0.0:
            return
        lista = self._crops.setdefault(track_id, [])
        lista.append((score, crop_bgr.copy()))
        lista.sort(key=lambda t: t[0], reverse=True)
        del lista[self._k:]

    def mejores(self, track_id: int, n: int = 3) -> list[np.ndarray]:
        return [c for _, c in self._crops.get(track_id, [])[:n]]

    def descartar(self, track_id: int) -> None:
        self._crops.pop(track_id, None)
