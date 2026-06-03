from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db
from models.nexo147 import (
    Usuario, UnidadGaula, Caso, Reportante, CasoReportante,
    Evidencia, EventoCaso, MedioPago
)
from models.intel import (
    Persona, Alias, Telefono, Correo, Direccion,
    Ubicacion, Vehiculo, CuentaBancaria, RedSocial, Organizacion,
    IntelNode, IntelEdge, HallazgoIntel, CasoPersona, CasoTelefono,
)
from models.osint import FuenteOsint, ConsultaOsint, CacheConsulta, ResultadoOsint, IndicadorRiesgo
from functools import wraps
from datetime import datetime
import os
import uuid
import requests
from bs4 import BeautifulSoup
import re
import unicodedata


nexo = Flask(__name__, static_folder="static", template_folder="templates")
nexo.secret_key = os.getenv("SECRET_KEY", "demo-gaula-nexo-147")

_basedir = os.path.abspath(os.path.dirname(__file__))

nexo.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(_basedir, "data", "nexo147.db")
nexo.config["SQLALCHEMY_BINDS"] = {
    "intel": "sqlite:///" + os.path.join(_basedir, "data", "intel.db"),
    "osint": "sqlite:///" + os.path.join(_basedir, "data", "osint.db"),
}
nexo.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(nexo)


def seed_db():
    with nexo.app_context():
        db.create_all()

        if Usuario.query.count() == 0:
            for username, pwd, nombre, rol in [
                ("admin",    "Admin147*",    "Administrador NEXO-147", "admin"),
                ("director", "Director147*", "Director GAULA",         "director"),
                ("analista", "Analista147*", "Analista Operacional",   "analista"),
                ("operador", "Operador147*", "Operador Linea 147",     "operador"),
            ]:
                db.session.add(Usuario(
                    username=username,
                    password_hash=generate_password_hash(pwd),
                    nombre=nombre,
                    rol=rol,
                    created_by="seed",
                ))
            db.session.commit()

        if UnidadGaula.query.count() == 0:
            for nombre, ciudad, depto in [
                ("GAULA Bogota D.C.",  "Bogota",       "Cundinamarca"),
                ("GAULA Medellin",     "Medellin",     "Antioquia"),
                ("GAULA Cali",         "Cali",         "Valle del Cauca"),
                ("GAULA Barranquilla", "Barranquilla", "Atlantico"),
                ("GAULA Bucaramanga",  "Bucaramanga",  "Santander"),
            ]:
                db.session.add(UnidadGaula(
                    nombre=nombre,
                    ciudad=ciudad,
                    departamento=depto,
                    created_by="seed",
                ))
            db.session.commit()


@nexo.after_request
def disable_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Acceso restringido a administradores.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return wrapper


def director_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") not in ["admin", "director"]:
            flash("Acceso restringido a directores y administradores.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return wrapper


def analista_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") not in ["admin", "analista"]:
            flash("Acceso restringido a analistas y administradores.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return wrapper


def operador_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") not in ["admin", "operador"]:
            flash("Acceso restringido a operadores y administradores.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return wrapper


# =========================================================
# MOTOR BÁSICO DEL CHATBOT
# =========================================================

def normalizar_texto(texto):
    texto = str(texto or "").lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def consulta_casos_por_rol():
    role = session.get("role")
    username = session.get("user")

    if role == "operador":
        return Caso.query.filter_by(created_by=username)

    return Caso.query


def contar_por_campo(casos, campo):
    conteo = {}

    for caso in casos:
        valor = getattr(caso, campo, None) or "Sin información"
        conteo[valor] = conteo.get(valor, 0) + 1

    return conteo


def responder_chatbot(pregunta):
    pregunta_original = pregunta
    pregunta = normalizar_texto(pregunta)

    role = session.get("role")

    try:
        query_base = consulta_casos_por_rol()

        patron_uuid = re.search(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            pregunta_original
        )

        if patron_uuid:
            codigo = patron_uuid.group(0)
            caso = query_base.filter_by(id_caso=codigo).first()

            if not caso:
                return f"No encontré un caso con el código {codigo}."

            unidad_nombre = caso.unidad_gaula.nombre if caso.unidad_gaula else "Sin unidad asignada"
            fecha = caso.fecha_registro.strftime("%Y-%m-%d %H:%M") if caso.fecha_registro else "Sin fecha"

            return (
                f"Estado del caso:\n"
                f"- Código: {caso.id_caso}\n"
                f"- Estado: {caso.estado or 'Sin estado'}\n"
                f"- Prioridad: {caso.prioridad or 'Sin prioridad'}\n"
                f"- Tipo de caso: {caso.tipo_caso or 'Sin tipo'}\n"
                f"- Unidad GAULA: {unidad_nombre}\n"
                f"- Fecha de registro: {fecha}"
            )

        if (
            ("cuantos" in pregunta or "total" in pregunta)
            and "casos" in pregunta
            and "estado" not in pregunta
            and "prioridad" not in pregunta
            and "tipo" not in pregunta
            and "gaula" not in pregunta
        ):
            total = query_base.count()

            if role == "operador":
                return f"Tienes {total} casos registrados por tu usuario."

            return f"Actualmente hay {total} casos registrados en el sistema."

        if "critico" in pregunta or "critica" in pregunta:
            casos = query_base.all()
            total = sum(1 for c in casos if normalizar_texto(c.prioridad) == "critica")
            return f"Hay {total} casos con prioridad crítica."

        if "activo" in pregunta or "activos" in pregunta or "abierto" in pregunta or "abiertos" in pregunta:
            casos = query_base.all()
            total = sum(1 for c in casos if normalizar_texto(c.estado) != "cerrado")
            return f"Hay {total} casos activos o no cerrados."

        if "cerrado" in pregunta or "cerrados" in pregunta:
            casos = query_base.all()
            total = sum(1 for c in casos if normalizar_texto(c.estado) == "cerrado")
            return f"Hay {total} casos cerrados."

        estados_validos = {
            "recibido": "Recibido",
            "validacion": "Validación",
            "asignado": "Asignado",
            "analisis": "Análisis",
            "seguimiento": "Seguimiento",
            "cerrado": "Cerrado"
        }

        for clave, estado_visible in estados_validos.items():
            if clave in pregunta:
                casos = query_base.all()
                total = sum(1 for c in casos if normalizar_texto(c.estado) == clave)
                return f"Hay {total} casos en estado: {estado_visible}."

        if "estado" in pregunta or "estados" in pregunta:
            casos = query_base.all()
            conteo = contar_por_campo(casos, "estado")

            if not conteo:
                return "No hay casos registrados para calcular estados."

            respuesta = "Casos por estado:\n"
            for estado, total in conteo.items():
                respuesta += f"- {estado}: {total}\n"

            return respuesta.strip()

        if "prioridad" in pregunta or "prioridades" in pregunta:
            casos = query_base.all()
            conteo = contar_por_campo(casos, "prioridad")

            if not conteo:
                return "No hay casos registrados para calcular prioridades."

            respuesta = "Casos por prioridad:\n"
            for prioridad, total in conteo.items():
                respuesta += f"- {prioridad}: {total}\n"

            return respuesta.strip()

        if "tipo" in pregunta or "delito" in pregunta or "modalidad" in pregunta:
            casos = query_base.all()
            conteo = contar_por_campo(casos, "tipo_caso")

            if not conteo:
                return "No hay casos registrados para calcular tipos de caso."

            respuesta = "Casos por tipo de caso:\n"
            for tipo, total in conteo.items():
                respuesta += f"- {tipo}: {total}\n"

            return respuesta.strip()

        if "gaula" in pregunta or "unidad" in pregunta:
            casos = query_base.all()
            conteo = {}

            for caso in casos:
                unidad = caso.unidad_gaula.nombre if caso.unidad_gaula else "Sin unidad"
                conteo[unidad] = conteo.get(unidad, 0) + 1

            if not conteo:
                return "No hay casos registrados por unidad GAULA."

            respuesta = "Casos por unidad GAULA:\n"
            for unidad, total in conteo.items():
                respuesta += f"- {unidad}: {total}\n"

            return respuesta.strip()

        if "ultimos" in pregunta or "recientes" in pregunta or "reciente" in pregunta:
            casos = query_base.order_by(Caso.fecha_registro.desc()).limit(5).all()

            if not casos:
                return "No hay casos recientes registrados."

            respuesta = "Últimos casos registrados:\n"

            for caso in casos:
                unidad = caso.unidad_gaula.nombre if caso.unidad_gaula else "Sin unidad"
                fecha = caso.fecha_registro.strftime("%Y-%m-%d %H:%M") if caso.fecha_registro else ""

                respuesta += (
                    f"- {caso.id_caso} | {caso.tipo_caso} | "
                    f"{caso.prioridad} | {caso.estado} | {unidad} | {fecha}\n"
                )

            return respuesta.strip()

        return (
            "Puedo ayudarte con consultas básicas como:\n"
            "- ¿Cuántos casos hay?\n"
            "- ¿Cuántos casos críticos hay?\n"
            "- Casos por estado\n"
            "- Casos por prioridad\n"
            "- Casos por tipo de caso\n"
            "- Casos por unidad GAULA\n"
            "- Últimos casos registrados\n"
            "- Estado del caso usando el código interno"
        )

    except Exception as e:
        print("Error en chatbot:", e)
        return "Ocurrió un error consultando la base de datos."


# =========================================================
# RUTAS PRINCIPALES
# =========================================================

@nexo.route("/")
@login_required
def home():
    return render_template("console.html")


@nexo.route("/index")
@login_required
def index():
    return render_template("index.html")


@nexo.route("/console")
@login_required
def console():
    return render_template("console.html")


@nexo.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()

        user = Usuario.query.filter_by(username=usuario, activo=True).first()

        if user and check_password_hash(user.password_hash, password):
            session["user"] = user.username
            session["role"] = user.rol
            session["name"] = user.nombre
            return redirect(url_for("home"))

        flash("Usuario o contraseña incorrectos.", "error")

    return render_template("login.html")


@nexo.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@nexo.route("/registrar-reporte", methods=["POST"])
@login_required
def registrar_reporte():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    tipo_caso = data.get("tipo_reporte", "").strip()
    prioridad = data.get("prioridad", "").strip()
    descripcion = data.get("descripcion", "").strip()

    if not tipo_caso or not prioridad or not descripcion:
        if request.is_json:
            return {"error": "Debe registrar tipo de reporte, prioridad y descripcion minima."}, 400

        flash("Debe registrar tipo de reporte, prioridad y descripcion minima.", "error")
        return redirect(url_for("home"))

    nombre_unidad = data.get("unidad_gaula", "").strip()
    unidad = None

    if nombre_unidad:
        unidad = UnidadGaula.query.filter_by(nombre=nombre_unidad).first()

        if not unidad:
            unidad = UnidadGaula(
                nombre=nombre_unidad,
                created_by=session.get("user")
            )
            db.session.add(unidad)
            db.session.flush()

    caso = Caso(
        id_caso=str(uuid.uuid4()),
        estado="Recibido",
        prioridad=prioridad,
        tipo_caso=tipo_caso,
        canal_recepcion=data.get("canal_recepcion", "").strip(),
        unidad_gaula_id=unidad.id if unidad else None,
        descripcion=descripcion,
        observaciones=data.get("observaciones", "").strip(),
        created_by=session.get("user"),
    )

    db.session.add(caso)
    db.session.flush()

    nombre_rep = data.get("nombre_reportante", "").strip()

    if nombre_rep or data.get("documento_reportante") or data.get("telefono_reportante"):
        rep = Reportante(
            nombre=nombre_rep,
            documento=data.get("documento_reportante", "").strip(),
            telefono=data.get("telefono_reportante", "").strip(),
            anonimo=not bool(nombre_rep),
            created_by=session.get("user"),
        )

        db.session.add(rep)
        db.session.flush()

        db.session.add(CasoReportante(
            caso_id=caso.id,
            reportante_id=rep.id,
            rol_en_caso="denunciante",
            created_by=session.get("user"),
        ))

    medio = data.get("medio_pago", "").strip()

    if medio:
        raw = data.get("valor_exigido", "0").strip().replace(",", "").replace("$", "") or "0"

        try:
            valor_decimal = float(raw)
        except ValueError:
            valor_decimal = 0.0

        db.session.add(MedioPago(
            caso_id=caso.id,
            tipo=medio,
            valor_exigido=valor_decimal,
            referencia=data.get("numero_extorsivo", "").strip(),
            created_by=session.get("user"),
        ))

    evidencia_txt = data.get("evidencia", "").strip()

    if evidencia_txt:
        db.session.add(Evidencia(
            caso_id=caso.id,
            tipo="referencia",
            descripcion=evidencia_txt,
            created_by=session.get("user"),
        ))

    db.session.add(EventoCaso(
        caso_id=caso.id,
        tipo_evento="creacion",
        descripcion="Caso registrado desde formulario.",
        estado_nuevo="Recibido",
        created_by=session.get("user"),
    ))

    db.session.commit()

    if request.is_json:
        return {
            "mensaje": f"Reporte registrado. Codigo: {caso.id_caso}",
            "id_reporte": caso.id_caso
        }, 201

    flash(f"Reporte registrado correctamente. Codigo interno: {caso.id_caso}", "ok")
    return redirect(url_for("home"))


@nexo.route("/dashboard")
@director_required
def dashboard():
    casos = Caso.query.order_by(Caso.fecha_registro.desc()).all()

    total = len(casos)
    casos_criticos = sum(1 for c in casos if normalizar_texto(c.prioridad) == "critica")

    tipos_conteo = {}

    for c in casos:
        tipo = c.tipo_caso or "Sin clasificar"
        tipos_conteo[tipo] = tipos_conteo.get(tipo, 0) + 1

    if not tipos_conteo:
        tipos_conteo = {
            "Extorsion": 18,
            "Hurto": 11,
            "Fraude digital": 9,
            "Amenaza": 7,
            "Secuestro": 3,
        }

    max_tipo = max(tipos_conteo.values()) if tipos_conteo else 1

    tipos = [
        {
            "tipo": t,
            "cantidad": n,
            "porcentaje": f"{int((n / max_tipo) * 100)}%"
        }
        for t, n in tipos_conteo.items()
    ]

    stats = {
        "casos_activos": total if total else 48,
        "casos_criticos": casos_criticos if total else 12,
        "gaulas_conectados": 34,
        "tiempo_respuesta": "08m",
        "reportes_147": total if total else 124,
        "alertas_osint": IndicadorRiesgo.query.filter_by(activo=True).count() or 19,
    }

    return render_template("dashboard.html", reportes=casos, stats=stats, tipos=tipos)


@nexo.route("/api/chatbot", methods=["POST"])
@login_required
def api_chatbot():
    data = request.get_json(silent=True) or {}
    pregunta = data.get("pregunta", "").strip()

    if not pregunta:
        return jsonify({
            "ok": False,
            "respuesta": "Debes escribir una pregunta."
        }), 400

    respuesta = responder_chatbot(pregunta)

    return jsonify({
        "ok": True,
        "respuesta": respuesta
    })


@nexo.route("/api/casos", methods=["GET"])
@login_required
def api_casos():
    role = session.get("role")
    username = session.get("user")

    if role == "operador":
        casos = Caso.query.filter_by(created_by=username).order_by(Caso.fecha_registro.desc()).all()
    else:
        casos = Caso.query.order_by(Caso.fecha_registro.desc()).all()

    resultados = []

    for c in casos:
        unidad_nombre = c.unidad_gaula.nombre if c.unidad_gaula else ""
        medio = c.medios_pago[0] if c.medios_pago else None
        rep_link = c.reportantes[0] if c.reportantes else None
        rep = rep_link.reportante if rep_link else None

        resultados.append({
            "id_reporte": c.id_caso,
            "fecha_registro": c.fecha_registro.strftime('%Y-%m-%d %H:%M') if c.fecha_registro else "",
            "estado": c.estado,
            "usuario_registro": c.created_by,
            "tipo_reporte": c.tipo_caso,
            "prioridad": c.prioridad,
            "unidad_gaula": unidad_nombre,
            "canal_recepcion": c.canal_recepcion,
            "nombre_reportante": rep.nombre if rep else "",
            "documento_reportante": rep.documento if rep else "",
            "telefono_reportante": rep.telefono if rep else "",
            "descripcion": c.descripcion,
            "medio_pago": medio.tipo if medio else "",
            "valor_exigido": str(medio.valor_exigido) if medio else "",
            "observaciones": c.observaciones,
        })

    return jsonify(resultados)


@nexo.route("/api/casos/<id_reporte>/estado", methods=["POST"])
@login_required
def api_actualizar_estado(id_reporte):
    role = session.get("role")

    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "No autorizado para cambiar el estado del caso."}), 403

    data = request.get_json() or {}
    nuevo_estado = data.get("estado", "").strip()

    if not nuevo_estado:
        return jsonify({"error": "Debe proporcionar un estado valido."}), 400

    caso = Caso.query.filter_by(id_caso=id_reporte).first()

    if not caso:
        return jsonify({"error": "Caso no encontrado."}), 404

    estado_anterior = caso.estado
    caso.estado = nuevo_estado

    db.session.add(EventoCaso(
        caso_id=caso.id,
        tipo_evento="cambio_estado",
        descripcion=f"Estado actualizado de {estado_anterior} a {nuevo_estado}.",
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        created_by=session.get("user"),
    ))

    db.session.commit()

    return jsonify({
        "mensaje": f"Estado actualizado a: {nuevo_estado}",
        "id_reporte": id_reporte
    })


@nexo.route("/api/entidades", methods=["GET"])
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

    return jsonify({
        "personas": personas,
        "telefonos": telefonos,
        "alias": alias,
        "ubicaciones": ubicaciones,
    })


@nexo.route("/api/inteligencia/relaciones", methods=["GET"])
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
        reps = [rl.reportante for rl in c.reportantes if rl.reportante]

        for medio in medios:
            if medio.referencia and reps:
                relaciones.append({
                    "origen": medio.referencia,
                    "destino": reps[0].nombre or "Reportante",
                    "tipo": "Amenaza a",
                    "confianza": "80%",
                })

    return jsonify({"relaciones": relaciones})


@nexo.route("/api/brechas", methods=["GET"])
@nexo.route("/api/osint/brechas", methods=["GET"])
@login_required
def api_osint_brechas():
    role = session.get("role")

    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "Acceso restringido."}), 403

    import hashlib
    import json
    from datetime import timedelta

    query_val = request.args.get("q", "all_breaches").strip()

    fuente = FuenteOsint.query.filter_by(nombre="HaveIBeenPwned").first()

    if not fuente:
        fuente = FuenteOsint(
            nombre="HaveIBeenPwned",
            tipo="API Brechas",
            url_base="https://haveibeenpwned.com/api/v3",
            requiere_key=False,
            activa=True,
            created_by="system"
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
            import json
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
            resultados = []

            for brecha in datos[:20]:
                resultados.append({
                    "Nombre": brecha.get("Name"),
                    "Dominio": brecha.get("Domain"),
                    "Fecha": brecha.get("BreachDate"),
                    "Cantidad_afectados": brecha.get("PwnCount"),
                    "Descripcion": brecha.get("Description")
                })
        else:
            raise Exception("API returned non-200")

    except Exception:
        resultados = [
            {"Nombre": "Adobe", "Dominio": "adobe.com", "Fecha": "2013-10-04", "Cantidad_afectados": 152445162, "Descripcion": "Adobe database compromise."},
            {"Nombre": "Canva", "Dominio": "canva.com", "Fecha": "2019-05-24", "Cantidad_afectados": 137000000, "Descripcion": "Canva security breach incident."},
            {"Nombre": "LinkedIn", "Dominio": "linkedin.com", "Fecha": "2016-05-17", "Cantidad_afectados": 164000000, "Descripcion": "Historical LinkedIn credential leak."}
        ]

    consulta = ConsultaOsint.query.filter_by(
        fuente_id=fuente.id,
        valor_consultado=query_val
    ).first()

    if not consulta:
        consulta = ConsultaOsint(
            fuente_id=fuente.id,
            tipo_consulta="brechas_scan",
            valor_consultado=query_val,
            estado="completado",
            created_by=session.get("user") or "system"
        )
        db.session.add(consulta)
        db.session.flush()

    expiration_time = now + timedelta(hours=1)

    if not cache_record:
        cache_record = CacheConsulta(
            consulta_id=consulta.id,
            hash_clave=hash_key,
            respuesta_raw=json.dumps(resultados),
            codigo_http=status_code,
            fecha_consulta=now,
            expira_en=expiration_time,
            hits=1
        )
        db.session.add(cache_record)
    else:
        cache_record.consulta_id = consulta.id
        cache_record.respuesta_raw = json.dumps(resultados)
        cache_record.codigo_http = status_code
        cache_record.fecha_consulta = now
        cache_record.expira_en = expiration_time
        cache_record.hits = (cache_record.hits or 0) + 1

    db.session.commit()

    return jsonify(resultados)


@nexo.route("/api/intel/entidades", methods=["GET"])
@login_required
def api_intel_entidades():
    role = session.get("role")

    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "Acceso restringido a roles de inteligencia."}), 403

    personas = Persona.query.order_by(Persona.nivel_riesgo.desc()).limit(50).all()
    alias_list = Alias.query.limit(50).all()
    telefonos = Telefono.query.limit(50).all()
    ubicaciones = Ubicacion.query.limit(50).all()
    organizaciones = Organizacion.query.limit(30).all()
    vehiculos = Vehiculo.query.limit(30).all()
    cuentas = CuentaBancaria.query.limit(30).all()

    return jsonify({
        "personas": [{
            "id": p.id,
            "nombres": p.nombres or "",
            "apellidos": p.apellidos or "",
            "documento": p.documento or "No registra",
            "tipo_documento": p.tipo_documento or "",
            "nivel_riesgo": p.nivel_riesgo or "Desconocido",
            "es_objetivo": p.es_objetivo or False,
            "created_at": p.created_at.strftime('%Y-%m-%d') if p.created_at else "",
        } for p in personas],

        "alias": [{
            "id": a.id,
            "valor": a.valor,
            "contexto": a.contexto or "Sin contexto",
        } for a in alias_list],

        "telefonos": [{
            "id": t.id,
            "numero": t.numero,
            "operador": t.operador or "No identificado",
            "tipo": t.tipo or "Desconocido",
            "activo": t.activo,
        } for t in telefonos],

        "ubicaciones": [{
            "id": u.id,
            "latitud": u.latitud,
            "longitud": u.longitud,
            "descripcion": u.descripcion or "Sin descripción",
            "fuente": u.fuente or "",
            "fecha_captura": u.fecha_captura.strftime('%Y-%m-%d') if u.fecha_captura else "",
        } for u in ubicaciones],

        "organizaciones": [{
            "id": o.id,
            "nombre": o.nombre or "Sin nombre",
            "tipo": o.tipo or "",
            "descripcion": o.descripcion or "",
            "activa": o.activa,
        } for o in organizaciones],

        "vehiculos": [{
            "id": v.id,
            "placa": v.placa or "No registra",
            "tipo": v.tipo or "",
            "marca": v.marca or "",
            "modelo": v.modelo or "",
            "anio": v.anio,
            "color": v.color or "",
        } for v in vehiculos],

        "cuentas": [{
            "id": c.id,
            "numero": c.numero or "",
            "tipo": c.tipo or "",
            "entidad": c.entidad or "No identificada",
            "titular_declarado": c.titular_declarado or "No registra",
        } for c in cuentas],
    })


@nexo.route("/api/intel/hallazgos", methods=["GET"])
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
        "id": h.id,
        "titulo": h.titulo or "Sin título",
        "descripcion": h.descripcion or "",
        "nivel_clasificacion": h.nivel_clasificacion or "No clasificado",
        "estado": h.estado or "pendiente",
        "caso_referencia_id": h.caso_referencia_id,
        "created_at": h.created_at.strftime('%Y-%m-%d') if h.created_at else "",
    } for h in hallazgos])


@nexo.route("/api/intel/grafo", methods=["GET"])
@login_required
def api_intel_grafo():
    role = session.get("role")

    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "Acceso restringido."}), 403

    nodos = IntelNode.query.limit(100).all()
    aristas = IntelEdge.query.limit(200).all()

    if not nodos:
        return jsonify({
            "nodos": [
                {"id": 1, "entity_type": "persona", "label": "Carlos Mendoza", "nivel_riesgo": "Alto"},
                {"id": 2, "entity_type": "alias", "label": "El Zarco", "nivel_riesgo": "Alto"},
                {"id": 3, "entity_type": "telefono", "label": "3124567890", "nivel_riesgo": "Crítico"},
                {"id": 4, "entity_type": "ubicacion", "label": "Bogotá — Kennedy", "nivel_riesgo": "Medio"},
                {"id": 5, "entity_type": "persona", "label": "Diana Restrepo", "nivel_riesgo": "Bajo"},
                {"id": 6, "entity_type": "cuenta", "label": "Nequi **7890", "nivel_riesgo": "Alto"},
                {"id": 7, "entity_type": "telefono", "label": "3209876543", "nivel_riesgo": "Alto"},
                {"id": 8, "entity_type": "alias", "label": "La Patrona", "nivel_riesgo": "Alto"},
            ],
            "aristas": [
                {"id": 1, "source": 1, "target": 2, "tipo_relacion": "usa_alias", "confianza": 0.99},
                {"id": 2, "source": 1, "target": 3, "tipo_relacion": "usa_telefono", "confianza": 0.95},
                {"id": 3, "source": 3, "target": 4, "tipo_relacion": "registrado_en", "confianza": 0.85},
                {"id": 4, "source": 3, "target": 5, "tipo_relacion": "amenaza_a", "confianza": 0.80},
                {"id": 5, "source": 1, "target": 6, "tipo_relacion": "recibe_en", "confianza": 0.90},
                {"id": 6, "source": 7, "target": 8, "tipo_relacion": "usa_alias", "confianza": 0.92},
                {"id": 7, "source": 7, "target": 5, "tipo_relacion": "amenaza_a", "confianza": 0.78},
            ],
        })

    return jsonify({
        "nodos": [{
            "id": n.id,
            "entity_type": n.entity_type,
            "label": n.label or f"{n.entity_type}-{n.entity_id}",
            "nivel_riesgo": n.nivel_riesgo or "Desconocido"
        } for n in nodos],

        "aristas": [{
            "id": e.id,
            "source": e.source_node_id,
            "target": e.target_node_id,
            "tipo_relacion": e.tipo_relacion or "relacionado_con",
            "confianza": round(e.confianza or 0.0, 2)
        } for e in aristas],
    })


@nexo.route("/api/osint/indicadores", methods=["GET"])
@login_required
def api_osint_indicadores():
    role = session.get("role")

    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "Acceso restringido."}), 403

    indicadores = IndicadorRiesgo.query.filter_by(activo=True)\
        .order_by(IndicadorRiesgo.nivel_riesgo.desc()).limit(50).all()

    if not indicadores:
        return jsonify([
            {"id": 1, "tipo": "telefono", "valor": "3124567890", "descripcion": "Número reportado en 4 casos extorsivos confirmados", "nivel_riesgo": "Crítico", "fuente_origen": "NEXO-147", "fecha_deteccion": "2026-05-15"},
            {"id": 2, "tipo": "ip", "valor": "190.14.23.45", "descripcion": "IP asociada a acceso de cuenta bancaria sospechosa", "nivel_riesgo": "Alto", "fuente_origen": "OSINT externo", "fecha_deteccion": "2026-05-20"},
            {"id": 3, "tipo": "dominio", "valor": "pagos-gaula.co", "descripcion": "Dominio falso usado en campaña de phishing institucional activa", "nivel_riesgo": "Crítico", "fuente_origen": "CERT-CO", "fecha_deteccion": "2026-05-22"},
            {"id": 4, "tipo": "correo", "valor": "gaula@pagos.net", "descripcion": "Dirección usada para envío masivo de correos de extorsión", "nivel_riesgo": "Alto", "fuente_origen": "Denuncia", "fecha_deteccion": "2026-05-18"},
        ])

    return jsonify([{
        "id": i.id,
        "tipo": i.tipo or "",
        "valor": i.valor,
        "descripcion": i.descripcion or "",
        "nivel_riesgo": i.nivel_riesgo or "Bajo",
        "fuente_origen": i.fuente_origen or "",
        "fecha_deteccion": i.fecha_deteccion.strftime('%Y-%m-%d') if i.fecha_deteccion else "",
    } for i in indicadores])


@nexo.route("/api/etl/status", methods=["GET"])
@login_required
def api_etl_status():
    role = session.get("role")

    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "Acceso restringido."}), 403

    n_casos = Caso.query.count()
    n_personas = Persona.query.count()
    n_alias = Alias.query.count()
    n_telefonos = Telefono.query.count()
    n_ubicaciones = Ubicacion.query.count()
    n_consultas = ConsultaOsint.query.count()
    n_indicadores = IndicadorRiesgo.query.count()
    n_nodos = IntelNode.query.count()
    n_aristas = IntelEdge.query.count()
    n_hallazgos = HallazgoIntel.query.count()

    def pct(n, d):
        return min(100, int((n / max(1, d)) * 100)) if n > 0 else 0

    etapas = [
        {"id": "captura", "nombre": "Captura / Línea 147", "estado": "completado" if n_casos > 0 else "pendiente", "registros": n_casos, "porcentaje": 100 if n_casos > 0 else 0},
        {"id": "gestion", "nombre": "Gestión de Casos", "estado": "completado" if n_casos > 0 else "pendiente", "registros": n_casos, "porcentaje": 100 if n_casos > 0 else 0},
        {"id": "transac", "nombre": "Base Transaccional", "estado": "completado" if n_casos > 0 else "pendiente", "registros": n_casos + n_personas, "porcentaje": 100 if n_casos > 0 else 0},
        {"id": "etl", "nombre": "Motor ETL y Correlación", "estado": "en_proceso" if (n_personas + n_alias) > 0 else ("en_proceso" if n_casos > 0 else "pendiente"), "registros": n_personas + n_alias + n_telefonos, "porcentaje": max(10 if n_casos > 0 else 0, min(90, pct(n_personas + n_alias, n_casos * 3 + 1)))},
        {"id": "dw", "nombre": "Data Warehouse / Grafo de Relaciones", "estado": "en_proceso" if n_nodos > 0 else ("en_proceso" if n_casos > 0 else "pendiente"), "registros": n_nodos, "porcentaje": max(8 if n_casos > 0 else 0, min(80, pct(n_nodos, n_personas + 10)))},
        {"id": "datamart", "nombre": "Data Mart de Inteligencia", "estado": "en_proceso" if n_hallazgos > 0 else ("en_proceso" if n_casos > 0 else "pendiente"), "registros": n_hallazgos, "porcentaje": max(5 if n_casos > 0 else 0, min(70, pct(n_hallazgos, n_personas + 5)))},
        {"id": "dashboard_ia", "nombre": "Dashboard IA / GIS / Analítica", "estado": "en_proceso" if n_indicadores > 0 else ("en_proceso" if n_casos > 0 else "pendiente"), "registros": n_indicadores, "porcentaje": max(3 if n_casos > 0 else 0, min(60, pct(n_indicadores, n_hallazgos + 3)))},
        {"id": "decisiones", "nombre": "Toma de Decisiones", "estado": "completado" if n_casos > 0 else "pendiente", "registros": n_casos, "porcentaje": 100 if n_casos > 0 else 0},
    ]

    return jsonify({
        "ultima_ejecucion": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        "estado_general": "nominal" if n_casos > 0 else "sin_datos",
        "etapas": etapas,
        "metricas": {
            "casos": n_casos,
            "personas": n_personas,
            "alias": n_alias,
            "telefonos": n_telefonos,
            "ubicaciones": n_ubicaciones,
            "consultas_osint": n_consultas,
            "indicadores_riesgo": n_indicadores,
            "nodos_grafo": n_nodos,
            "aristas_grafo": n_aristas,
            "hallazgos": n_hallazgos,
        },
    })


@nexo.route("/health")
def health():
    return {"status": "ok", "service": "NEXO-147 Demo"}


@nexo.route('/api_externa', methods=['POST', 'GET'])
def api_externa():
    url = "https://haveibeenpwned.com/api/v3/breaches"

    if request.method == 'GET':
        try:
            response = requests.get(url)

            if response.status_code != 200:
                return jsonify({
                    "error": f"Error al conectar con la API externa: {response.status_code}"
                }), response.status_code

            response.raise_for_status()
            datos = response.json()
            resultados = []

            for brecha in datos:
                resultados.append({
                    "Nombre": brecha["Name"],
                    "Dominio": brecha["Domain"],
                    "Fecha": brecha["BreachDate"],
                    "Cantidad_afectados": brecha["PwnCount"],
                    "Descripcion": brecha["Description"]
                })

            return render_template("brechas_seguridad.html", brechas=resultados)

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({
        "Mensaje": "Endpoint de API externa, envía una solicitud POST con datos JSON."
    }), 200


if __name__ == "__main__":
    os.makedirs(os.path.join(_basedir, "data"), exist_ok=True)
    seed_db()
    port = int(os.environ.get("PORT", 5000))
    nexo.run(host="0.0.0.0", port=port, debug=True)