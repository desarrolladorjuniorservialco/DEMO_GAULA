from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import os
import json
import uuid
from pathlib import Path as path
import requests
from bs4 import BeautifulSoup

nexo = Flask(__name__, static_folder="static", template_folder="templates")
nexo.secret_key = os.getenv("SECRET_KEY", "demo-gaula-nexo-147")
_basedir = os.path.abspath(os.path.dirname(__file__))
nexo.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(_basedir, "data", "nexo147.db")
nexo.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(nexo)


class Usuario(db.Model):
    __tablename__ = "usuarios"
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre        = db.Column(db.String(100), nullable=False)
    rol           = db.Column(db.String(20), nullable=False)
    activo        = db.Column(db.Boolean, default=True)


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

USERS = {
    "admin": {
        "password": "Admin147*",
        "role": "admin",
        "name": "Administrador NEXO-147"
    },
    "operador": {
        "password": "Operador147*",
        "role": "operador",
        "name": "Operador Línea 147"
    },
    "api": {
        "password": "Api_general_nexo-147",
        "role": "api_general",
        "name": "API general del sistema"
    }
}

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
            flash("Acceso restringido. Usuario operador solo puede registrar reportes.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return wrapper

def api_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") not in ["api_general", "admin"]:
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return wrapper


def guardar_reporte(datos):
    os.makedirs(DATA_DIR, exist_ok=True)

    registro = {
        "id_reporte": str(uuid.uuid4()),
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "estado": "Recibido",
        "usuario_registro": session.get("user"),
        "rol_usuario": session.get("role"),
        "datos": datos
    }

    with open(REPORTES_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(registro, ensure_ascii=False) + "\n")

    return registro["id_reporte"]


def cargar_reportes():
    if not os.path.exists(REPORTES_FILE):
        return []

    reportes = []
    with open(REPORTES_FILE, "r", encoding="utf-8") as file:
        for line in file:
            try:
                reportes.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return reportes[::-1]


@nexo.route("/")
@login_required
def home():
    return render_template("index.html")


@nexo.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()

        user = USERS.get(usuario)
        role = USERS.get("api", {}).get("role", {})

        if user and user["password"] == password:
            session["user"] = usuario
            session["role"] = user["role"]
            session["name"] = user["name"]

            if session["role"] == role:
                return redirect(url_for("api_general"))
            
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
    # Handle both form-encoded and JSON requests
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    datos = {
        "tipo_reporte": data.get("tipo_reporte", "").strip(),
        "prioridad": data.get("prioridad", "").strip(),
        "unidad_gaula": data.get("unidad_gaula", "").strip(),
        "canal_recepcion": data.get("canal_recepcion", "").strip(),
        "reportante": {
            "nombre": data.get("nombre_reportante", "").strip(),
            "documento": data.get("documento_reportante", "").strip(),
            "telefono": data.get("telefono_reportante", "").strip(),
            "ubicacion": data.get("ubicacion", "").strip()
        },
        "caso": {
            "descripcion": data.get("descripcion", "").strip(),
            "numero_extorsivo": data.get("numero_extorsivo", "").strip(),
            "alias_sospechoso": data.get("alias_sospechoso", "").strip(),
            "medio_pago": data.get("medio_pago", "").strip(),
            "valor_exigido": data.get("valor_exigido", "").strip(),
            "evidencia": data.get("evidencia", "").strip(),
            "observaciones": data.get("observaciones", "").strip()
        }
    }

    if not datos["tipo_reporte"] or not datos["prioridad"] or not datos["caso"]["descripcion"]:
        if request.is_json:
            return {"error": "Debe registrar tipo de reporte, prioridad y descripción mínima."}, 400
        else:
            flash("Debe registrar tipo de reporte, prioridad y descripción mínima.", "error")
            return redirect(url_for("home") + "#reporte")

    id_reporte = guardar_reporte(datos)
    
    if request.is_json:
        return {"mensaje": f"Reporte registrado correctamente. Código interno: {id_reporte}", "id_reporte": id_reporte}, 201
    else:
        flash(f"Reporte registrado correctamente. Código interno: {id_reporte}", "ok")
        return redirect(url_for("home") + "#reporte")


@nexo.route("/dashboard")
@admin_required
def dashboard():
    reportes = cargar_reportes()

    total_reportes = len(reportes)
    casos_criticos = sum(
        1 for r in reportes
        if r.get("datos", {}).get("prioridad", "").lower() == "crítica"
    )

    tipos_conteo = {}
    for r in reportes:
        tipo = r.get("datos", {}).get("tipo_reporte", "Sin clasificar")
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
        "casos_activos": total_reportes if total_reportes else 48,
        "casos_criticos": casos_criticos if total_reportes else 12,
        "gaulas_conectados": 34,
        "tiempo_respuesta": "08m",
        "reportes_147": total_reportes if total_reportes else 124,
        "alertas_osint": 19
    }

    return render_template(
        "dashboard.html",
        reportes=reportes,
        stats=stats,
        tipos=tipos
    )


@nexo.route("/health")
def health():
    return {"status": "ok", "service": "NEXO-147 Demo"}


@nexo.post("/registrar_reporte")
@login_required
def cargar_formulario():
    try:
        datos = request.get_json()
        carpeta = "Reportes"
        os.makedirs(carpeta, exist_ok=True)
        marca_tiempo = datetime.now().strftime("%y%m%d_%H%M%S")
        nombre_archivo = f"Reporte_{marca_tiempo}.json"

        ruta = os.path.join("Reportes", nombre_archivo)

        with open(ruta, "w", encoding='utf-8') as archivo:
            json.dump(datos, archivo, indent=4, ensure_ascii=False)

        return jsonify({"Mensaje": "Denuncia guardada de manera satisfactoria",
                        "archivo": nombre_archivo}), 200

    except Exception as e:
        return jsonify({'Error': str(e)}), 500


@nexo.route('/api_general', methods=['POST', 'GET'])
@api_required
def api_general():
    carpeta_reportes = path('reportes')
    archivo = "Reporte_260519_162606"
    ruta = carpeta_reportes/f"{archivo}.json"
    if not ruta.exists():
        return jsonify({"Error": "Archivo inexistente, verifique elnombre del archivo."}), 404
    try:
        with open(ruta, 'r', encoding='utf-8') as archivo_json:
            datos = json.load(archivo_json)
            return jsonify(datos)
    except json.JSONDecodeError:

        return jsonify({
            "error": "JSON inválido"
        }), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

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