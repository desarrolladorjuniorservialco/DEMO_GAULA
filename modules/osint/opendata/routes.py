import json
from datetime import datetime, timedelta

from flask import render_template, request

from models import db
from models.osint import CacheConsulta, ConsultaOsint, FuenteOsint, ResultadoOsint
from modules.osint.auth import login_required
from modules.osint.open_data.service import OpenDataEngine
from modules.osint.opendata import opendata_osint_bp

_ENGINE = OpenDataEngine()


def _ensure_source() -> FuenteOsint:
    source = db.session.query(FuenteOsint).filter_by(nombre="open_data_engine").first()
    if source:
        return source

    source = FuenteOsint(
        nombre="open_data_engine",
        tipo="engine",
        url_base="https://www.datos.gov.co/",
        requiere_key=False,
        activa=True,
        rate_limit_por_min=120,
        descripcion="Panel de datos abiertos y fuentes oficiales",
        created_by="system",
        updated_by="system",
    )
    db.session.add(source)
    db.session.commit()
    return source


def _persist_lookup(payload: dict[str, object]) -> None:
    try:
        source = _ensure_source()
        consulta = ConsultaOsint(
            fuente_id=source.id,
            tipo_consulta=f"open_data:{payload.get('source_hint', 'official')}",
            valor_consultado=str(payload.get("query", "")),
            entity_type=str(payload.get("target_type", "unknown")),
            estado="completada",
            created_by="system",
        )
        db.session.add(consulta)
        db.session.flush()

        cache = CacheConsulta(
            consulta_id=consulta.id,
            hash_clave=(
                f"open-data:{payload.get('source_hint', 'official')}:"
                f"{payload.get('query_normalized', payload.get('query', ''))}:{consulta.id}"
            ),
            respuesta_raw=json.dumps(payload, ensure_ascii=False, default=str),
            codigo_http=200,
            expira_en=datetime.utcnow() + timedelta(hours=1),
            hits=0,
        )
        db.session.add(cache)

        for item in list(payload.get("results", []))[:25]:
            if not isinstance(item, dict):
                continue
            resultado = ResultadoOsint(
                consulta_id=consulta.id,
                tipo_hallazgo=str(item.get("entity_type", "record")),
                titulo=str(item.get("value", ""))[:200],
                descripcion=json.dumps(item.get("metadata", {}), ensure_ascii=False, default=str),
                datos_json=json.dumps(item, ensure_ascii=False, default=str),
                relevancia=float(item.get("confidence", 0.5) or 0.5),
                verificado=False,
                created_by="system",
            )
            db.session.add(resultado)

        db.session.commit()
    except Exception:
        db.session.rollback()


@opendata_osint_bp.route("/lookup")
@login_required
def lookup():
    query = request.args.get("q", "").strip()
    source = (request.args.get("source", "official", type=str) or "official").strip() or "official"

    if not query:
        payload = {
            "query": "",
            "query_normalized": "",
            "source_hint": source,
            "source_label": source.replace("_", " ").title(),
            "target_type": "unknown",
            "source_catalog": _ENGINE.catalog("empty", source),
            "source_results": [],
            "results": [],
            "errors": ["No se proporciono una consulta."],
            "network": {"ip_data": None, "rdap_data": None, "crt_data": []},
            "ip_data": None,
            "rdap_data": None,
            "crt_data": [],
            "summary": {
                "sources_count": 0,
                "records_count": 0,
                "errors_count": 1,
                "network_records_count": 0,
            },
            "guidance": [],
        }
    else:
        payload = _ENGINE.search(query, source_hint=source)
        _persist_lookup(payload)

    return render_template("osint/opendata_fragment.html", **payload)
