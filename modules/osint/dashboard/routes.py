from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from flask import jsonify, render_template, request

from models.osint import ConsultaOsint, FuenteOsint, IndicadorRiesgo, ResultadoOsint

from modules.osint.auth import login_required
from modules.osint.dashboard import dashboard_osint_bp


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


def _dashboard_payload() -> dict:
    consultas = ConsultaOsint.query.order_by(ConsultaOsint.created_at.desc()).all()
    resultados = ResultadoOsint.query.order_by(ResultadoOsint.created_at.desc()).all()
    indicadores_activos = IndicadorRiesgo.query.filter_by(activo=True).count()

    total_consultas = len(consultas)
    total_resultados = len(resultados)
    source_counter = Counter()
    target_counter = Counter()
    risk_counter = Counter()
    daily_counter = defaultdict(int)
    recent = []

    for consulta in consultas:
        fuente = consulta.fuente.nombre if consulta.fuente else consulta.tipo_consulta or "desconocida"
        source_counter[fuente] += 1
        target_counter[consulta.entity_type or "unknown"] += 1
        risk_counter[_risk_from_results(list(consulta.resultados or []))["level"]] += 1
        if consulta.created_at:
            daily_counter[consulta.created_at.strftime("%Y-%m-%d")] += 1
        if len(recent) < 10:
            recent.append(
                {
                    "id": consulta.id,
                    "target": consulta.valor_consultado or "",
                    "target_type": consulta.entity_type or "",
                    "source": fuente,
                    "created_at": consulta.created_at.isoformat() if consulta.created_at else "",
                    "risk": _risk_from_results(list(consulta.resultados or [])),
                    "results_count": len(list(consulta.resultados or [])),
                }
            )

    last_7_days = []
    today = datetime.utcnow().date()
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        key = day.strftime("%Y-%m-%d")
        last_7_days.append({"date": key, "count": daily_counter.get(key, 0)})

    top_sources = [
        {"name": name, "count": count}
        for name, count in source_counter.most_common(8)
    ]
    top_targets = [
        {"name": name, "count": count}
        for name, count in target_counter.most_common(8)
    ]
    top_risks = [
        {"name": name, "count": count}
        for name, count in risk_counter.most_common()
    ]

    avg_results = round(total_resultados / total_consultas, 2) if total_consultas else 0
    avg_risk = 0
    if consultas:
        scores = []
        for consulta in consultas:
            summary = _risk_from_results(list(consulta.resultados or []))
            scores.append(summary["score"])
        avg_risk = round(sum(scores) / len(scores), 1) if scores else 0

    stats = {
        "consultas_total": total_consultas,
        "resultados_total": total_resultados,
        "fuentes_total": FuenteOsint.query.count(),
        "indicadores_activos": indicadores_activos,
        "promedio_resultados": avg_results,
        "riesgo_promedio": avg_risk,
    }

    return {
        "stats": stats,
        "series": {
            "consultas_por_dia": last_7_days,
            "top_fuentes": top_sources,
            "top_objetivos": top_targets,
            "riesgos": top_risks,
        },
        "recent": recent,
    }


@dashboard_osint_bp.route("/dashboard")
@login_required
def dashboard():
    payload = _dashboard_payload()
    return render_template(
        "osint/dashboard.html",
        stats=payload["stats"],
        series=payload["series"],
        recent=payload["recent"],
    )


@dashboard_osint_bp.route("/dashboard/api")
@login_required
def dashboard_api():
    return jsonify(_dashboard_payload())
