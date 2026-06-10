# modules/placas/video/job_store.py
from __future__ import annotations

import logging
import os
import threading
import time
import uuid

from .schemas import VideoJob

log = logging.getLogger(__name__)

_TTL_SECONDS = 7200  # 2 horas


class VideoJobStore:
    """Registro en memoria de jobs de procesamiento de video."""

    def __init__(self) -> None:
        self._jobs: dict[str, VideoJob] = {}
        self._lock = threading.Lock()

    def create(self, video_path: str) -> VideoJob:
        job = VideoJob(job_id=uuid.uuid4().hex, video_path=video_path)
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> VideoJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def delete(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if job and job.video_path and os.path.exists(job.video_path):
            try:
                os.remove(job.video_path)
            except OSError as exc:
                log.warning("No se pudo eliminar %s: %s", job.video_path, exc)
        return job is not None

    def purge_stale(self) -> int:
        """Elimina jobs más viejos que TTL. Llamar periódicamente."""
        cutoff = time.time() - _TTL_SECONDS
        with self._lock:
            stale = [jid for jid, j in self._jobs.items() if j.creado_en < cutoff]
        for jid in stale:
            self.delete(jid)
        if stale:
            log.info("VideoJobStore: %d jobs obsoletos eliminados", len(stale))
        return len(stale)


# Singleton compartido por routes y pipeline
job_store = VideoJobStore()
