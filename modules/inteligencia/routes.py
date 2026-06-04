# modules/inteligencia/routes.py
from flask import session, jsonify
from datetime import datetime
from modules.inteligencia import intel_bp
from modules.auth.decorators import login_required
from models.nexo147 import Caso
from models.intel import (
    Persona, Alias, Telefono, Correo, Ubicacion,
    Vehiculo, CuentaBancaria, Organizacion,
    IntelNode, IntelEdge, HallazgoIntel,
)
from models.osint import ConsultaOsint, IndicadorRiesgo


@intel_bp.route("/api/entidades", methods=["GET"])
@login_required
def api_entidades():
    personas = [
        {"nombre": "Carlos Mendoza", "documento": "1.023.456.789", "rol": "Sospechoso", "casos_vinculados": ["147-001", "147-003"]},
        {"nombre": "Diana Restrepo", "documento": "52.345.678", "rol": "Reportante", "casos_vinculados": ["147-002"]},
        {"nombre": "Andres Felipe Gomez", "documento": "1.018.990.123", "rol": "Victima", "casos_vinculados": ["147-005"]},
    ]
    telefonos = [
        {"numero": "3124567890", "compania": "Claro", "tipo": "Extorsivo", "casos_vinculados": ["147-001", "147-004"]},
        {"numero": "3209876543", "compania": "Movistar", "tipo": "Sospechoso", "casos_vinculados": ["147-003"]},
        {"numero": "3151112233", "compania": "Tigo", "tipo": "Victima", "casos_vinculados": ["147-002"]},
    ]
    alias = [
        {"nombre": "El Zarco", "descripcion": "Cabecilla de banda de extorsion carcelaria", "casos_vinculados": ["147-001", "147-004"]},
        {"nombre": "La Patrona", "descripcion": "Coordinadora de cobros en cuentas digitales", "casos_vinculados": ["147-003"]},
        {"nombre": "El Ingeniero", "descripcion": "Encargado de estafas informaticas y phishing", "casos_vinculados": ["147-005"]},
    ]
    ubicaciones = [
        {"nombre": "Bogota - Localidad Kennedy", "coordenadas": "4.6200, -74.1500", "tipo": "Foco delictivo", "casos_vinculados": ["147-001", "147-002"]},
        {"nombre": "Medellin - El Poblado", "coordenadas": "6.2100, -75.5700", "tipo": "Zona de amenazas", "casos_vinculados": ["147-003"]},
        {"nombre": "Cali - Distrito de Aguablanca", "coordenadas": "3.4200, -76.4800", "tipo": "Cobro extorsion", "casos_vinculados": ["147-004", "147-005"]},
    ]

    casos = Caso.query.all()
    for c in casos:
        code_pfx = c.id_caso[:7]
        for rep_link in c.reportantes:
            rep = rep_link.reportante
            if rep and rep.nombre and not any(p["nombre"].lower() == rep.nombre.lower() for p in personas):
                personas.append({
                    "nombre": rep.nombre,
                    "documento": rep.documento or "No registra",
                    "rol": "Reportante",
                    "casos_vinculados": [code_pfx],
                })
            if rep and rep.telefono and not any(t["numero"] == rep.telefono for t in telefonos):
                telefonos.append({
                    "numero": rep.telefono,
                    "compania": "No identificada",
                    "tipo": "Contacto",
                    "casos_vinculados": [code_pfx],
                })
        for medio in c.medios_pago:
            if medio.referencia and not any(t["numero"] == medio.referencia for t in telefonos):
                telefonos.append({
                    "numero": medio.referencia,
                    "compania": "No identificada",
                    "tipo": "Extorsivo",
                    "casos_vinculados": [code_pfx],
                })

    return jsonify({"personas": personas, "telefonos": telefonos, "alias": alias, "ubicaciones": ubicaciones})


@intel_bp.route("/api/inteligencia/relaciones", methods=["GET"])
@login_required
def api_inteligencia_relaciones():
    relaciones = [
        {"origen": "3124567890", "destino": "El Zarco", "tipo": "Uso", "confianza": "95%"},
        {"origen": "El Zarco", "destino": "Carlos Mendoza", "tipo": "Alias de", "confianza": "99%"},
        {"origen": "Carlos Mendoza", "destino": "Bogota - Localidad Kennedy", "tipo": "Ubicado en", "confianza": "85%"},
        {"origen": "3209876543", "destino": "La Patrona", "tipo": "Uso", "confianza": "90%"},
    ]
    casos = Caso.query.all()
    for c in casos:
        medios = c.medios_pago
        reps   = [rl.reportante for rl in c.reportantes if rl.reportante]
        for medio in medios:
            if medio.referencia and reps:
                relaciones.append({
                    "origen": medio.referencia,
                    "destino": reps[0].nombre or "Reportante",
                    "tipo": "Amenaza a",
                    "confianza": "80%",
                })
    return jsonify({"relaciones": relaciones})


@intel_bp.route("/api/intel/entidades", methods=["GET"])
@login_required
def api_intel_entidades():
    role = session.get("role")
    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "Acceso restringido a roles de inteligencia."}), 403

    personas       = Persona.query.order_by(Persona.nivel_riesgo.desc()).limit(50).all()
    alias_list     = Alias.query.limit(50).all()
    telefonos      = Telefono.query.limit(50).all()
    ubicaciones    = Ubicacion.query.limit(50).all()
    organizaciones = Organizacion.query.limit(30).all()
    vehiculos      = Vehiculo.query.limit(30).all()
    cuentas        = CuentaBancaria.query.limit(30).all()

    return jsonify({
        "personas": [{
            "id": p.id, "nombres": p.nombres or "", "apellidos": p.apellidos or "",
            "documento": p.documento or "No registra", "tipo_documento": p.tipo_documento or "",
            "nivel_riesgo": p.nivel_riesgo or "Desconocido", "es_objetivo": p.es_objetivo or False,
            "created_at": p.created_at.strftime('%Y-%m-%d') if p.created_at else "",
        } for p in personas],
        "alias": [{"id": a.id, "valor": a.valor, "contexto": a.contexto or "Sin contexto"} for a in alias_list],
        "telefonos": [{
            "id": t.id, "numero": t.numero, "operador": t.operador or "No identificado",
            "tipo": t.tipo or "Desconocido", "activo": t.activo,
        } for t in telefonos],
        "ubicaciones": [{
            "id": u.id, "latitud": u.latitud, "longitud": u.longitud,
            "descripcion": u.descripcion or "Sin descripción", "fuente": u.fuente or "",
            "fecha_captura": u.fecha_captura.strftime('%Y-%m-%d') if u.fecha_captura else "",
        } for u in ubicaciones],
        "organizaciones": [{"id": o.id, "nombre": o.nombre or "Sin nombre", "tipo": o.tipo or "", "descripcion": o.descripcion or "", "activa": o.activa} for o in organizaciones],
        "vehiculos": [{"id": v.id, "placa": v.placa or "No registra", "tipo": v.tipo or "", "marca": v.marca or "", "modelo": v.modelo or "", "anio": v.anio, "color": v.color or ""} for v in vehiculos],
        "cuentas": [{"id": c.id, "numero": c.numero or "", "tipo": c.tipo or "", "entidad": c.entidad or "No identificada", "titular_declarado": c.titular_declarado or "No registra"} for c in cuentas],
    })


@intel_bp.route("/api/intel/hallazgos", methods=["GET"])
@login_required
def api_intel_hallazgos():
    role = session.get("role")
    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "Acceso restringido."}), 403

    hallazgos = HallazgoIntel.query.order_by(HallazgoIntel.created_at.desc()).limit(30).all()
    if not hallazgos:
        return jsonify([
            {"id": 1, "titulo": "Red extorsiva activa — zona sur Bogotá", "descripcion": "Célula de 5 personas usando líneas prepago para coordinar cobros extorsivos a comerciantes de la zona.", "nivel_clasificacion": "Reservado", "estado": "activo", "caso_referencia_id": None, "created_at": "2026-06-01"},
            {"id": 2, "titulo": "Alias 'El Zarco' vinculado a múltiples casos", "descripcion": "Correlación cruzada confirma uso del mismo alias en casos 147-001, 147-003 y 147-007. Alta confianza 98%.", "nivel_clasificacion": "Confidencial", "estado": "confirmado", "caso_referencia_id": None, "created_at": "2026-05-28"},
            {"id": 3, "titulo": "Cuenta Nequi receptora de pagos extorsivos", "descripcion": "Cuenta con 4 transacciones extorsivas registradas en 30 días. Solicitud de bloqueo enviada a autoridad bancaria.", "nivel_clasificacion": "Reservado", "estado": "en_análisis", "caso_referencia_id": None, "created_at": "2026-05-25"},
            {"id": 4, "titulo": "Patrón de llamadas desde Penal La Picota", "descripcion": "Detección de patrón de llamadas externas coordinadas desde teléfonos registrados en el interior del penal.", "nivel_clasificacion": "Secreto", "estado": "activo", "caso_referencia_id": None, "created_at": "2026-05-20"},
        ])
    return jsonify([{
        "id": h.id, "titulo": h.titulo or "Sin título",
        "descripcion": h.descripcion or "", "nivel_clasificacion": h.nivel_clasificacion or "No clasificado",
        "estado": h.estado or "pendiente", "caso_referencia_id": h.caso_referencia_id,
        "created_at": h.created_at.strftime('%Y-%m-%d') if h.created_at else "",
    } for h in hallazgos])


@intel_bp.route("/api/intel/grafo", methods=["GET"])
@login_required
def api_intel_grafo():
    role = session.get("role")
    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "Acceso restringido."}), 403

    nodos   = IntelNode.query.limit(100).all()
    aristas = IntelEdge.query.limit(200).all()

    if not nodos:
        return jsonify({
            "nodos": [
                {"id": 1, "entity_type": "persona",   "label": "Carlos Mendoza",  "nivel_riesgo": "Alto"},
                {"id": 2, "entity_type": "alias",     "label": "El Zarco",         "nivel_riesgo": "Alto"},
                {"id": 3, "entity_type": "telefono",  "label": "3124567890",       "nivel_riesgo": "Crítico"},
                {"id": 4, "entity_type": "ubicacion", "label": "Bogotá — Kennedy", "nivel_riesgo": "Medio"},
                {"id": 5, "entity_type": "persona",   "label": "Diana Restrepo",   "nivel_riesgo": "Bajo"},
                {"id": 6, "entity_type": "cuenta",    "label": "Nequi **7890",     "nivel_riesgo": "Alto"},
                {"id": 7, "entity_type": "telefono",  "label": "3209876543",       "nivel_riesgo": "Alto"},
                {"id": 8, "entity_type": "alias",     "label": "La Patrona",       "nivel_riesgo": "Alto"},
            ],
            "aristas": [
                {"id": 1, "source": 1, "target": 2, "tipo_relacion": "usa_alias",     "confianza": 0.99},
                {"id": 2, "source": 1, "target": 3, "tipo_relacion": "usa_telefono",  "confianza": 0.95},
                {"id": 3, "source": 3, "target": 4, "tipo_relacion": "registrado_en", "confianza": 0.85},
                {"id": 4, "source": 3, "target": 5, "tipo_relacion": "amenaza_a",     "confianza": 0.80},
                {"id": 5, "source": 1, "target": 6, "tipo_relacion": "recibe_en",     "confianza": 0.90},
                {"id": 6, "source": 7, "target": 8, "tipo_relacion": "usa_alias",     "confianza": 0.92},
                {"id": 7, "source": 7, "target": 5, "tipo_relacion": "amenaza_a",     "confianza": 0.78},
            ],
        })

    return jsonify({
        "nodos": [{"id": n.id, "entity_type": n.entity_type, "label": n.label or f"{n.entity_type}-{n.entity_id}", "nivel_riesgo": n.nivel_riesgo or "Desconocido"} for n in nodos],
        "aristas": [{"id": e.id, "source": e.source_node_id, "target": e.target_node_id, "tipo_relacion": e.tipo_relacion or "relacionado_con", "confianza": round(e.confianza or 0.0, 2)} for e in aristas],
    })


@intel_bp.route("/api/etl/status", methods=["GET"])
@login_required
def api_etl_status():
    role = session.get("role")
    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "Acceso restringido."}), 403

    n_casos       = Caso.query.count()
    n_personas    = Persona.query.count()
    n_alias       = Alias.query.count()
    n_telefonos   = Telefono.query.count()
    n_ubicaciones = Ubicacion.query.count()
    n_consultas   = ConsultaOsint.query.count()
    n_indicadores = IndicadorRiesgo.query.count()
    n_nodos       = IntelNode.query.count()
    n_aristas     = IntelEdge.query.count()
    n_hallazgos   = HallazgoIntel.query.count()

    def pct(n, d):
        return min(100, int((n / max(1, d)) * 100)) if n > 0 else 0

    etapas = [
        {"id": "captura",      "nombre": "Captura / Línea 147",           "estado": "completado" if n_casos > 0 else "pendiente",     "registros": n_casos,                              "porcentaje": 100 if n_casos > 0 else 0},
        {"id": "gestion",      "nombre": "Gestión de Casos",               "estado": "completado" if n_casos > 0 else "pendiente",     "registros": n_casos,                              "porcentaje": 100 if n_casos > 0 else 0},
        {"id": "transac",      "nombre": "Base Transaccional",             "estado": "completado" if n_casos > 0 else "pendiente",     "registros": n_casos + n_personas,                 "porcentaje": 100 if n_casos > 0 else 0},
        {"id": "etl",          "nombre": "Motor ETL y Correlación",        "estado": "en_proceso" if (n_personas + n_alias) > 0 else ("en_proceso" if n_casos > 0 else "pendiente"),      "registros": n_personas + n_alias + n_telefonos,   "porcentaje": max(10 if n_casos > 0 else 0, min(90, pct(n_personas + n_alias, n_casos * 3 + 1)))},
        {"id": "dw",           "nombre": "Data Warehouse / Grafo",         "estado": "en_proceso" if n_nodos > 0 else ("en_proceso" if n_casos > 0 else "pendiente"),                     "registros": n_nodos,                              "porcentaje": max(8 if n_casos > 0 else 0, min(80, pct(n_nodos, n_personas + 10)))},
        {"id": "datamart",     "nombre": "Data Mart de Inteligencia",      "estado": "en_proceso" if n_hallazgos > 0 else ("en_proceso" if n_casos > 0 else "pendiente"),                 "registros": n_hallazgos,                          "porcentaje": max(5 if n_casos > 0 else 0, min(70, pct(n_hallazgos, n_personas + 5)))},
        {"id": "dashboard_ia", "nombre": "Dashboard IA / GIS / Analítica", "estado": "en_proceso" if n_indicadores > 0 else ("en_proceso" if n_casos > 0 else "pendiente"),               "registros": n_indicadores,                        "porcentaje": max(3 if n_casos > 0 else 0, min(60, pct(n_indicadores, n_hallazgos + 3)))},
        {"id": "decisiones",   "nombre": "Toma de Decisiones",             "estado": "completado" if n_casos > 0 else "pendiente",     "registros": n_casos,                              "porcentaje": 100 if n_casos > 0 else 0},
    ]

    return jsonify({
        "ultima_ejecucion": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        "estado_general": "nominal" if n_casos > 0 else "sin_datos",
        "etapas": etapas,
        "metricas": {
            "casos": n_casos, "personas": n_personas, "alias": n_alias,
            "telefonos": n_telefonos, "ubicaciones": n_ubicaciones,
            "consultas_osint": n_consultas, "indicadores_riesgo": n_indicadores,
            "nodos_grafo": n_nodos, "aristas_grafo": n_aristas, "hallazgos": n_hallazgos,
        },
    })
