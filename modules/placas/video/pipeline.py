# modules/placas/video/pipeline.py
from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor

import cv2

from modules.placas.engine import ALLOW, _get_reader
from . import detector
from .detector import Detection, check_deps as yolo_ok, detectar_frame
from .tracker import PlacaTracker
from .best_frames import TrackCropBuffer
from .plate_votes import PlateVoter, ConteoVideo
from .schemas import VideoJob
from .job_store import job_store

log = logging.getLogger(__name__)

# ── Configuración de rendimiento ──────────────────────────────────────────────
YOLO_EVERY_N_FRAMES = 2      # inferencia YOLO 1 de cada N frames
MAX_YOLO_DIM = 640           # resize máximo antes de YOLO
OCR_WORKERS = 2              # hilos paralelos de EasyOCR
MAX_CONCURRENT_JOBS = 2      # videos procesándose en paralelo
CIERRE_GAP_S = 1.5           # s de video sin ver el track → se cierra
OCR_PARCIAL_CADA_S = 2.0     # OCR temprano para tracks largos aún abiertos
CROP_PAD_PX = 6

_semaphore = threading.Semaphore(MAX_CONCURRENT_JOBS)
_executor = ThreadPoolExecutor(max_workers=OCR_WORKERS, thread_name_prefix="placas-ocr")


# ── OCR sobre recorte de placa ────────────────────────────────────────────────

def _ocr_recorte(crop_bgr) -> tuple[str, float]:
    """Upscale ×3 + EasyOCR con allowlist. Devuelve (texto, confianza_media)."""
    try:
        up = cv2.resize(crop_bgr, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        reader = _get_reader()
        dets = reader.readtext(up, allowlist=ALLOW, detail=1, paragraph=False)
    except Exception:
        return "", 0.0
    if not dets:
        return "", 0.0
    texto = "".join(t for _, t, _ in dets)
    conf = sum(float(c) for _, _, c in dets) / len(dets)
    return texto, conf


def _recortar(frame_bgr, x1: int, y1: int, x2: int, y2: int):
    h, w = frame_bgr.shape[:2]
    cx1, cy1 = max(0, x1 - CROP_PAD_PX), max(0, y1 - CROP_PAD_PX)
    cx2, cy2 = min(w, x2 + CROP_PAD_PX), min(h, y2 + CROP_PAD_PX)
    return frame_bgr[cy1:cy2, cx1:cx2]


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
            int(d.x2 / scale), int(d.y2 / scale), d.conf,
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
    job.modelo_detector = detector.modo() if yolo_ok() else "sin-yolo"
    job.estado = "processing"

    tracker = PlacaTracker()
    crops = TrackCropBuffer()
    voter = PlateVoter()
    conteo = ConteoVideo()
    job.eventos = conteo.eventos  # misma lista: appends visibles para el SSE

    # track_id -> {"primer_ts", "ultimo_ts", "confirmado", "ultimo_ocr"}
    abiertos: dict[int, dict] = {}
    # OCR parciales en vuelo: alimentan el voter al completarse
    parciales: list[tuple[Future, int]] = []
    # tracks cerrados esperando sus OCRs finales: track_id -> (futures, estado)
    cierres: dict[int, tuple[list[Future], dict]] = {}

    def _drenar_parciales(wait: bool = False) -> None:
        restantes = []
        for f, tid in parciales:
            if wait or f.done():
                try:
                    texto, conf = f.result(timeout=10 if wait else 0)
                    voter.agregar_lectura(tid, texto, conf)
                except Exception as exc:
                    log.debug("OCR parcial track %d: %s", tid, exc)
            else:
                restantes.append((f, tid))
        parciales[:] = restantes

    def _iniciar_cierre(tid: int) -> None:
        est = abiertos.pop(tid)
        if not est["confirmado"]:
            crops.descartar(tid)        # track fugaz: falso positivo
            return
        futs = [_executor.submit(_ocr_recorte, c) for c in crops.mejores(tid, 3)]
        crops.descartar(tid)
        cierres[tid] = (futs, est)

    def _resolver_cierres(wait: bool = False) -> None:
        for tid in list(cierres):
            futs, est = cierres[tid]
            if not wait and not all(f.done() for f in futs):
                continue
            for f in futs:
                try:
                    texto, conf = f.result(timeout=15 if wait else 0)
                    voter.agregar_lectura(tid, texto, conf)
                except Exception as exc:
                    log.debug("OCR cierre track %d: %s", tid, exc)
            placa, tipo, conf_voto = voter.resolver(tid)
            conteo.cerrar_track(
                tid, placa, tipo, conf_voto, est["primer_ts"], est["ultimo_ts"]
            )
            del cierres[tid]

    frame_idx = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            ts_s = frame_idx / job.fps

            if frame_idx % YOLO_EVERY_N_FRAMES == 0:
                yolo_frame, scale = _resize_para_yolo(frame)
                raw = detectar_frame(yolo_frame) if yolo_ok() else []
                raw = _escalar_detecciones(raw, scale)
                tracked = tracker.update(raw, frame.shape)

                vistos = set()
                for obj in tracked:
                    vistos.add(obj.track_id)
                    est = abiertos.setdefault(
                        obj.track_id,
                        {"primer_ts": ts_s, "ultimo_ts": ts_s,
                         "confirmado": False, "ultimo_ocr": ts_s},
                    )
                    est["ultimo_ts"] = ts_s
                    crops.agregar(
                        obj.track_id, _recortar(frame, obj.x1, obj.y1, obj.x2, obj.y2)
                    )
                    if not est["confirmado"] and tracker.hits.es_confirmado(obj.track_id):
                        est["confirmado"] = True
                        conteo.confirmar_vehiculo(obj.track_id, ts_s)

                    # OCR temprano para tracks largos (feedback antes del cierre)
                    if (est["confirmado"]
                            and ts_s - est["ultimo_ocr"] >= OCR_PARCIAL_CADA_S):
                        est["ultimo_ocr"] = ts_s
                        mejores = crops.mejores(obj.track_id, 1)
                        if mejores:
                            parciales.append(
                                (_executor.submit(_ocr_recorte, mejores[0]),
                                 obj.track_id)
                            )

                # Cerrar tracks que desaparecieron hace > CIERRE_GAP_S
                for tid in [t for t, e in abiertos.items()
                            if t not in vistos and ts_s - e["ultimo_ts"] > CIERRE_GAP_S]:
                    _iniciar_cierre(tid)

            _drenar_parciales()
            _resolver_cierres()

            frame_idx += 1
            job.frames_procesados = frame_idx
            job.progreso = frame_idx / max(job.total_frames, 1)
            job.vehiculos = conteo.vehiculos
            job.placas_leidas = conteo.placas_leidas
            job.sin_lectura = conteo.sin_lectura

    finally:
        cap.release()
        for tid in list(abiertos):
            _iniciar_cierre(tid)
        _drenar_parciales(wait=True)
        _resolver_cierres(wait=True)
        job.vehiculos = conteo.vehiculos
        job.placas_leidas = conteo.placas_leidas
        job.sin_lectura = conteo.sin_lectura

    job.estado = "done"
    job.progreso = 1.0
    log.info(
        "Video job %s: %d frames, %d vehiculos, %d placas, %d sin lectura",
        job.job_id, frame_idx, job.vehiculos, job.placas_leidas, job.sin_lectura,
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
