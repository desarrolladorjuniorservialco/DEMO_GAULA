# modules/placas/video/schemas.py
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlacaDeteccion:
    track_id: int
    placa: str | None
    tipo: str | None                              # "CARRO" | "MOTO" | None
    confianza: float
    bbox_norm: tuple[float, float, float, float]  # x1,y1,x2,y2 en [0..1]
    nuevo: bool                                   # primera aparición del track_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "placa": self.placa,
            "tipo": self.tipo,
            "conf": round(self.confianza, 2),
            "bbox": list(self.bbox_norm),
            "nuevo": self.nuevo,
        }


@dataclass(slots=True)
class FrameResult:
    ts_ms: int                                    # milisegundos desde inicio del video
    frame_idx: int
    detecciones: list[PlacaDeteccion] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ts_ms": self.ts_ms,
            "frame": self.frame_idx,
            "detecciones": [d.as_dict() for d in self.detecciones],
        }


@dataclass
class VideoJob:
    job_id: str
    estado: str = "pending"       # pending | processing | done | error
    progreso: float = 0.0         # 0.0 – 1.0
    fps: float = 0.0
    duracion_s: float = 0.0
    total_frames: int = 0
    frames_procesados: int = 0
    resultados: list[FrameResult] = field(default_factory=list)
    error: str | None = None
    video_path: str = ""
    creado_en: float = field(default_factory=time.time)

    def summary(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "estado": self.estado,
            "progreso": round(self.progreso, 3),
            "fps": self.fps,
            "duracion_s": round(self.duracion_s, 2),
            "total_frames": self.total_frames,
            "frames_procesados": self.frames_procesados,
            "error": self.error,
        }

    def full_result(self) -> dict[str, Any]:
        return {
            **self.summary(),
            "timeline": [r.as_dict() for r in self.resultados],
        }
