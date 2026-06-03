# SQLite + Flask-SQLAlchemy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrar el almacenamiento de NEXO-147 de archivos JSONL y usuarios hardcodeados a SQLite usando Flask-SQLAlchemy, con 4 roles (admin, director, analista, operador) y seed automático.

**Architecture:** Flask-SQLAlchemy gestiona dos tablas (`usuarios`, `reportes`) en `data/nexo147.db`. Los modelos se definen en `app.py`. Al arrancar, `db.create_all()` crea las tablas y un seed inserta los 4 usuarios demo si la tabla está vacía.

**Tech Stack:** Flask 3.1.3, Flask-SQLAlchemy 3.1.1, SQLite (stdlib), werkzeug.security (incluido en Flask)

---

## Archivos afectados

| Archivo | Acción |
|---|---|
| `requirements.txt` | Agregar `flask-sqlalchemy==3.1.1` |
| `.gitignore` | Agregar `data/nexo147.db` |
| `app.py` | Refactor principal: modelos, seed, login, decoradores, rutas |
| `templates/dashboard.html` | Actualizar acceso de campos: `r.datos.tipo_reporte` → `r.tipo_reporte` |

---

## Task 1: Instalar dependencia y actualizar .gitignore

**Files:**
- Modify: `requirements.txt`
- Modify: `.gitignore` (crear si no existe)

- [ ] **Step 1: Agregar flask-sqlalchemy a requirements.txt**

Contenido final de `requirements.txt`:
```
blinker==1.9.0
click==8.4.0
colorama==0.4.6
Flask==3.1.3
flask-sqlalchemy==3.1.1
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.3
Werkzeug==3.1.8
```

- [ ] **Step 2: Instalar la dependencia**

```bash
pip install flask-sqlalchemy==3.1.1
```

Salida esperada: `Successfully installed flask-sqlalchemy-3.1.1 SQLAlchemy-2.x.x`

- [ ] **Step 3: Verificar instalación**

```bash
python -c "from flask_sqlalchemy import SQLAlchemy; print('OK')"
```

Salida esperada: `OK`

- [ ] **Step 4: Agregar nexo147.db a .gitignore**

Crear o editar `.gitignore` en la raíz del proyecto:
```
data/nexo147.db
data/*.db
__pycache__/
*.pyc
.env
venv/
.venv/
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore
git commit -m "chore: agregar flask-sqlalchemy y excluir db de git"
```

---

## Task 2: Configurar SQLAlchemy e imports en app.py

**Files:**
- Modify: `app.py` (líneas 1-15)

- [ ] **Step 1: Reemplazar bloque de imports y configuración inicial**

Reemplazar las líneas 1–15 del `app.py` actual por:

```python
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
nexo.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data/nexo147.db"
nexo.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(nexo)
```

> `json` y `Path` se mantienen temporalmente porque las rutas obsoletas aún los usan. Se eliminan en Task 11 junto con esas rutas.

- [ ] **Step 2: Eliminar constantes de archivo obsoletas**

Eliminar estas dos líneas del archivo original (estaban después de la config):
```python
DATA_DIR = "data"
REPORTES_FILE = os.path.join(DATA_DIR, "reportes_147.jsonl")
```

- [ ] **Step 3: Verificar que el archivo arranca sin error de imports**

```bash
python -c "import app; print('imports OK')"
```

Salida esperada: `imports OK` (puede haber warnings de SQLAlchemy sobre tablas no creadas, es normal)

---

## Task 3: Definir modelo Usuario

**Files:**
- Modify: `app.py` (insertar después de `db = SQLAlchemy(nexo)`)

- [ ] **Step 1: Insertar clase Usuario en app.py**

Después de la línea `db = SQLAlchemy(nexo)`, agregar:

```python
class Usuario(db.Model):
    __tablename__ = "usuarios"
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre        = db.Column(db.String(100), nullable=False)
    rol           = db.Column(db.String(20), nullable=False)
    activo        = db.Column(db.Boolean, default=True)
```

---

## Task 4: Definir modelo Reporte

**Files:**
- Modify: `app.py` (insertar después de clase Usuario)

- [ ] **Step 1: Insertar clase Reporte en app.py**

Después de la clase `Usuario`, agregar:

```python
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
```

---

## Task 5: Función seed y startup

**Files:**
- Modify: `app.py` (insertar función seed, modificar bloque `__main__`)

- [ ] **Step 1: Insertar función seed_db después de los modelos**

```python
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
```

- [ ] **Step 2: Reemplazar bloque final `__main__`**

Reemplazar:
```python
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    nexo.run(host="0.0.0.0", port=port, debug=True)
```

Por:
```python
if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    seed_db()
    port = int(os.environ.get("PORT", 5000))
    nexo.run(host="0.0.0.0", port=port, debug=True)
```

- [ ] **Step 3: Verificar que la base de datos se crea correctamente**

```bash
python -c "
import os; os.makedirs('data', exist_ok=True)
from app import nexo, db, seed_db, Usuario
seed_db()
with nexo.app_context():
    users = Usuario.query.all()
    for u in users:
        print(u.username, u.rol)
"
```

Salida esperada:
```
admin admin
director director
analista analista
operador operador
```

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: agregar modelos SQLAlchemy y seed de usuarios demo"
```

---

## Task 6: Actualizar ruta de login

**Files:**
- Modify: `app.py` — función `login()` y eliminar diccionario `USERS`

- [ ] **Step 1: Eliminar el diccionario USERS**

Eliminar completamente el bloque:
```python
USERS = {
    "admin": { ... },
    "operador": { ... },
    "api": { ... }
}
```

- [ ] **Step 2: Reemplazar función login()**

Reemplazar la función `login()` completa por:

```python
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
```

- [ ] **Step 3: Verificar login arranca sin errores**

```bash
python -c "from app import nexo, login; print('login OK')"
```

Salida esperada: `login OK`

---

## Task 7: Actualizar decoradores de roles

**Files:**
- Modify: `app.py` — bloque de decoradores

- [ ] **Step 1: Reemplazar bloque de decoradores completo**

Reemplazar los decoradores `login_required`, `admin_required`, `api_required` por:

```python
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
```

---

## Task 8: Actualizar ruta registrar_reporte con ORM

**Files:**
- Modify: `app.py` — función `registrar_reporte()`, eliminar `guardar_reporte()` y `cargar_reportes()`

- [ ] **Step 1: Eliminar funciones guardar_reporte() y cargar_reportes()**

Eliminar completamente:
```python
def guardar_reporte(datos):
    ...

def cargar_reportes():
    ...
```

- [ ] **Step 2: Reemplazar función registrar_reporte()**

Reemplazar la función `registrar_reporte()` completa por:

```python
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
```

---

## Task 9: Actualizar ruta dashboard con ORM

**Files:**
- Modify: `app.py` — función `dashboard()`

- [ ] **Step 1: Reemplazar función dashboard() completa**

```python
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
        "casos_activos":   total_reportes if total_reportes else 48,
        "casos_criticos":  casos_criticos if total_reportes else 12,
        "gaulas_conectados": 34,
        "tiempo_respuesta": "08m",
        "reportes_147":    total_reportes if total_reportes else 124,
        "alertas_osint":   19
    }

    return render_template(
        "dashboard.html",
        reportes=reportes,
        stats=stats,
        tipos=tipos
    )
```

> Nota: el decorador cambia de `@admin_required` a `@director_required` para que `admin` y `director` puedan acceder.

---

## Task 10: Actualizar template dashboard.html

**Files:**
- Modify: `templates/dashboard.html` (líneas 158–161)

- [ ] **Step 1: Actualizar acceso de campos en la tabla de reportes**

En `templates/dashboard.html`, dentro del `{% for r in reportes %}`, reemplazar:

```html
<td>{{ r.fecha_registro }}</td>
<td>{{ r.datos.tipo_reporte }}</td>
<td>{{ r.datos.prioridad }}</td>
<td>{{ r.datos.unidad_gaula }}</td>
<td>{{ r.estado }}</td>
```

Por:

```html
<td>{{ r.fecha_registro.strftime('%Y-%m-%d %H:%M') }}</td>
<td>{{ r.tipo_reporte }}</td>
<td>{{ r.prioridad }}</td>
<td>{{ r.unidad_gaula }}</td>
<td>{{ r.estado }}</td>
```

---

## Task 11: Eliminar rutas y código obsoleto

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Eliminar ruta /registrar_reporte (guión bajo)**

Eliminar completamente la función `cargar_formulario()`:

```python
@nexo.post("/registrar_reporte")
@login_required
def cargar_formulario():
    ...
```

- [ ] **Step 2: Eliminar ruta /api_general**

Eliminar completamente la función `api_general()`:

```python
@nexo.route('/api_general', methods=['POST', 'GET'])
@api_required
def api_general():
    ...
```

- [ ] **Step 3: Limpiar imports que ya no se usan**

En `app.py`, reemplazar el bloque de imports por la versión limpia (sin `json` ni `Path`):

```python
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import os
import uuid
import requests
from bs4 import BeautifulSoup
```

- [ ] **Step 4: Verificar que no quedan referencias a elementos eliminados**

```bash
grep -n "api_required\|api_general\|USERS\|guardar_reporte\|cargar_reportes\|REPORTES_FILE\|DATA_DIR\|cargar_formulario" app.py
```

Salida esperada: sin resultados (grep retorna vacío).

- [ ] **Step 5: Commit**

```bash
git add app.py templates/dashboard.html
git commit -m "feat: migrar almacenamiento a SQLite con Flask-SQLAlchemy y 4 roles"
```

---

## Task 12: Prueba de humo final

- [ ] **Step 1: Arrancar la aplicación**

```bash
python app.py
```

Salida esperada:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

- [ ] **Step 2: Verificar seed en la base de datos**

En otra terminal:
```bash
python -c "
from app import nexo, Usuario
with nexo.app_context():
    for u in Usuario.query.all():
        print(u.username, u.rol, u.activo)
"
```

Salida esperada:
```
admin admin True
director director True
analista analista True
operador operador True
```

- [ ] **Step 3: Verificar login de cada rol en el navegador**

Abrir `http://localhost:5000/login` y verificar:

| Usuario | Contraseña | Acceso esperado |
|---|---|---|
| `admin` | `Admin147*` | Redirige a `/` (formulario) |
| `director` | `Director147*` | Redirige a `/` (formulario) |
| `analista` | `Analista147*` | Redirige a `/` (formulario) |
| `operador` | `Operador147*` | Redirige a `/` (formulario) |

- [ ] **Step 4: Verificar acceso al dashboard**

Logeado como `admin`: `http://localhost:5000/dashboard` → debe cargar  
Logeado como `operador`: `http://localhost:5000/dashboard` → debe redirigir con mensaje de acceso restringido

- [ ] **Step 5: Registrar un reporte de prueba y verificarlo en el dashboard**

1. Login como `operador`
2. Llenar el formulario con: tipo=Extorsión, prioridad=Crítica, descripcion=Prueba SQLite
3. Enviar — debe aparecer flash con UUID
4. Login como `admin` → ir a `/dashboard` → el reporte debe aparecer en la tabla

- [ ] **Step 6: Commit final**

```bash
git add .
git commit -m "test: verificar flujo completo login + reporte + dashboard con SQLite"
```
