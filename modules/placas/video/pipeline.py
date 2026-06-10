# modules/placas/video/pipeline.py
from __future__ import annotations

import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor

import cv2

from modules.placas.engine import ALLOW, extraer_placas_de_texto, _get_reader
from .detector import Detection, check_deps as yolo_ok, detectar_frame
from .tracker import PlacaTracker
from .ocr_cache import OcrTrackCache
from .schemas import FrameResult, PlacaDeteccion, VideoJob
from .job_store import job_store

log = logging.getLogger(__name__)

# ── Configuración de rendimiento ──────────────────────────────────────────────
YOLO_EVERY_N_FRAMES = 5      # inferencia YOLO 1 de cada N frames (80% menos llamadas)
MAX_YOLO_DIM = 640           # resize máximo antes de YOLO para reducir cómputo
OCR_WORKERS = 2              # hilos paralelos de EasyOCR
MAX_CONCURRENT_JOBS = 2      # límite de videos procesándose en paralelo

_semaphore = threading.Semaphore(MAX_CONCURRENT_JOBS)
_executor = ThreadPoolExecutor(max_workers=OCR_WORKERS, thread_name_prefix="placas-ocr")


# ── Helpers OCR ───────────────────────────────────────────────────────────────

def _recortar_y_ocr(frame_bgr, x1: int, y1: int, x2: int, y2: int) -> str | None:
    """Recorta región de placa, hace upscale ×3 y aplica EasyOCR (igual que engine.py pase B)."""
    pad = 6
    h, w = frame_bgr.shape[:2]
    cx1, cy1 = max(0, x1 - pad), max(0, y1 - pad)
    cx2, cy2 = min(w, x2 + pad), min(h, y2 + pad)
    crop = frame_bgr[cy1:cy2, cx1:cx2]
    if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 16:
        return None

    up = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    reader = _get_reader()
    try:
        dets = reader.readtext(up, allowlist=ALLOW, detail=1, paragraph=False)
    except Exception:
        return None

    texto_concat = "".join(
        re.sub(r"[^A-Z0-9]", "", t.upper()) for _, t, _ in dets
    )
    candidatos = extraer_placas_de_texto(texto_concat)
    if candidatos:
        return candidatos[0][0]
    for _, t, _ in dets:
        candidatos = extraer_placas_de_texto(t)
        if candidatos:
            return candidatos[0][0]
    return None


def _resize_para_yolo(frame):
    h, w = frame.shape[:2]
    if max(h, w) <= MAX_YOLO_DIM:
        return frame, 1.0
    scale = MAX_YOLO_DIM / max(h, w)
    return cv2.resize(frame, (int(w * scale), int(h * scale))), scale


def _escalar_detecciones(dets: list[Detection], scale: float) -> list[Detection]:
    if scale == 1.0:
        return dets
    return [
        Detection(
            int(d.x1 / scale), int(d.y1 / scale),
            int(d.x2 / scale), int(d.y2 / scale),
            d.conf,
        )
        for d in dets
    ]


# ── Pipeline principal ────────────────────────────────────────────────────────

def _procesar_video(job: VideoJob) -> None:
    """Ejecutado en background thread. Modifica el job in-place."""
    cap = cv2.VideoCapture(job.video_path)
    if not cap.isOpened():
        job.estado = "error"
        job.error = "No se pudo abrir el video"
        return

    job.fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    job.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    job.duracion_s = job.total_frames / job.fps
    job.estado = "processing"

    tracker = PlacaTracker()
    ocr_cache = OcrTrackCache()
    frame_idx = 0
    last_tracked: list = []
    futures: dict = {}  # future -> (track_id, PlacaDeteccion)

    def _flush_futures(wait: bool = False) -> None:
        done = [f for f in list(futures) if wait or f.done()]
        for f in done:
            track_id, det = futures.pop(f)
            try:
                placa = f.result(timeout=5 if wait else 0)
                ocr_cache.registrar(track_id, placa)
                det.placa = placa
            except Exception as exc:
                log.debug("OCR future track %d: %s", track_id, exc)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            ts_ms = int(frame_idx * 1000 / job.fps)
            frame_result = FrameResult(ts_ms=ts_ms, frame_idx=frame_idx)

            # ── Detección YOLO (1 de cada N frames) ──────────────────────────
            if frame_idx % YOLO_EVERY_N_FRAMES == 0:
                yolo_frame, scale = _resize_para_yolo(frame)
                raw_dets = detectar_frame(yolo_frame) if yolo_ok() else []
                raw_dets = _escalar_detecciones(raw_dets, scale)
                last_tracked = tracker.update(raw_dets, frame.shape)

            _flush_futures()

            # ── Construir detecciones del frame ──────────────────────────────
            h, w = frame.shape[:2]
            for obj in last_tracked:
                es_nuevo = ocr_cache.es_nuevo(obj.track_id)
                necesita = ocr_cache.necesita_ocr(obj.track_id)
                placa_actual = ocr_cache.obtener(obj.track_id)

                det = PlacaDeteccion(
                    track_id=obj.track_id,
                    placa=placa_actual,
                    tipo=None,
                    confianza=obj.conf,
                    bbox_norm=(obj.x1 / w, obj.y1 / h, obj.x2 / w, obj.y2 / h),
                    nuevo=es_nuevo,
                )
                frame_result.detecciones.append(det)

                if necesita:
                    frame_copy = frame.copy()
                    future = _executor.submit(
                        _recortar_y_ocr, frame_copy, obj.x1, obj.y1, obj.x2, obj.y2
                    )
                    futures[future] = (obj.track_id, det)

            if frame_result.detecciones:
                job.resultados.append(frame_result)

            frame_idx += 1
            job.frames_procesados = frame_idx
            job.progreso = frame_idx / max(job.total_frames, 1)

    finally:
        cap.release()
        _flush_futures(wait=True)

    job.estado = "done"
    job.progreso = 1.0
    log.info(
        "Video job %s completado: %d frames procesados, %d con detecciones",
        job.job_id, frame_idx, len(job.resultados),
    )


def iniciar_procesamiento(job_id: str) -> None:
    """Lanza el pipeline en un thread daemon. Llamar desde el route tras guardar el archivo."""
    job = job_store.get(job_id)
    if not job:
        log.warning("iniciar_procesamiento: job_id %s no encontrado", job_id)
        return

    def _run() -> None:
        with _semaphore:
            try:
                _procesar_video(job)
            except Exception as exc:
                log.exception("Error fatal en job %s", job_id)
                job.estado = "error"
                job.error = str(exc)

    t = threading.Thread(target=_run, daemon=True, name=f"placas-video-{job_id[:8]}")
    t.start()
