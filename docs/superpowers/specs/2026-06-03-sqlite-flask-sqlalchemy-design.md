# Diseño: Migración a SQLite con Flask-SQLAlchemy

**Fecha:** 2026-06-03  
**Proyecto:** NEXO-147 (DEMO_GAULA)  
**Alcance:** Reemplazar almacenamiento en archivo JSONL y usuarios hardcodeados por SQLite usando Flask-SQLAlchemy

---

## Contexto

El proyecto es una app Flask de demo que gestiona reportes de la Línea 147 / GAULA. Actualmente:
- Los usuarios están hardcodeados en un diccionario `USERS` en `app.py`
- Los reportes se guardan en `data/reportes_147.jsonl` (una línea JSON por reporte)
- No hay dependencia de servicios externos de base de datos

El objetivo es migrar a SQLite para poder demostrar control de acceso por roles con datos persistentes, sin requerir servicios externos.

---

## Arquitectura

**Dependencia nueva:** `flask-sqlalchemy`  
**Archivo de base de datos:** `data/nexo147.db` (no versionado en git)  
**Hashing de contraseñas:** `werkzeug.security` (ya incluido con Flask)

La instancia `db = SQLAlchemy(nexo)` se inicializa en `app.py`. Los modelos `Usuario` y `Reporte` se definen como clases en el mismo archivo (el proyecto es pequeño, no justifica separar en módulos).

Al arrancar la app se ejecuta `db.create_all()` y si la tabla `usuarios` está vacía se insertan los 4 usuarios de demo (seed).

---

## Modelos

### `Usuario`

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

### `Reporte`

```python
class Reporte(db.Model):
    __tablename__ = "reportes"
    id                   = db.Column(db.Integer, primary_key=True)
    id_reporte           = db.Column(db.String(36), nullable=False)
    fecha_registro       = db.Column(db.DateTime, default=datetime.utcnow)
    estado               = db.Column(db.String(20), default="Recibido")
    usuario_registro     = db.Column(db.String(50))
    rol_usuario          = db.Column(db.String(20))
    # Clasificación
    tipo_reporte         = db.Column(db.String(50))
    prioridad            = db.Column(db.String(20))
    unidad_gaula         = db.Column(db.String(100))
    canal_recepcion      = db.Column(db.String(50))
    # Reportante
    nombre_reportante    = db.Column(db.String(100))
    documento_reportante = db.Column(db.String(30))
    telefono_reportante  = db.Column(db.String(20))
    ubicacion            = db.Column(db.String(200))
    # Caso
    descripcion          = db.Column(db.Text)
    numero_extorsivo     = db.Column(db.String(30))
    alias_sospechoso     = db.Column(db.String(100))
    medio_pago           = db.Column(db.String(50))
    valor_exigido        = db.Column(db.String(50))
    evidencia            = db.Column(db.String(200))
    observaciones        = db.Column(db.Text)
```

No se define FK explícita entre `reportes.usuario_registro` y `usuarios.username` para preservar historial si un usuario es desactivado.

---

## Roles y permisos

| Rol | Registrar reporte | Ver reportes | Dashboard | Gestión usuarios |
|---|:---:|:---:|:---:|:---:|
| `admin` | SI | SI | SI | SI |
| `director` | NO | SI (lectura) | SI | NO |
| `analista` | NO | SI + cambiar estado | NO | NO |
| `operador` | SI | NO | NO | NO |

### Decoradores

Se mantienen los decoradores existentes y se agregan dos nuevos:

- `@login_required` — cualquier sesión activa
- `@admin_required` — solo `admin`
- `@director_required` — `admin`, `director`
- `@analista_required` — `admin`, `analista`
- `@operador_required` — `admin`, `operador` (ya existente, se ajusta)

---

## Flujos principales

### Login
1. `POST /login` recibe `usuario` y `password`
2. `Usuario.query.filter_by(username=usuario, activo=True).first()`
3. `check_password_hash(user.password_hash, password)`
4. Si válido: guarda `session["user"]`, `session["role"]`, `session["name"]`
5. Redirige según rol (api_general ya no existe como rol separado)

### Guardar reporte
1. `POST /registrar-reporte` — requiere `@login_required`
2. Valida campos obligatorios: `tipo_reporte`, `prioridad`, `descripcion`
3. Crea `Reporte(**datos)` con `id_reporte=uuid4()`
4. `db.session.add(reporte)` → `db.session.commit()`
5. Retorna UUID al cliente

### Cargar reportes (dashboard)
1. `GET /dashboard` — requiere `@admin_required` o `@director_required`
2. `Reporte.query.order_by(Reporte.fecha_registro.desc()).all()`
3. Agrupaciones para stats: filtros por `prioridad`, `tipo_reporte`

### Seed inicial
```python
with nexo.app_context():
    db.create_all()
    if Usuario.query.count() == 0:
        usuarios_demo = [
            ("admin",    "Admin147*",    "Administrador NEXO-147",  "admin"),
            ("director", "Director147*", "Director GAULA",          "director"),
            ("analista", "Analista147*", "Analista Operacional",    "analista"),
            ("operador", "Operador147*", "Operador Línea 147",      "operador"),
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

---

## Cambios en `requirements.txt`

Agregar:
```
flask-sqlalchemy==3.1.1
```

---

## Archivos afectados

| Archivo | Cambio |
|---|---|
| `app.py` | Agregar modelos, reemplazar USERS, reemplazar funciones de archivo |
| `requirements.txt` | Agregar `flask-sqlalchemy` |
| `.gitignore` | Agregar `data/nexo147.db` |
| `docs/DATABASE.md` | Ya creado — referencia de esquema |

Los templates (`dashboard.html`, `index.html`) no requieren cambios porque los datos se pasan con la misma estructura de variables.

---

## Eliminaciones del código actual

| Elemento | Acción |
|---|---|
| Diccionario `USERS` | Eliminado — reemplazado por tabla `usuarios` |
| Funciones `guardar_reporte()` / `cargar_reportes()` | Eliminadas — reemplazadas por ORM |
| Rol `api_general` | Eliminado — no tiene equivalente en los 4 roles nuevos |
| Ruta `/api_general` | Eliminada — servía para exponer un JSON de archivo hardcodeado |
| Ruta `/registrar_reporte` (con guión bajo) | Eliminada — duplicado de `/registrar-reporte` que guardaba en carpeta local |
| Decorador `@api_required` | Eliminado junto con el rol |

---

## Lo que NO cambia

- Estructura de templates HTML
- Rutas existentes (`/`, `/login`, `/logout`, `/dashboard`, `/registrar-reporte`)
- Lógica de la ruta `/api_externa` (consulta HIBP)
- Estilos CSS
- Archivos estáticos
