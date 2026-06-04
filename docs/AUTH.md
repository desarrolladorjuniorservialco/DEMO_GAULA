# Autenticación y autorización — NEXO-147

## Mecanismo

**Tipo:** Sesiones basadas en cookies (Flask `session`)  
**Hash de contraseñas:** Werkzeug `generate_password_hash` / `check_password_hash` (pbkdf2:sha256)  
**Sin JWT ni OAuth** — autenticación servidor-a-servidor clásica.

---

## Flujo de autenticación

```
1. Usuario accede a /login (GET)
   └── Si ya tiene sesión activa → redirige a /

2. Usuario envía formulario (POST /login)
   ├── Busca usuario en BD por username
   ├── Verifica hash de contraseña con Werkzeug
   ├── Si correcto: session["username"] = username
   │              session["rol"] = rol
   │              session["nombre"] = nombre
   │              Redirige a /
   └── Si incorrecto: renderiza login.html con error

3. La ruta / detecta el rol y redirige:
   ├── operador → /casos/console (consola de registro)
   └── admin/director/analista → /dashboard

4. POST /logout
   └── session.clear() → redirige a /login
```

---

## Roles

| Rol | Descripción |
|---|---|
| `admin` | Acceso total: casos, dashboard, usuarios |
| `director` | Dashboard + lectura de casos |
| `analista` | Lectura y actualización de estado de casos |
| `operador` | Solo registro de nuevos casos |

---

## Matriz de permisos

| Acción / Ruta | admin | director | analista | operador |
|---|:---:|:---:|:---:|:---:|
| `GET /login` | ✓ | ✓ | ✓ | ✓ |
| `GET /` (home) | ✓ | ✓ | ✓ | ✓ |
| `POST /registrar-reporte` | ✓ | — | — | ✓ |
| `GET /api/casos` | ✓ | ✓ | ✓ | — |
| `POST /api/casos/<id>/estado` | ✓ | — | ✓ | — |
| `GET /dashboard` | ✓ | ✓ | — | — |
| `GET /api/brechas` | ✓ | ✓ | ✓ | ✓ |
| `GET /api/osint/indicadores` | ✓ | ✓ | ✓ | ✓ |
| `GET /api/intel/*` | ✓ | ✓ | ✓ | ✓ |
| `GET /health` | ✓ | ✓ | ✓ | ✓ |
| Rutas OSINT | ✓ | ✓ | ✓ | — |

---

## Decoradores de rol

Definidos en `modules/auth/decorators.py`. Se aplican como decoradores de función sobre las rutas Flask.

### `@login_required`

Verifica que exista `session["username"]`. Si no, redirige a `/login`.

```python
from modules.auth.decorators import login_required

@app.route("/ruta-protegida")
@login_required
def ruta_protegida():
    ...
```

### `@admin_required`

Solo usuarios con `rol == "admin"`. Redirige a `/` si el rol no cumple.

### `@director_required`

Permite roles: `admin`, `director`.

### `@analista_required`

Permite roles: `admin`, `analista`.

### `@operador_required`

Permite roles: `admin`, `operador`.

---

## Implementación de decoradores

```python
# modules/auth/decorators.py
from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

def director_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if session.get("rol") not in ("admin", "director"):
            return redirect(url_for("auth.home"))
        return f(*args, **kwargs)
    return decorated
```

---

## Datos de sesión

La sesión Flask almacena en una cookie firmada (HMAC-SHA1 con `SECRET_KEY`):

```python
session = {
    "username": "admin",
    "rol": "admin",
    "nombre": "Administrador NEXO-147"
}
```

---

## Seguridad

| Medida | Implementación |
|---|---|
| Contraseñas hasheadas | Werkzeug pbkdf2:sha256, no texto plano |
| Cookie firmada | Flask session con SECRET_KEY |
| Cache-Control | `no-store, no-cache, must-revalidate` en todas las respuestas |
| Sin exposición de roles en HTML | El rol no se renderiza en el DOM público |
| Seed seguro | Los usuarios demo se insertan con hash, no texto plano |

---

## Cambiar la SECRET_KEY en producción

```bash
# Variable de entorno (recomendado)
export SECRET_KEY="clave-larga-y-aleatoria-aqui"

# O en .env (cargar con python-dotenv)
SECRET_KEY=clave-larga-y-aleatoria-aqui
```

El valor por defecto (`"demo-gaula-nexo-147"`) es solo para desarrollo local.

---

## Usuarios demo

| Username | Contraseña | Rol | Nombre |
|---|---|---|---|
| `admin` | `Admin147*` | admin | Administrador NEXO-147 |
| `director` | `Director147*` | director | Director GAULA |
| `analista` | `Analista147*` | analista | Analista Operacional |
| `operador` | `Operador147*` | operador | Operador Línea 147 |

Estos usuarios se insertan automáticamente si la tabla `usuarios` está vacía (ver `_seed_db()` en `modules/__init__.py`).
