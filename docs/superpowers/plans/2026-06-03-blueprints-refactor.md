# Blueprints Refactor — NEXO-147 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactorizar `app.py` (792 líneas) en blueprints por dominio de negocio usando Application Factory y optimizaciones SQLite, sin romper ninguna URL ni test existente.

**Architecture:** Application Factory en `modules/__init__.py`; `db` singleton en `modules/extensions.py`; cuatro blueprints nuevos (`auth`, `casos`, `inteligencia`, `dashboard`) dentro de `modules/`; el módulo `modules/osint/` queda intacto. Los templates se reorganizan en subcarpetas por blueprint.

**Tech Stack:** Flask 3.1.3, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.50, SQLite, pytest 8.3.5

---

## File Map

| Acción | Archivo | Responsabilidad |
|--------|---------|-----------------|
| Crear | `modules/extensions.py` | `db` singleton + SQLite pragmas WAL/cache |
| Crear | `modules/config.py` | `Config` y `TestConfig` classes |
| Modificar | `models/__init__.py` | Importar `db` desde `modules.extensions` en lugar de crearlo |
| Crear | `modules/auth/__init__.py` | `auth_bp = Blueprint("auth", ...)` |
| Crear | `modules/auth/decorators.py` | 5 decoradores de control de acceso |
| Crear | `modules/auth/routes.py` | Rutas `/`, `/login`, `/logout` |
| Crear | `modules/casos/__init__.py` | `casos_bp = Blueprint("casos", ...)` |
| Crear | `modules/casos/routes.py` | `/registrar-reporte`, `/api/casos`, `/api/casos/<id>/estado` |
| Crear | `modules/inteligencia/__init__.py` | `intel_bp = Blueprint("intel", ...)` |
| Crear | `modules/inteligencia/routes.py` | 6 rutas de inteligencia y ETL |
| Crear | `modules/dashboard/__init__.py` | `dashboard_bp = Blueprint("dashboard", ...)` |
| Crear | `modules/dashboard/routes.py` | `/dashboard`, brechas, indicadores, health, api_externa |
| Crear | `modules/__init__.py` | `create_app()` + `_register_blueprints()` + `_seed_db()` |
| Modificar | `app.py` | Reducir a 2 líneas |
| Modificar | `tests/conftest.py` | Usar `create_app()` de `modules` |
| Mover | `templates/login.html` → `templates/auth/login.html` | — |
| Mover | `templates/console.html` → `templates/casos/console.html` | — |
| Mover | `templates/index.html` → `templates/casos/index.html` | — |
| Mover | `templates/dashboard.html` → `templates/dashboard/dashboard.html` | — |
| Mover | `templates/brechas_seguridad.html` → `templates/dashboard/brechas_seguridad.html` | — |

---

## Task 1: Crear modules/extensions.py

**Files:**
- Create: `modules/extensions.py`

- [ ] **Step 1: Escribir extensions.py**

```python
# modules/extensions.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

db = SQLAlchemy()

@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA cache_size=10000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
```

- [ ] **Step 2: Verificar que el archivo existe y es importable**

```bash
python -c "from modules.extensions import db; print('OK:', db)"
```

Expected: `OK: <SQLAlchemy ...>`

- [ ] **Step 3: Commit**

```bash
git add modules/extensions.py
git commit -m "feat: agregar extensions.py con db singleton y pragmas SQLite WAL"
```

---

## Task 2: Crear modules/config.py

**Files:**
- Create: `modules/config.py`

- [ ] **Step 1: Escribir config.py**

```python
# modules/config.py
import os
from sqlalchemy.pool import StaticPool

_basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "demo-gaula-nexo-147")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(_basedir, "data", "nexo147.db")
    SQLALCHEMY_BINDS = {
        "intel": "sqlite:///" + os.path.join(_basedir, "data", "intel.db"),
        "osint": "sqlite:///" + os.path.join(_basedir, "data", "osint.db"),
    }
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_BINDS = {
        "intel": "sqlite:///:memory:",
        "osint": "sqlite:///:memory:",
    }
    # StaticPool necesario: SQLite :memory: pierde datos cuando cambia la conexión
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
```

- [ ] **Step 2: Verificar importación**

```bash
python -c "from modules.config import Config, TestConfig; print('URI:', Config.SQLALCHEMY_DATABASE_URI)"
```

Expected: `URI: sqlite:///...data/nexo147.db`

- [ ] **Step 3: Commit**

```bash
git add modules/config.py
git commit -m "feat: agregar config.py con Config y TestConfig para factory pattern"
```

---

## Task 3: Actualizar models/__init__.py

**Files:**
- Modify: `models/__init__.py`

El archivo actualmente crea `db = SQLAlchemy()`. Pasa a importarlo desde `modules.extensions`.

- [ ] **Step 1: Ejecutar tests para tener baseline**

```bash
pytest tests/ -v --tb=short
```

Anotar cuántos pasan. Expected: todos los tests pasan (o al menos los que pasaban antes).

- [ ] **Step 2: Modificar models/__init__.py**

Reemplazar el contenido completo del archivo:

```python
# models/__init__.py
from modules.extensions import db  # noqa: F401
```

- [ ] **Step 3: Ejecutar tests nuevamente — deben pasar igual**

```bash
pytest tests/ -v --tb=short
```

Expected: mismo resultado que Step 1. Si algún test falla, revisar imports en los archivos de modelo.

- [ ] **Step 4: Commit**

```bash
git add models/__init__.py
git commit -m "refactor: models importa db desde modules.extensions en lugar de crearlo"
```

---

## Task 4: Crear modules/auth/decorators.py y __init__.py

**Files:**
- Create: `modules/auth/__init__.py`
- Create: `modules/auth/decorators.py`

- [ ] **Step 1: Crear directorio y __init__.py**

```python
# modules/auth/__init__.py
from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

from modules.auth import routes  # noqa: F401, E402
```

- [ ] **Step 2: Crear decorators.py**

```python
# modules/auth/decorators.py
from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            flash("Acceso restringido a administradores.", "error")
            return redirect(url_for("auth.home"))
        return f(*args, **kwargs)
    return wrapper


def director_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") not in ["admin", "director"]:
            flash("Acceso restringido a directores y administradores.", "error")
            return redirect(url_for("auth.home"))
        return f(*args, **kwargs)
    return wrapper


def analista_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") not in ["admin", "analista"]:
            flash("Acceso restringido a analistas y administradores.", "error")
            return redirect(url_for("auth.home"))
        return f(*args, **kwargs)
    return wrapper


def operador_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") not in ["admin", "operador"]:
            flash("Acceso restringido a operadores y administradores.", "error")
            return redirect(url_for("auth.home"))
        return f(*args, **kwargs)
    return wrapper
```

- [ ] **Step 3: Commit**

```bash
git add modules/auth/__init__.py modules/auth/decorators.py
git commit -m "feat: crear blueprint auth con decoradores de control de acceso"
```

---

## Task 5: Crear modules/auth/routes.py

**Files:**
- Create: `modules/auth/routes.py`

Rutas `/`, `/login`, `/logout` extraídas de `app.py` líneas 138-166.

- [ ] **Step 1: Crear routes.py**

```python
# modules/auth/routes.py
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from modules.auth import auth_bp
from modules.auth.decorators import login_required
from models.nexo147 import Usuario


@auth_bp.route("/")
@login_required
def home():
    return render_template("casos/console.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()
        user = Usuario.query.filter_by(username=usuario, activo=True).first()
        if user and check_password_hash(user.password_hash, password):
            session["user"] = user.username
            session["role"] = user.rol
            session["name"] = user.nombre
            return redirect(url_for("auth.home"))
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
```

- [ ] **Step 2: Commit**

```bash
git add modules/auth/routes.py
git commit -m "feat: agregar rutas de auth (/, /login, /logout) al blueprint auth"
```

---

## Task 6: Crear modules/casos/

**Files:**
- Create: `modules/casos/__init__.py`
- Create: `modules/casos/routes.py`

Rutas `/registrar-reporte`, `/api/casos`, `/api/casos/<id>/estado` extraídas de `app.py` líneas 169-359.

- [ ] **Step 1: Crear __init__.py**

```python
# modules/casos/__init__.py
from flask import Blueprint

casos_bp = Blueprint("casos", __name__)

from modules.casos import routes  # noqa: F401, E402
```

- [ ] **Step 2: Crear routes.py**

```python
# modules/casos/routes.py
from flask import request, redirect, url_for, flash, session, jsonify
from modules.casos import casos_bp
from modules.auth.decorators import login_required
from modules.extensions import db
from models.nexo147 import Caso, Reportante, CasoReportante, Evidencia, EventoCaso, MedioPago, UnidadGaula
import uuid


@casos_bp.route("/registrar-reporte", methods=["POST"])
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
        return redirect(url_for("auth.home") + "#reporte")

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
    return redirect(url_for("auth.home") + "#reporte")


@casos_bp.route("/api/casos", methods=["GET"])
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
            "id_reporte":           c.id_caso,
            "fecha_registro":       c.fecha_registro.strftime('%Y-%m-%d %H:%M') if c.fecha_registro else "",
            "estado":               c.estado,
            "usuario_registro":     c.created_by,
            "tipo_reporte":         c.tipo_caso,
            "prioridad":            c.prioridad,
            "unidad_gaula":         unidad_nombre,
            "canal_recepcion":      c.canal_recepcion,
            "nombre_reportante":    rep.nombre if rep else "",
            "documento_reportante": rep.documento if rep else "",
            "telefono_reportante":  rep.telefono if rep else "",
            "descripcion":          c.descripcion,
            "medio_pago":           medio.tipo if medio else "",
            "valor_exigido":        str(medio.valor_exigido) if medio else "",
            "observaciones":        c.observaciones,
        })
    return jsonify(resultados)


@casos_bp.route("/api/casos/<id_reporte>/estado", methods=["POST"])
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
```

- [ ] **Step 3: Commit**

```bash
git add modules/casos/__init__.py modules/casos/routes.py
git commit -m "feat: crear blueprint casos con rutas de registro y API de casos"
```

---

## Task 7: Crear modules/inteligencia/

**Files:**
- Create: `modules/inteligencia/__init__.py`
- Create: `modules/inteligencia/routes.py`

Rutas de inteligencia extraídas de `app.py` líneas 362-741.

- [ ] **Step 1: Crear __init__.py**

```python
# modules/inteligencia/__init__.py
from flask import Blueprint

intel_bp = Blueprint("intel", __name__)

from modules.inteligencia import routes  # noqa: F401, E402
```

- [ ] **Step 2: Crear routes.py**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add modules/inteligencia/__init__.py modules/inteligencia/routes.py
git commit -m "feat: crear blueprint inteligencia con 6 rutas de intel y ETL"
```

---

## Task 8: Crear modules/dashboard/

**Files:**
- Create: `modules/dashboard/__init__.py`
- Create: `modules/dashboard/routes.py`

Rutas de dashboard extraídas de `app.py` líneas 268-302 y 448-774.

- [ ] **Step 1: Crear __init__.py**

```python
# modules/dashboard/__init__.py
from flask import Blueprint

dashboard_bp = Blueprint("dashboard", __name__)

from modules.dashboard import routes  # noqa: F401, E402
```

- [ ] **Step 2: Crear routes.py**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add modules/dashboard/__init__.py modules/dashboard/routes.py
git commit -m "feat: crear blueprint dashboard con vistas de director y APIs de brechas"
```

---

## Task 9: Crear modules/__init__.py (Application Factory)

**Files:**
- Create: `modules/__init__.py`

Este archivo reemplaza la lógica de arranque de `app.py`.

- [ ] **Step 1: Crear __init__.py**

```python
# modules/__init__.py
import os
from flask import Flask
from werkzeug.security import generate_password_hash
from modules.extensions import db
from modules.config import Config


def create_app(config=None):
    _basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app = Flask(__name__, template_folder=os.path.join(_basedir, "templates"), static_folder=os.path.join(_basedir, "static"))
    app.config.from_object(config or Config)

    db.init_app(app)

    @app.after_request
    def disable_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    _register_blueprints(app)

    with app.app_context():
        os.makedirs(os.path.join(_basedir, "data"), exist_ok=True)
        db.create_all()
        _seed_db()

    return app


def _register_blueprints(app):
    from modules.auth        import auth_bp
    from modules.casos       import casos_bp
    from modules.inteligencia import intel_bp
    from modules.dashboard   import dashboard_bp
    from modules.osint.social    import social_osint_bp
    from modules.osint.opendata  import opendata_osint_bp
    from modules.osint.analytics import analytics_osint_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(casos_bp)
    app.register_blueprint(intel_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(social_osint_bp,    url_prefix="/osint/social")
    app.register_blueprint(opendata_osint_bp,  url_prefix="/osint/opendata")
    app.register_blueprint(analytics_osint_bp, url_prefix="/osint/analytics")


def _seed_db():
    from models.nexo147 import Usuario, UnidadGaula
    from models.osint_graph import Node as OsintNode, OsintEdge  # noqa: F401

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
            db.session.add(UnidadGaula(nombre=nombre, ciudad=ciudad, departamento=depto, created_by="seed"))
        db.session.commit()

    from modules.osint.plugins.registry import discover_plugins
    discover_plugins()
```

- [ ] **Step 2: Verificar que la factory arranca**

```bash
python -c "from modules import create_app; app = create_app(); print('Blueprints:', list(app.blueprints.keys()))"
```

Expected (7 blueprints):
```
Blueprints: ['auth', 'casos', 'intel', 'dashboard', 'osint_social', 'osint_opendata', 'osint_analytics']
```

- [ ] **Step 3: Commit**

```bash
git add modules/__init__.py
git commit -m "feat: Application Factory create_app() con 7 blueprints y seed_db"
```

---

## Task 10: Actualizar tests/conftest.py

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Reemplazar contenido de conftest.py**

```python
# tests/conftest.py
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules import create_app
from modules.config import TestConfig
from modules.extensions import db as _db


@pytest.fixture(scope="function")
def app():
    app = create_app(TestConfig)
    with app.app_context():
        yield app


@pytest.fixture
def session(app):
    yield _db.session


@pytest.fixture
def client(app):
    return app.test_client()
```

- [ ] **Step 2: Ejecutar tests**

```bash
pytest tests/ -v --tb=short
```

Expected: todos los tests pasan. Si alguno falla por `from app import nexo`, revisar el archivo de test y corregir el import.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "refactor: conftest usa create_app() desde modules en lugar de importar nexo de app"
```

---

## Task 11: Reducir app.py a punto de entrada mínimo

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Reemplazar app.py completo**

```python
# app.py
from modules import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

- [ ] **Step 2: Verificar que la app arranca**

```bash
python -c "from app import app; print('Routes:', len(list(app.url_map.iter_rules())))"
```

Expected: `Routes: 21` (o el número de rutas total — debe ser mayor que 0 y coincidir con las rutas del sistema).

- [ ] **Step 3: Ejecutar suite completa de tests**

```bash
pytest tests/ -v --tb=short
```

Expected: todos pasan.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "refactor: app.py reducido a 4 líneas — punto de entrada que llama create_app()"
```

---

## Task 12: Mover templates a subcarpetas por blueprint

**Files:**
- Move: `templates/login.html` → `templates/auth/login.html`
- Move: `templates/console.html` → `templates/casos/console.html`
- Move: `templates/index.html` → `templates/casos/index.html`
- Move: `templates/dashboard.html` → `templates/dashboard/dashboard.html`
- Move: `templates/brechas_seguridad.html` → `templates/dashboard/brechas_seguridad.html`

- [ ] **Step 1: Crear subcarpetas y mover archivos**

En PowerShell (Windows):
```powershell
New-Item -ItemType Directory -Force templates/auth
New-Item -ItemType Directory -Force templates/casos
New-Item -ItemType Directory -Force templates/dashboard

Move-Item templates/login.html           templates/auth/login.html
Move-Item templates/console.html         templates/casos/console.html
Move-Item templates/index.html           templates/casos/index.html
Move-Item templates/dashboard.html       templates/dashboard/dashboard.html
Move-Item templates/brechas_seguridad.html templates/dashboard/brechas_seguridad.html
```

- [ ] **Step 2: Verificar que los render_template en routes ya usan las rutas correctas**

Las rutas ya están escritas con las rutas nuevas en los pasos anteriores:
- `modules/auth/routes.py`: `render_template("auth/login.html")` y `render_template("casos/console.html")`
- `modules/dashboard/routes.py`: `render_template("dashboard/dashboard.html")` y `render_template("dashboard/brechas_seguridad.html")`

Confirmar que ningún archivo de módulos OSINT (`modules/osint/`) hace `render_template` de los templates movidos:

```bash
grep -r "render_template" modules/osint/
```

Expected: solo referencias a `osint/` templates (no a `login.html`, `console.html`, etc.)

- [ ] **Step 3: Ejecutar tests**

```bash
pytest tests/ -v --tb=short
```

Expected: todos pasan.

- [ ] **Step 4: Commit**

```bash
git add templates/ modules/
git commit -m "refactor: reorganizar templates en subcarpetas por blueprint (auth, casos, dashboard)"
```

---

## Task 13: Verificación Final

**Files:**
- Ninguno nuevo — solo verificación.

- [ ] **Step 1: Ejecutar suite completa de tests**

```bash
pytest tests/ -v
```

Expected: todos los tests pasan con output similar a:
```
tests/test_nexo147_models.py  PASSED
tests/test_intel_models.py    PASSED
tests/test_osint_models.py    PASSED
tests/test_osint_api.py       PASSED
tests/test_migration.py       PASSED
```

- [ ] **Step 2: Verificar rutas registradas**

```bash
python -c "
from app import app
rules = sorted(str(r) for r in app.url_map.iter_rules())
for r in rules:
    print(r)
"
```

Expected: deben aparecer todas las rutas: `/`, `/login`, `/logout`, `/registrar-reporte`, `/api/casos`, `/dashboard`, `/api/brechas`, `/api/osint/brechas`, `/api/osint/indicadores`, `/api/intel/entidades`, `/api/intel/hallazgos`, `/api/intel/grafo`, `/api/etl/status`, `/api/entidades`, `/api/inteligencia/relaciones`, `/api_externa`, `/health`, `/osint/social/...`, etc.

- [ ] **Step 3: Verificar tamaño de app.py**

```bash
python -c "
with open('app.py') as f:
    lines = f.readlines()
print(f'app.py: {len(lines)} líneas (antes: 792)')
"
```

Expected: `app.py: 4 líneas (antes: 792)`

- [ ] **Step 4: Commit final**

```bash
git add -A
git commit -m "chore: verificación final — refactor blueprints completo, todos los tests pasan"
```

---

## Resumen de Commits Esperados

1. `feat: agregar extensions.py con db singleton y pragmas SQLite WAL`
2. `feat: agregar config.py con Config y TestConfig para factory pattern`
3. `refactor: models importa db desde modules.extensions en lugar de crearlo`
4. `feat: crear blueprint auth con decoradores de control de acceso`
5. `feat: agregar rutas de auth (/, /login, /logout) al blueprint auth`
6. `feat: crear blueprint casos con rutas de registro y API de casos`
7. `feat: crear blueprint inteligencia con 6 rutas de intel y ETL`
8. `feat: crear blueprint dashboard con vistas de director y APIs de brechas`
9. `feat: Application Factory create_app() con 7 blueprints y seed_db`
10. `refactor: conftest usa create_app() desde modules en lugar de importar nexo de app`
11. `refactor: app.py reducido a 4 líneas — punto de entrada que llama create_app()`
12. `refactor: reorganizar templates en subcarpetas por blueprint (auth, casos, dashboard)`
13. `chore: verificación final — refactor blueprints completo, todos los tests pasan`
