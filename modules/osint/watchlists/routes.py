from __future__ import annotations

import json
from datetime import datetime

from flask import jsonify, render_template, request, session

from models import db
from models.osint import WatchlistOsint

from modules.osint.auth import login_required
from modules.osint.core.engine import UniversalOsintEngine
from modules.osint.watchlists import watchlists_osint_bp

_ENGINE = UniversalOsintEngine()


def _serialize_watchlist(item: WatchlistOsint) -> dict:
    return {
        "id": item.id,
        "nombre": item.nombre,
        "target": item.target,
        "target_type": item.target_type,
        "source_hint": item.source_hint,
        "frecuencia_minutos": item.frecuencia_minutos,
        "activo": bool(item.activo),
        "last_run_at": item.last_run_at.isoformat() if item.last_run_at else "",
        "last_risk_level": item.last_risk_level or "Bajo",
        "last_risk_score": item.last_risk_score or 0,
        "notas": item.notas or "",
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
        "created_by": item.created_by or "",
    }


def _list_watchlists() -> list[dict]:
    items = WatchlistOsint.query.order_by(WatchlistOsint.created_at.desc()).all()
    return [_serialize_watchlist(item) for item in items]


def _upsert_from_payload(item: WatchlistOsint, payload: dict) -> WatchlistOsint:
    item.nombre = (payload.get("nombre") or item.nombre or "").strip() or item.nombre
    item.target = (payload.get("target") or item.target or "").strip() or item.target
    item.target_type = (payload.get("target_type") or item.target_type or "unknown").strip() or "unknown"
    item.source_hint = (payload.get("source_hint") or item.source_hint or "all").strip() or "all"
    item.frecuencia_minutos = int(payload.get("frecuencia_minutos") or item.frecuencia_minutos or 1440)
    item.notas = payload.get("notas", item.notas)
    item.updated_by = str(session.get("user") or "system")
    return item


@watchlists_osint_bp.route("/watchlists", methods=["GET", "POST"])
@login_required
def watchlists():
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form.to_dict()
        nombre = (payload.get("nombre") or "").strip()
        target = (payload.get("target") or "").strip()

        if not nombre or not target:
            if request.is_json:
                return jsonify({"ok": False, "error": "nombre y target son requeridos"}), 400
            return render_template(
                "osint/watchlists.html",
                items=_list_watchlists(),
                error="nombre y target son requeridos",
            ), 400

        item = WatchlistOsint(
            nombre=nombre,
            target=target,
            target_type=(payload.get("target_type") or "unknown").strip() or "unknown",
            source_hint=(payload.get("source_hint") or "all").strip() or "all",
            frecuencia_minutos=int(payload.get("frecuencia_minutos") or 1440),
            notas=payload.get("notas", ""),
            created_by=str(session.get("user") or "system"),
            updated_by=str(session.get("user") or "system"),
        )
        db.session.add(item)
        db.session.commit()

        if request.is_json:
            return jsonify({"ok": True, "item": _serialize_watchlist(item)})
        return render_template(
            "osint/watchlists.html",
            items=_list_watchlists(),
            success="Watchlist creada correctamente.",
        )

    return render_template(
        "osint/watchlists.html",
        items=_list_watchlists(),
    )


@watchlists_osint_bp.route("/watchlists/api")
@login_required
def watchlists_api():
    return jsonify({"ok": True, "items": _list_watchlists()})


@watchlists_osint_bp.route("/watchlists/<int:item_id>/toggle", methods=["POST"])
@login_required
def watchlists_toggle(item_id: int):
    item = db.session.get(WatchlistOsint, item_id)
    if not item:
        return jsonify({"ok": False, "error": "Watchlist no encontrada"}), 404
    item.activo = not bool(item.activo)
    item.updated_by = str(session.get("user") or "system")
    db.session.commit()
    return jsonify({"ok": True, "item": _serialize_watchlist(item)})


@watchlists_osint_bp.route("/watchlists/<int:item_id>/delete", methods=["POST"])
@login_required
def watchlists_delete(item_id: int):
    item = db.session.get(WatchlistOsint, item_id)
    if not item:
        return jsonify({"ok": False, "error": "Watchlist no encontrada"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


@watchlists_osint_bp.route("/watchlists/<int:item_id>/run", methods=["POST"])
@login_required
def watchlists_run(item_id: int):
    item = db.session.get(WatchlistOsint, item_id)
    if not item:
        return jsonify({"ok": False, "error": "Watchlist no encontrada"}), 404

    result = _ENGINE.search(
        target=item.target,
        source_hint=item.source_hint or "all",
        persist=True,
        user_name=session.get("user"),
        created_by=str(session.get("user") or "system"),
    )
    risk = result.get("risk", {})
    item.last_run_at = datetime.utcnow()
    item.last_risk_level = risk.get("level", "Bajo")
    item.last_risk_score = int(risk.get("score", 0) or 0)
    item.last_result_json = json.dumps(result, ensure_ascii=False, default=str)
    item.updated_by = str(session.get("user") or "system")
    db.session.commit()
    return jsonify({"ok": True, "item": _serialize_watchlist(item), "result": result})
