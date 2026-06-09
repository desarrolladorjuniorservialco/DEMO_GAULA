from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from xml.etree import ElementTree as ET

from flask import Response, jsonify, make_response, render_template, request, session

from models import db
from models.osint import ConsultaOsint, FuenteOsint, ResultadoOsint

from modules.osint.auth import login_required
from modules.osint.core.engine import UniversalOsintEngine
from modules.osint.history import history_osint_bp

_ENGINE = UniversalOsintEngine()


def _risk_from_results(results: list[ResultadoOsint]) -> dict:
    if not results:
        return {"score": 0, "level": "Bajo"}

    relevancias = [float(r.relevancia or 0) for r in results]
    max_rel = max(relevancias)
    avg_rel = sum(relevancias) / len(relevancias)
    score = min(20, int(round((max_rel * 12) + (avg_rel * 8) + min(len(results), 4))))

    if score >= 16:
        level = "Crítico"
    elif score >= 11:
        level = "Alto"
    elif score >= 6:
        level = "Medio"
    else:
        level = "Bajo"

    return {"score": score, "level": level}


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _serialize_consulta(consulta: ConsultaOsint) -> dict:
    resultados = list(consulta.resultados or [])
    risk = _risk_from_results(resultados)
    fuente = consulta.fuente.nombre if consulta.fuente else ""
    latest = max((r.created_at for r in resultados if r.created_at), default=consulta.created_at)

    return {
        "id": consulta.id,
        "fuente": fuente,
        "tipo_consulta": consulta.tipo_consulta or "",
        "target": consulta.valor_consultado or "",
        "target_type": consulta.entity_type or "",
        "estado": consulta.estado or "",
        "usuario_id": consulta.usuario_id,
        "created_at": consulta.created_at.isoformat() if consulta.created_at else "",
        "updated_at": latest.isoformat() if latest else "",
        "results_count": len(resultados),
        "risk": risk,
        "results": [
            {
                "id": r.id,
                "tipo_hallazgo": r.tipo_hallazgo or "",
                "titulo": r.titulo or "",
                "descripcion": r.descripcion or "",
                "relevancia": float(r.relevancia or 0),
                "verificado": bool(r.verificado),
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in resultados
        ],
    }


def _history_facets(consultas: list[ConsultaOsint]) -> dict:
    return {
        "target_types": sorted(
            {
                consulta.entity_type or "unknown"
                for consulta in consultas
            }
        ),
        "sources": sorted(
            {
                consulta.fuente.nombre if consulta.fuente else consulta.tipo_consulta or "unknown"
                for consulta in consultas
            }
        ),
    }


def _query_history():
    q = request.args.get("q", "").strip()
    source = request.args.get("source", "all").strip() or "all"
    risk = request.args.get("risk", "all").strip() or "all"
    target_type = request.args.get("target_type", "all").strip() or "all"
    date_from = _parse_date(request.args.get("from"))
    date_to = _parse_date(request.args.get("to"))
    page = max(int(request.args.get("page", 1) or 1), 1)
    page_size = min(max(int(request.args.get("limit", 20) or 20), 5), 100)

    consultas = ConsultaOsint.query.order_by(ConsultaOsint.created_at.desc()).all()
    facets = _history_facets(consultas)

    rows = []
    for consulta in consultas:
        if q and q.lower() not in (consulta.valor_consultado or "").lower():
            continue
        if source != "all":
            fuente_nombre = consulta.fuente.nombre if consulta.fuente else ""
            fuente_tipo = consulta.fuente.tipo if consulta.fuente else ""
            if source not in {fuente_nombre, fuente_tipo, consulta.tipo_consulta or ""}:
                continue
        if target_type != "all" and (consulta.entity_type or "") != target_type:
            continue
        if date_from and consulta.created_at and consulta.created_at < date_from:
            continue
        if date_to and consulta.created_at and consulta.created_at > date_to:
            continue

        payload = _serialize_consulta(consulta)
        if risk != "all" and payload["risk"]["level"].lower() != risk.lower():
            continue
        rows.append(payload)

    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]

    return {
        "rows": page_rows,
        "total": total,
        "page": page,
        "limit": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
        "filters": {
            "q": q,
            "source": source,
            "risk": risk,
            "target_type": target_type,
            "from": request.args.get("from", ""),
            "to": request.args.get("to", ""),
        },
        "facets": facets,
    }


def _history_csv(rows: list[dict]) -> Response:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "target",
            "target_type",
            "fuente",
            "estado",
            "risk_level",
            "risk_score",
            "results_count",
            "created_at",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "id": row["id"],
                "target": row["target"],
                "target_type": row["target_type"],
                "fuente": row["fuente"],
                "estado": row["estado"],
                "risk_level": row["risk"]["level"],
                "risk_score": row["risk"]["score"],
                "results_count": row["results_count"],
                "created_at": row["created_at"],
            }
        )

    resp = make_response(buffer.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=osint_history.csv"
    return resp


def _history_json(rows: list[dict]) -> Response:
    resp = make_response(json.dumps(rows, ensure_ascii=False, indent=2))
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=osint_history.json"
    return resp


def _consulta_graphml(consulta: ConsultaOsint) -> Response:
    root = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
    ET.SubElement(root, "key", id="label", attrib={"for": "node", "attr.name": "label", "attr.type": "string"})
    ET.SubElement(root, "key", id="type", attrib={"for": "node", "attr.name": "type", "attr.type": "string"})
    ET.SubElement(root, "key", id="relation", attrib={"for": "edge", "attr.name": "relation", "attr.type": "string"})
    graph = ET.SubElement(root, "graph", id=f"consulta_{consulta.id}", edgedefault="directed")

    target_id = f"consulta_{consulta.id}"
    node = ET.SubElement(graph, "node", id=target_id)
    ET.SubElement(node, "data", key="label").text = consulta.valor_consultado or ""
    ET.SubElement(node, "data", key="type").text = consulta.entity_type or "unknown"

    for result in consulta.resultados or []:
        node_id = f"r_{result.id}"
        node = ET.SubElement(graph, "node", id=node_id)
        ET.SubElement(node, "data", key="label").text = result.titulo or result.tipo_hallazgo or ""
        ET.SubElement(node, "data", key="type").text = result.tipo_hallazgo or "resultado"
        edge = ET.SubElement(graph, "edge", source=target_id, target=node_id)
        ET.SubElement(edge, "data", key="relation").text = result.tipo_hallazgo or "hallazgo"

    xml_payload = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    resp = make_response(xml_payload)
    resp.headers["Content-Type"] = "application/graphml+xml; charset=utf-8"
    resp.headers["Content-Disposition"] = f"attachment; filename=osint_consulta_{consulta.id}.graphml"
    return resp


@history_osint_bp.route("/history")
@login_required
def history():
    payload = _query_history()
    return render_template(
        "osint/history.html",
        entries=payload["rows"],
        total=payload["total"],
        page=payload["page"],
        pages=payload["pages"],
        limit=payload["limit"],
        filters=payload["filters"],
        target_types=["all", *payload["facets"]["target_types"]] if payload["facets"]["target_types"] else ["all"],
        sources=["all", *payload["facets"]["sources"]] if payload["facets"]["sources"] else ["all"],
    )


@history_osint_bp.route("/history/api")
@login_required
def history_api():
    payload = _query_history()
    return jsonify(payload)


@history_osint_bp.route("/history/export/<format>")
@login_required
def history_export(format: str):
    payload = _query_history()
    rows = payload["rows"]
    if format == "csv":
        return _history_csv(rows)
    if format == "json":
        return _history_json(rows)
    return jsonify({"ok": False, "error": "Formato de exportación no soportado"}), 400


@history_osint_bp.route("/history/<int:consulta_id>/replay", methods=["POST"])
@login_required
def history_replay(consulta_id: int):
    consulta = db.session.get(ConsultaOsint, consulta_id)
    if not consulta:
        return jsonify({"ok": False, "error": "Consulta no encontrada"}), 404

    result = _ENGINE.search(
        target=consulta.valor_consultado or "",
        source_hint=consulta.fuente.nombre if consulta.fuente else "all",
        persist=True,
        user_name=session.get("user"),
        created_by=str(session.get("user") or "system"),
    )
    return jsonify(
        {
            "ok": True,
            "consulta_id": consulta_id,
            "target": consulta.valor_consultado,
            "target_type": result.get("target_type", consulta.entity_type or "unknown"),
            "results_count": result.get("stats", {}).get("results_count", 0),
            "risk": result.get("risk", {}),
        }
    )


@history_osint_bp.route("/history/<int:consulta_id>")
@login_required
def history_detail(consulta_id: int):
    consulta = db.session.get(ConsultaOsint, consulta_id)
    if not consulta:
        return jsonify({"ok": False, "error": "Consulta no encontrada"}), 404
    return jsonify(_serialize_consulta(consulta))


@history_osint_bp.route("/history/<int:consulta_id>/export/<format>")
@login_required
def history_detail_export(consulta_id: int, format: str):
    consulta = db.session.get(ConsultaOsint, consulta_id)
    if not consulta:
        return jsonify({"ok": False, "error": "Consulta no encontrada"}), 404
    if format == "graphml":
        return _consulta_graphml(consulta)
    if format == "json":
        return _history_json([_serialize_consulta(consulta)])
    if format == "csv":
        return _history_csv([_serialize_consulta(consulta)])
    return jsonify({"ok": False, "error": "Formato de exportación no soportado"}), 400
