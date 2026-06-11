# modules/placas/routes.py
import json
import os
import time

from flask import Response, jsonify, render_template, request, stream_with_context

from modules.auth.decorators import login_required
from modules.placas import engine, placas_bp

# ── Imagen (existente) ────────────────────────────────────────────────────────

@placas_bp.route("/")
@login_required
def index():
    return render_template("placas/index.html")


@placas_bp.route("/analizar", methods=["POST"])
@login_required
def analizar():
    if "imagen" not in request.files:
        return jsonify({"ok": False, "error": "No se envió archivo"}), 400

    archivo = request.files["imagen"]
    if not archivo.mimetype.startswith("image/"):
        return jsonify({"ok": False, "error": "El archivo no es una imagen"}), 400

    resultado = engine.reconocer_placa(archivo.read())
    return jsonify(resultado)


@placas_bp.route("/analizar-frame", methods=["POST"])
@login_required
def analizar_frame():
    """Recibe un frame JPEG del browser y devuelve la placa detectada (sin paneles)."""
    if "frame" not in request.files:
        return jsonify({"ok": False, "error": "No se envió frame"}), 400
    resultado = engine.reconocer_placa(request.files["frame"].read())
    resultado.pop("paneles", None)
    return jsonify(resultado)


# ── Video ─────────────────────────────────────────────────────────────────────

_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "videos")
_MAX_VIDEO_BYTES = int(os.getenv("MAX_VIDEO_MB", "200")) * 1024 * 1024
_ALLOWED_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


@placas_bp.route("/video")
@login_required
def video_index():
    return render_template("placas/video.html")


@placas_bp.route("/video/upload", methods=["POST"])
@login_required
def video_upload():
    from modules.placas.video.job_store import job_store
    from modules.placas.video import pipeline

    if "video" not in request.files:
        return jsonify({"ok": False, "error": "No se envió archivo"}), 400

    archivo = request.files["video"]
    ext = os.path.splitext(archivo.filename or "")[1].lower()
    if ext not in _ALLOWED_EXTS:
        return jsonify({"ok": False, "error": f"Formato no soportado: {ext}"}), 400

    os.makedirs(_UPLOAD_FOLDER, exist_ok=True)
    job = job_store.create("")
    dest = os.path.join(_UPLOAD_FOLDER, f"{job.job_id}{ext}")
    job.video_path = dest

    total = 0
    try:
        with open(dest, "wb") as fh:
            while True:
                chunk = archivo.stream.read(65_536)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_VIDEO_BYTES:
                    fh.close()
                    os.remove(dest)
                    lim = _MAX_VIDEO_BYTES // 1024 // 1024
                    return jsonify({"ok": False, "error": f"Video supera el límite de {lim} MB"}), 413
                fh.write(chunk)
    except OSError as exc:
        return jsonify({"ok": False, "error": f"Error al guardar archivo: {exc}"}), 500

    pipeline.iniciar_procesamiento(job.job_id)
    return jsonify({"ok": True, "job_id": job.job_id})


@placas_bp.route("/video/<job_id>/status")
@login_required
def video_status(job_id: str):
    from modules.placas.video.job_store import job_store
    job = job_store.get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Job no encontrado"}), 404
    return jsonify({"ok": True, **job.summary()})


@placas_bp.route("/video/<job_id>/results")
@login_required
def video_results(job_id: str):
    from modules.placas.video.job_store import job_store
    job = job_store.get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Job no encontrado"}), 404
    if job.estado not in ("done", "processing"):
        return jsonify({"ok": False, "error": f"Job en estado: {job.estado}"}), 400
    return jsonify({"ok": True, **job.full_result()})


@placas_bp.route("/video/<job_id>/stream")
@login_required
def video_stream(job_id: str):
    """SSE: emite progreso cada segundo hasta done/error."""
    from modules.placas.video.job_store import job_store
    job = job_store.get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Job no encontrado"}), 404

    def _generate():
        cursor = 0
        while True:
            nuevos = job.eventos[cursor:]
            cursor += len(nuevos)
            payload = {**job.summary(), "eventos": nuevos}
            yield f"data: {json.dumps(payload)}\n\n"
            if job.estado in ("done", "error"):
                break
            time.sleep(0.5)

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@placas_bp.route("/video/<job_id>", methods=["DELETE"])
@login_required
def video_delete(job_id: str):
    from modules.placas.video.job_store import job_store
    deleted = job_store.delete(job_id)
    return jsonify({"ok": deleted})
