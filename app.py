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


class Reporte(db.Model):
    __tablename__ = "reportes"
    id                   = db.Column(db.Integer, primary_key=True)
    id_reporte           = db.Column(db.String(36), nullable=False)
    fecha_registro       = db.Column(db.DateTime, default=datetime.utcnow)
    estado               = db.Column(db.String(20), default="Recibido")
    usuario_registro     = db.Column(db.String(50))
    rol_usuario          = db.Column(db.String(20))
    tipo_reporte         = db.Column(db.String(50))
    prioridad            = db.Column(db.String(20))
    unidad_gaula         = db.Column(db.String(100))
    canal_recepcion      = db.Column(db.String(50))
    nombre_reportante    = db.Column(db.String(100))
    documento_reportante = db.Column(db.String(30))
    telefono_reportante  = db.Column(db.String(20))
    ubicacion            = db.Column(db.String(200))
    descripcion          = db.Column(db.Text)
    numero_extorsivo     = db.Column(db.String(30))
    alias_sospechoso     = db.Column(db.String(100))
    medio_pago           = db.Column(db.String(50))
    valor_exigido        = db.Column(db.String(50))
    evidencia            = db.Column(db.String(200))
    observaciones        = db.Column(db.Text)


def seed_db():
    with nexo.app_context():
        db.create_all()
        if Usuario.query.count() == 0:
            usuarios_demo = [
                ("admin",    "Admin147*",    "Administrador NEXO-147", "admin"),
                ("director", "Director147*", "Director GAULA",         "director"),
                ("analista", "Analista147*", "Analista Operacional",   "analista"),
                ("operador", "Operador147*", "Operador Línea 147",     "operador"),
            ]
            for username, pwd, nombre, rol in usuarios_demo:
                db.session.add(Usuario(
                    username=username,
                    password_hash=generate_password_hash(pwd),
                    nombre=nombre,
                    rol=rol
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

    tipo_reporte = data.get("tipo_reporte", "").strip()
    prioridad    = data.get("prioridad", "").strip()
    descripcion  = data.get("descripcion", "").strip()

    if not tipo_reporte or not prioridad or not descripcion:
        if request.is_json:
            return {"error": "Debe registrar tipo de reporte, prioridad y descripción mínima."}, 400
        flash("Debe registrar tipo de reporte, prioridad y descripción mínima.", "error")
        return redirect(url_for("home") + "#reporte")

    reporte = Reporte(
        id_reporte           = str(uuid.uuid4()),
        usuario_registro     = session.get("user"),
        rol_usuario          = session.get("role"),
        tipo_reporte         = tipo_reporte,
        prioridad            = prioridad,
        unidad_gaula         = data.get("unidad_gaula", "").strip(),
        canal_recepcion      = data.get("canal_recepcion", "").strip(),
        nombre_reportante    = data.get("nombre_reportante", "").strip(),
        documento_reportante = data.get("documento_reportante", "").strip(),
        telefono_reportante  = data.get("telefono_reportante", "").strip(),
        ubicacion            = data.get("ubicacion", "").strip(),
        descripcion          = descripcion,
        numero_extorsivo     = data.get("numero_extorsivo", "").strip(),
        alias_sospechoso     = data.get("alias_sospechoso", "").strip(),
        medio_pago           = data.get("medio_pago", "").strip(),
        valor_exigido        = data.get("valor_exigido", "").strip(),
        evidencia            = data.get("evidencia", "").strip(),
        observaciones        = data.get("observaciones", "").strip(),
    )
    db.session.add(reporte)
    db.session.commit()

    if request.is_json:
        return {"mensaje": f"Reporte registrado correctamente. Código interno: {reporte.id_reporte}", "id_reporte": reporte.id_reporte}, 201
    flash(f"Reporte registrado correctamente. Código interno: {reporte.id_reporte}", "ok")
    return redirect(url_for("home") + "#reporte")


@nexo.route("/dashboard")
@director_required
def dashboard():
    reportes = Reporte.query.order_by(Reporte.fecha_registro.desc()).all()

    total_reportes = len(reportes)
    casos_criticos = sum(1 for r in reportes if (r.prioridad or "").lower() == "crítica")

    tipos_conteo = {}
    for r in reportes:
        tipo = r.tipo_reporte or "Sin clasificar"
        tipos_conteo[tipo] = tipos_conteo.get(tipo, 0) + 1

    if not tipos_conteo:
        tipos_conteo = {
            "Extorsión": 18,
            "Hurto": 11,
            "Fraude digital": 9,
            "Amenaza": 7,
            "Secuestro": 3
        }

    max_tipo = max(tipos_conteo.values()) if tipos_conteo else 1

    tipos = [
        {
            "tipo": tipo,
            "cantidad": cantidad,
            "porcentaje": f"{int((cantidad / max_tipo) * 100)}%"
        }
        for tipo, cantidad in tipos_conteo.items()
    ]

    stats = {
        "casos_activos":     total_reportes if total_reportes else 48,
        "casos_criticos":    casos_criticos if total_reportes else 12,
        "gaulas_conectados": 34,
        "tiempo_respuesta":  "08m",
        "reportes_147":      total_reportes if total_reportes else 124,
        "alertas_osint":     19
    }

    return render_template(
        "dashboard.html",
        reportes=reportes,
        stats=stats,
        tipos=tipos
    )


@nexo.route("/api/casos", methods=["GET"])
@login_required
def api_casos():
    role = session.get("role")
    username = session.get("user")
    if role == "operador":
        reportes = Reporte.query.filter_by(usuario_registro=username).order_by(Reporte.fecha_registro.desc()).all()
    else:
        reportes = Reporte.query.order_by(Reporte.fecha_registro.desc()).all()
    
    resultados = []
    for r in reportes:
        resultados.append({
            "id_reporte": r.id_reporte,
            "fecha_registro": r.fecha_registro.strftime('%Y-%m-%d %H:%M') if r.fecha_registro else "",
            "estado": r.estado,
            "usuario_registro": r.usuario_registro,
            "rol_usuario": r.rol_usuario,
            "tipo_reporte": r.tipo_reporte,
            "prioridad": r.prioridad,
            "unidad_gaula": r.unidad_gaula,
            "canal_recepcion": r.canal_recepcion,
            "nombre_reportante": r.nombre_reportante,
            "documento_reportante": r.documento_reportante,
            "telefono_reportante": r.telefono_reportante,
            "ubicacion": r.ubicacion,
            "descripcion": r.descripcion,
            "numero_extorsivo": r.numero_extorsivo,
            "alias_sospechoso": r.alias_sospechoso,
            "medio_pago": r.medio_pago,
            "valor_exigido": r.valor_exigido,
            "evidencia": r.evidencia,
            "observaciones": r.observaciones
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
        return jsonify({"error": "Debe proporcionar un estado válido."}), 400
        
    reporte = Reporte.query.filter_by(id_reporte=id_reporte).first()
    if not reporte:
        return jsonify({"error": "Caso no encontrado."}), 404
        
    reporte.estado = nuevo_estado
    db.session.commit()
    return jsonify({"mensaje": f"Estado actualizado a: {nuevo_estado}", "id_reporte": id_reporte})


@nexo.route("/api/entidades", methods=["GET"])
@login_required
def api_entidades():
    reportes = Reporte.query.all()
    
    personas = [
        {"nombre": "Carlos Mendoza", "documento": "1.023.456.789", "rol": "Sospechoso", "casos_vinculados": ["147-001", "147-003"]},
        {"nombre": "Diana Restrepo", "documento": "52.345.678", "rol": "Reportante", "casos_vinculados": ["147-002"]},
        {"nombre": "Andrés Felipe Gómez", "documento": "1.018.990.123", "rol": "Víctima", "casos_vinculados": ["147-005"]},
    ]
    telefonos = [
        {"numero": "3124567890", "compania": "Claro", "tipo": "Extorsivo", "casos_vinculados": ["147-001", "147-004"]},
        {"numero": "3209876543", "compania": "Movistar", "tipo": "Sospechoso", "casos_vinculados": ["147-003"]},
        {"numero": "3151112233", "compania": "Tigo", "tipo": "Víctima", "casos_vinculados": ["147-002"]},
    ]
    alias = [
        {"nombre": "El Zarco", "descripcion": "Cabecilla de banda de extorsión carcelaria", "casos_vinculados": ["147-001", "147-004"]},
        {"nombre": "La Patrona", "descripcion": "Coordinadora de cobros en cuentas digitales", "casos_vinculados": ["147-003"]},
        {"nombre": "El Ingeniero", "descripcion": "Encargado de estafas informáticas y phishing", "casos_vinculados": ["147-005"]},
    ]
    ubicaciones = [
        {"nombre": "Bogotá - Localidad Kennedy", "coordenadas": "4.6200, -74.1500", "tipo": "Foco delictivo", "casos_vinculados": ["147-001", "147-002"]},
        {"nombre": "Medellín - El Poblado", "coordenadas": "6.2100, -75.5700", "tipo": "Zona de amenazas", "casos_vinculados": ["147-003"]},
        {"nombre": "Cali - Distrito de Aguablanca", "coordenadas": "3.4200, -76.4800", "tipo": "Cobro extorsión", "casos_vinculados": ["147-004", "147-005"]},
    ]
    
    for r in reportes:
        code_pfx = r.id_reporte[:7]
        if r.nombre_reportante and not any(p["nombre"].lower() == r.nombre_reportante.lower() for p in personas):
            personas.append({
                "nombre": r.nombre_reportante,
                "documento": r.documento_reportante or "No registra",
                "rol": "Reportante",
                "casos_vinculados": [code_pfx]
            })
        if r.telefono_reportante and not any(t["numero"] == r.telefono_reportante for t in telefonos):
            telefonos.append({
                "numero": r.telefono_reportante,
                "compania": "No identificada",
                "tipo": "Contacto",
                "casos_vinculados": [code_pfx]
            })
        if r.numero_extorsivo and not any(t["numero"] == r.numero_extorsivo for t in telefonos):
            telefonos.append({
                "numero": r.numero_extorsivo,
                "compania": "No identificada",
                "tipo": "Extorsivo",
                "casos_vinculados": [code_pfx]
            })
        if r.alias_sospechoso and not any(a["nombre"].lower() == r.alias_sospechoso.lower() for a in alias):
            alias.append({
                "nombre": r.alias_sospechoso,
                "descripcion": "Alias reportado en llamada",
                "casos_vinculados": [code_pfx]
            })
        if r.ubicacion and not any(u["nombre"].lower() == r.ubicacion.lower() for u in ubicaciones):
            ubicaciones.append({
                "nombre": r.ubicacion,
                "coordenadas": "4.5708, -74.2973",
                "tipo": "Foco delictivo",
                "casos_vinculados": [code_pfx]
            })
            
    return jsonify({
        "personas": personas,
        "telefonos": telefonos,
        "alias": alias,
        "ubicaciones": ubicaciones
    })


@nexo.route("/api/inteligencia/relaciones", methods=["GET"])
@login_required
def api_inteligencia_relaciones():
    reportes = Reporte.query.all()
    
    relaciones = [
        {"origen": "3124567890", "destino": "El Zarco", "tipo": "Uso", "confianza": "95%"},
        {"origen": "El Zarco", "destino": "Carlos Mendoza", "tipo": "Alias de", "confianza": "99%"},
        {"origen": "Carlos Mendoza", "destino": "Bogotá - Localidad Kennedy", "tipo": "Ubicado en", "confianza": "85%"},
        {"origen": "3209876543", "destino": "La Patrona", "tipo": "Uso", "confianza": "90%"},
    ]
    
    for r in reportes:
        if r.numero_extorsivo and r.alias_sospechoso:
            relaciones.append({
                "origen": r.numero_extorsivo,
                "destino": r.alias_sospechoso,
                "tipo": "Reportado contra",
                "confianza": "90%"
            })
        if r.alias_sospechoso and r.nombre_reportante:
            relaciones.append({
                "origen": r.alias_sospechoso,
                "destino": r.nombre_reportante,
                "tipo": "Amenaza a",
                "confianza": "80%"
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