# modules/dashboard/routes.py
from flask import render_template, request, session, jsonify
from modules.dashboard import dashboard_bp
from modules.auth.decorators import login_required, director_required
from modules.extensions import db
from models.nexo147 import Caso
from models.osint import FuenteOsint, ConsultaOsint, CacheConsulta, IndicadorRiesgo
import requests
import hashlib
import json
from datetime import datetime, timedelta


@dashboard_bp.route("/dashboard")
@director_required
def dashboard():
    casos = Caso.query.order_by(Caso.fecha_registro.desc()).all()
    total          = len(casos)
    casos_criticos = sum(1 for c in casos if (c.prioridad or "").lower() == "critica")

    tipos_conteo = {}
    for c in casos:
        tipo = c.tipo_caso or "Sin clasificar"
        tipos_conteo[tipo] = tipos_conteo.get(tipo, 0) + 1

    if not tipos_conteo:
        tipos_conteo = {"Extorsion": 18, "Hurto": 11, "Fraude digital": 9, "Amenaza": 7, "Secuestro": 3}

    max_tipo = max(tipos_conteo.values()) if tipos_conteo else 1
    tipos = [
        {"tipo": t, "cantidad": n, "porcentaje": f"{int((n / max_tipo) * 100)}%"}
        for t, n in tipos_conteo.items()
    ]

    stats = {
        "casos_activos":     total if total else 48,
        "casos_criticos":    casos_criticos if total else 12,
        "gaulas_conectados": 34,
        "tiempo_respuesta":  "08m",
        "reportes_147":      total if total else 124,
        "alertas_osint":     IndicadorRiesgo.query.filter_by(activo=True).count() or 19,
    }
    return render_template("dashboard/dashboard.html", reportes=casos, stats=stats, tipos=tipos)


@dashboard_bp.route("/api/brechas", methods=["GET"])
@dashboard_bp.route("/api/osint/brechas", methods=["GET"])
@login_required
def api_osint_brechas():
    role = session.get("role")
    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "Acceso restringido."}), 403

    query_val = request.args.get("q", "all_breaches").strip()

    fuente = FuenteOsint.query.filter_by(nombre="HaveIBeenPwned").first()
    if not fuente:
        fuente = FuenteOsint(
            nombre="HaveIBeenPwned", tipo="API Brechas",
            url_base="https://haveibeenpwned.com/api/v3",
            requiere_key=False, activa=True, created_by="system"
        )
        db.session.add(fuente)
        db.session.commit()

    hash_key = hashlib.sha256(f"hibp:{query_val}".encode("utf-8")).hexdigest()
    cache_record = CacheConsulta.query.filter_by(hash_clave=hash_key).first()
    now = datetime.utcnow()

    if cache_record and cache_record.expira_en and cache_record.expira_en > now:
        cache_record.hits = (cache_record.hits or 0) + 1
        db.session.commit()
        try:
            return jsonify(json.loads(cache_record.respuesta_raw))
        except Exception:
            pass

    url = "https://haveibeenpwned.com/api/v3/breaches"
    status_code = 200
    try:
        response = requests.get(url, timeout=5)
        status_code = response.status_code
        if response.status_code == 200:
            datos = response.json()
            resultados = [{"Nombre": b.get("Name"), "Dominio": b.get("Domain"), "Fecha": b.get("BreachDate"), "Cantidad_afectados": b.get("PwnCount"), "Descripcion": b.get("Description")} for b in datos[:20]]
        else:
            raise Exception("API returned non-200")
    except Exception:
        resultados = [
            {"Nombre": "Adobe",    "Dominio": "adobe.com",    "Fecha": "2013-10-04", "Cantidad_afectados": 152445162, "Descripcion": "Adobe database compromise."},
            {"Nombre": "Canva",    "Dominio": "canva.com",    "Fecha": "2019-05-24", "Cantidad_afectados": 137000000, "Descripcion": "Canva security breach incident."},
            {"Nombre": "LinkedIn", "Dominio": "linkedin.com", "Fecha": "2016-05-17", "Cantidad_afectados": 164000000, "Descripcion": "Historical LinkedIn credential leak."},
        ]

    consulta = ConsultaOsint.query.filter_by(fuente_id=fuente.id, valor_consultado=query_val).first()
    if not consulta:
        consulta = ConsultaOsint(fuente_id=fuente.id, tipo_consulta="brechas_scan", valor_consultado=query_val, estado="completado", created_by=session.get("user") or "system")
        db.session.add(consulta)
        db.session.flush()

    expiration_time = now + timedelta(hours=1)
    if not cache_record:
        cache_record = CacheConsulta(consulta_id=consulta.id, hash_clave=hash_key, respuesta_raw=json.dumps(resultados), codigo_http=status_code, fecha_consulta=now, expira_en=expiration_time, hits=1)
        db.session.add(cache_record)
    else:
        cache_record.consulta_id   = consulta.id
        cache_record.respuesta_raw = json.dumps(resultados)
        cache_record.codigo_http   = status_code
        cache_record.fecha_consulta = now
        cache_record.expira_en     = expiration_time
        cache_record.hits          = (cache_record.hits or 0) + 1

    db.session.commit()
    return jsonify(resultados)


@dashboard_bp.route("/api/osint/indicadores", methods=["GET"])
@login_required
def api_osint_indicadores():
    role = session.get("role")
    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "Acceso restringido."}), 403

    indicadores = IndicadorRiesgo.query.filter_by(activo=True).order_by(IndicadorRiesgo.nivel_riesgo.desc()).limit(50).all()
    if not indicadores:
        return jsonify([
            {"id": 1, "tipo": "telefono", "valor": "3124567890",    "descripcion": "Número reportado en 4 casos extorsivos confirmados",              "nivel_riesgo": "Crítico", "fuente_origen": "NEXO-147",     "fecha_deteccion": "2026-05-15"},
            {"id": 2, "tipo": "ip",       "valor": "190.14.23.45",   "descripcion": "IP asociada a acceso de cuenta bancaria sospechosa",              "nivel_riesgo": "Alto",    "fuente_origen": "OSINT externo", "fecha_deteccion": "2026-05-20"},
            {"id": 3, "tipo": "dominio",  "valor": "pagos-gaula.co", "descripcion": "Dominio falso usado en campaña de phishing institucional activa", "nivel_riesgo": "Crítico", "fuente_origen": "CERT-CO",      "fecha_deteccion": "2026-05-22"},
            {"id": 4, "tipo": "correo",   "valor": "gaula@pagos.net","descripcion": "Dirección usada para envío masivo de correos de extorsión",      "nivel_riesgo": "Alto",    "fuente_origen": "Denuncia",     "fecha_deteccion": "2026-05-18"},
        ])
    return jsonify([{"id": i.id, "tipo": i.tipo or "", "valor": i.valor, "descripcion": i.descripcion or "", "nivel_riesgo": i.nivel_riesgo or "Bajo", "fuente_origen": i.fuente_origen or "", "fecha_deteccion": i.fecha_deteccion.strftime('%Y-%m-%d') if i.fecha_deteccion else ""} for i in indicadores])


@dashboard_bp.route("/api_externa", methods=["GET", "POST"])
def api_externa():
    url = "https://haveibeenpwned.com/api/v3/breaches"
    if request.method == "GET":
        try:
            response = requests.get(url)
            if response.status_code != 200:
                return jsonify({"error": f"Error al conectar con la API externa: {response.status_code}"}), response.status_code
            response.raise_for_status()
            datos = response.json()
            resultados = [{"Nombre": b["Name"], "Dominio": b["Domain"], "Fecha": b["BreachDate"], "Cantidad_afectados": b["PwnCount"], "Descripcion": b["Description"]} for b in datos]
            return render_template("dashboard/brechas_seguridad.html", brechas=resultados)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"Mensaje": "Endpoint de API externa, envía una solicitud POST con datos JSON."}), 200


@dashboard_bp.route("/health")
def health():
    return {"status": "ok", "service": "NEXO-147 Demo"}
