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
)
from models.osint import FuenteOsint, ConsultaOsint, CacheConsulta, ResultadoOsint, IndicadorRiesgo
from functools import wraps
from datetime import datetime
import os
import uuid
import requests
from bs4 import BeautifulSoup

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
                    nombre=nombre, ciudad=ciudad,
                    departamento=depto, created_by="seed",
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




@nexo.route("/")
@login_required
def home():
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

    tipo_caso   = data.get("tipo_reporte", "").strip()
    prioridad   = data.get("prioridad", "").strip()
    descripcion = data.get("descripcion", "").strip()

    if not tipo_caso or not prioridad or not descripcion:
        if request.is_json:
            return {"error": "Debe registrar tipo de reporte, prioridad y descripcion minima."}, 400
        flash("Debe registrar tipo de reporte, prioridad y descripcion minima.", "error")
        return redirect(url_for("home") + "#reporte")

    nombre_unidad = data.get("unidad_gaula", "").strip()
    unidad = None
    if nombre_unidad:
        unidad = UnidadGaula.query.filter_by(nombre=nombre_unidad).first()
        if not unidad:
            unidad = UnidadGaula(nombre=nombre_unidad, created_by=session.get("user"))
            db.session.add(unidad)
            db.session.flush()

    caso = Caso(
        id_caso         = str(uuid.uuid4()),
        estado          = "Recibido",
        prioridad       = prioridad,
        tipo_caso       = tipo_caso,
        canal_recepcion = data.get("canal_recepcion", "").strip(),
        unidad_gaula_id = unidad.id if unidad else None,
        descripcion     = descripcion,
        observaciones   = data.get("observaciones", "").strip(),
        created_by      = session.get("user"),
    )
    db.session.add(caso)
    db.session.flush()

    nombre_rep = data.get("nombre_reportante", "").strip()
    if nombre_rep or data.get("documento_reportante") or data.get("telefono_reportante"):
        rep = Reportante(
            nombre     = nombre_rep,
            documento  = data.get("documento_reportante", "").strip(),
            telefono   = data.get("telefono_reportante", "").strip(),
            anonimo    = not bool(nombre_rep),
            created_by = session.get("user"),
        )
        db.session.add(rep)
        db.session.flush()
        db.session.add(CasoReportante(
            caso_id       = caso.id,
            reportante_id = rep.id,
            rol_en_caso   = "denunciante",
            created_by    = session.get("user"),
        ))

    medio = data.get("medio_pago", "").strip()
    if medio:
        raw = data.get("valor_exigido", "0").strip().replace(",", "").replace("$", "") or "0"
        try:
            valor_decimal = float(raw)
        except ValueError:
            valor_decimal = 0.0
        db.session.add(MedioPago(
            caso_id       = caso.id,
            tipo          = medio,
            valor_exigido = valor_decimal,
            referencia    = data.get("numero_extorsivo", "").strip(),
            created_by    = session.get("user"),
        ))

    evidencia_txt = data.get("evidencia", "").strip()
    if evidencia_txt:
        db.session.add(Evidencia(
            caso_id     = caso.id,
            tipo        = "referencia",
            descripcion = evidencia_txt,
            created_by  = session.get("user"),
        ))

    db.session.add(EventoCaso(
        caso_id      = caso.id,
        tipo_evento  = "creacion",
        descripcion  = "Caso registrado desde formulario.",
        estado_nuevo = "Recibido",
        created_by   = session.get("user"),
    ))

    db.session.commit()

    if request.is_json:
        return {"mensaje": f"Reporte registrado. Codigo: {caso.id_caso}", "id_reporte": caso.id_caso}, 201
    flash(f"Reporte registrado correctamente. Codigo interno: {caso.id_caso}", "ok")
    return redirect(url_for("home") + "#reporte")


@nexo.route("/dashboard")
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
        tipos_conteo = {
            "Extorsion": 18, "Hurto": 11, "Fraude digital": 9,
            "Amenaza": 7,    "Secuestro": 3,
        }

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
        "alertas_osint":     19,
    }

    return render_template("dashboard.html", reportes=casos, stats=stats, tipos=tipos)


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
            "id_reporte":          c.id_caso,
            "fecha_registro":      c.fecha_registro.strftime('%Y-%m-%d %H:%M') if c.fecha_registro else "",
            "estado":              c.estado,
            "usuario_registro":    c.created_by,
            "tipo_reporte":        c.tipo_caso,
            "prioridad":           c.prioridad,
            "unidad_gaula":        unidad_nombre,
            "canal_recepcion":     c.canal_recepcion,
            "nombre_reportante":   rep.nombre if rep else "",
            "documento_reportante": rep.documento if rep else "",
            "telefono_reportante": rep.telefono if rep else "",
            "descripcion":         c.descripcion,
            "medio_pago":          medio.tipo if medio else "",
            "valor_exigido":       str(medio.valor_exigido) if medio else "",
            "observaciones":       c.observaciones,
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

    caso.estado = nuevo_estado
    db.session.commit()
    return jsonify({"mensaje": f"Estado actualizado a: {nuevo_estado}", "id_reporte": id_reporte})


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


@nexo.route("/api/brechas", methods=["GET"])
@login_required
def api_brechas():
    url = "https://haveibeenpwned.com/api/v3/breaches"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return jsonify([
                {"Nombre": "Adobe", "Dominio": "adobe.com", "Fecha": "2013-10-04", "Cantidad_afectados": 152445162, "Descripcion": "Adobe database compromise."},
                {"Nombre": "Canva", "Dominio": "canva.com", "Fecha": "2019-05-24", "Cantidad_afectados": 137000000, "Descripcion": "Canva security breach incident."},
                {"Nombre": "LinkedIn", "Dominio": "linkedin.com", "Fecha": "2016-05-17", "Cantidad_afectados": 164000000, "Descripcion": "Historical LinkedIn credential leak."}
            ])
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
        return jsonify(resultados)
    except Exception:
        return jsonify([
            {"Nombre": "Adobe", "Dominio": "adobe.com", "Fecha": "2013-10-04", "Cantidad_afectados": 152445162, "Descripcion": "Adobe database compromise."},
            {"Nombre": "Canva", "Dominio": "canva.com", "Fecha": "2019-05-24", "Cantidad_afectados": 137000000, "Descripcion": "Canva security breach incident."},
            {"Nombre": "LinkedIn", "Dominio": "linkedin.com", "Fecha": "2016-05-17", "Cantidad_afectados": 164000000, "Descripcion": "Historical LinkedIn credential leak."}
        ])


@nexo.route("/health")
def health():
    return {"status": "ok", "service": "NEXO-147 Demo"}


# Conexion api externa
@nexo.route('/api_externa', methods=['POST', 'GET'])
def api_externa():
    url = "https://haveibeenpwned.com/api/v3/breaches"
    if request.method == 'GET':
        try:
            response = requests.get(url)
            if response.status_code != 200:
                return jsonify({"error": f"Error al conectar con la API externa: {response.status_code}"}), response.status_code
            else:
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
    else:
        return jsonify({"Mensaje": "Endpoint de API externa, envía una solicitud POST con datos JSON."}), 200
    



if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    seed_db()
    port = int(os.environ.get("PORT", 5000))
    nexo.run(host="0.0.0.0", port=port, debug=True)