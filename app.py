from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime
import os
import json
import uuid

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "demo-gaula-nexo-147")

DATA_DIR = "data"
REPORTES_FILE = os.path.join(DATA_DIR, "reportes_147.jsonl")

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
    }
}


@app.after_request
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


@app.route("/")
@login_required
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()

        user = USERS.get(usuario)

        if user and user["password"] == password:
            session["user"] = usuario
            session["role"] = user["role"]
            session["name"] = user["name"]
            return redirect(url_for("home"))

        flash("Usuario o contraseña incorrectos.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/registrar-reporte", methods=["POST"])
@login_required
def registrar_reporte():
    datos = {
        "tipo_reporte": request.form.get("tipo_reporte", "").strip(),
        "prioridad": request.form.get("prioridad", "").strip(),
        "unidad_gaula": request.form.get("unidad_gaula", "").strip(),
        "canal_recepcion": request.form.get("canal_recepcion", "").strip(),
        "reportante": {
            "nombre": request.form.get("nombre_reportante", "").strip(),
            "documento": request.form.get("documento_reportante", "").strip(),
            "telefono": request.form.get("telefono_reportante", "").strip(),
            "ubicacion": request.form.get("ubicacion", "").strip()
        },
        "caso": {
            "descripcion": request.form.get("descripcion", "").strip(),
            "numero_extorsivo": request.form.get("numero_extorsivo", "").strip(),
            "alias_sospechoso": request.form.get("alias_sospechoso", "").strip(),
            "medio_pago": request.form.get("medio_pago", "").strip(),
            "valor_exigido": request.form.get("valor_exigido", "").strip(),
            "evidencia": request.form.get("evidencia", "").strip(),
            "observaciones": request.form.get("observaciones", "").strip()
        }
    }

    if not datos["tipo_reporte"] or not datos["prioridad"] or not datos["caso"]["descripcion"]:
        flash("Debe registrar tipo de reporte, prioridad y descripción mínima.", "error")
        return redirect(url_for("home") + "#reporte")

    id_reporte = guardar_reporte(datos)
    flash(f"Reporte registrado correctamente. Código interno: {id_reporte}", "ok")
    return redirect(url_for("home") + "#reporte")


@app.route("/dashboard")
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


@app.route("/health")
def health():
    return {"status": "ok", "service": "NEXO-147 Demo"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)