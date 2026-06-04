---
name: blueprints-refactor-design
description: Reestructuración de NEXO-147 usando Flask Blueprints por dominio de negocio, Application Factory y optimización de bases de datos SQLite
metadata:
  type: project
---

# Diseño: Reestructuración con Flask Blueprints — NEXO-147

**Fecha:** 2026-06-03  
**Estado:** Aprobado  
**Objetivo:** Refactorizar el monolítico `app.py` (792 líneas) en blueprints organizados por dominio de negocio, adoptando Application Factory y optimizando las consultas a las 3 bases de datos SQLite locales.

---

## 1. Contexto y Problema

### Estado Actual
- `app.py` tiene 792 líneas / 36 KB con 18 rutas mezcladas: autenticación, dashboard, APIs de casos, inteligencia, OSINT y ETL en un solo archivo.
- Solo el módulo OSINT (`modules/osint/`) usa blueprints correctamente.
- Los modelos están bien separados en `models/` — no se tocan.
- Hay 3 bases de datos SQLite sin optimizaciones de engine configuradas.

### Problema
A medida que el proyecto crece, trabajar sobre `app.py` se vuelve complejo: cualquier cambio en un módulo requiere navegar todo el archivo, los imports circulares son un riesgo latente, y los tests no pueden instanciar la app de forma aislada sin cargar toda la configuración global.

---

## 2. Decisiones de Diseño

| Decisión | Elección | Razón |
|----------|----------|-------|
| Organización de blueprints | Por dominio de negocio | Refleja la estructura real del sistema (auth, casos, inteligencia, dashboard) |
| Código compartido (decoradores) | Módulo `auth/` centralizado | Los decoradores y las rutas de auth son el mismo dominio |
| Pattern de arranque | Application Factory (`create_app()`) | Permite instancias aisladas para tests, configuración por entorno |
| Ubicación de blueprints | Dentro de `modules/` | OSINT ya vive ahí; unifica el lugar para todos los blueprints |

---

## 3. Arquitectura Target

### Estructura de Directorios

```
DEMO_GAULA/
├── app.py                          ← 2 líneas: from modules import create_app; app = create_app()
├── requirements.txt                ← sin cambios
├── modules/
│   ├── __init__.py                 ← create_app() + _register_blueprints()
│   ├── extensions.py               ← db = SQLAlchemy() + pragmas SQLite
│   ├── config.py                   ← Config class con engine options optimizadas
│   ├── auth/
│   │   ├── __init__.py             ← auth_bp = Blueprint("auth", __name__)
│   │   ├── routes.py               ← /, /login, /logout
│   │   └── decorators.py           ← @login_required, @admin_required, @director_required,
│   │                                   @analista_required, @operador_required
│   ├── casos/
│   │   ├── __init__.py             ← casos_bp = Blueprint("casos", __name__)
│   │   └── routes.py               ← /registrar-reporte, /api/casos, /api/casos/<id>/estado
│   ├── inteligencia/
│   │   ├── __init__.py             ← intel_bp = Blueprint("intel", __name__)
│   │   └── routes.py               ← /api/entidades, /api/inteligencia/relaciones, /api/intel/entidades,
│   │                                   /api/intel/hallazgos, /api/intel/grafo, /api/etl/status
│   ├── dashboard/
│   │   ├── __init__.py             ← dashboard_bp = Blueprint("dashboard", __name__)
│   │   └── routes.py               ← /dashboard, /api/brechas, /api/osint/brechas,
│   │                                   /api/osint/indicadores, /api_externa, /health
│   └── osint/                      ← SIN CAMBIOS (ya tiene blueprints correctos)
│       ├── social/
│       ├── opendata/
│       ├── analytics/
│       ├── services/
│       └── plugins/
├── models/                         ← SIN CAMBIOS
│   ├── __init__.py
│   ├── nexo147.py
│   ├── intel.py
│   ├── osint.py
│   └── osint_graph.py
├── templates/
│   ├── base.html                   ← sin cambios
│   ├── footer.html                 ← sin cambios
│   ├── auth/
│   │   └── login.html              ← movido desde templates/login.html
│   ├── casos/
│   │   ├── console.html            ← movido desde templates/console.html
│   │   └── index.html              ← movido desde templates/index.html
│   ├── dashboard/
│   │   ├── dashboard.html          ← movido desde templates/dashboard.html
│   │   └── brechas_seguridad.html  ← movido desde templates/brechas_seguridad.html
│   └── osint/                      ← sin cambios
│       ├── social_fragment.html
│       └── opendata_fragment.html
├── static/                         ← SIN CAMBIOS
├── tests/
│   ├── conftest.py                 ← 1 línea cambia: import desde modules
│   └── test_*.py (5 archivos)     ← sin cambios internos
├── scripts/                        ← sin cambios
└── data/                           ← sin cambios (archivos .db generados en runtime)
```

---

## 4. Componentes Clave

### 4.1 Application Factory (`modules/__init__.py`)

```python
from flask import Flask
from modules.config import Config
from modules.extensions import db

def create_app(config=None):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config or Config)
    db.init_app(app)
    _register_blueprints(app)
    with app.app_context():
        db.create_all(bind_key=None)
        db.create_all(bind_key="intel")
        db.create_all(bind_key="osint")
        _seed_db()
    return app

def _register_blueprints(app):
    from modules.auth           import auth_bp
    from modules.casos          import casos_bp
    from modules.inteligencia   import intel_bp
    from modules.dashboard      import dashboard_bp
    from modules.osint.social    import social_osint_bp
    from modules.osint.opendata  import opendata_osint_bp
    from modules.osint.analytics import analytics_osint_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(casos_bp)
    app.register_blueprint(intel_bp)      # sin url_prefix: rutas con paths mixtos (/api/intel/*, /api/entidades, /api/etl/status)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(social_osint_bp,    url_prefix="/osint/social")
    app.register_blueprint(opendata_osint_bp,  url_prefix="/osint/opendata")
    app.register_blueprint(analytics_osint_bp, url_prefix="/osint/analytics")
```

### 4.2 Extensions (`modules/extensions.py`)

```python
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

db = SQLAlchemy()

@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")      # lecturas concurrentes sin bloquear escrituras
        cur.execute("PRAGMA synchronous=NORMAL")    # balance seguridad/velocidad
        cur.execute("PRAGMA cache_size=10000")      # ~10 MB de cache en memoria por DB
        cur.execute("PRAGMA foreign_keys=ON")       # integridad referencial activa
        cur.close()
```

### 4.3 Configuración (`modules/config.py`)

```python
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "nexo147-dev-key")
    SQLALCHEMY_DATABASE_URI = "sqlite:///data/nexo147.db"
    SQLALCHEMY_BINDS = {
        "intel": "sqlite:///data/intel.db",
        "osint": "sqlite:///data/osint.db",
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
```

### 4.4 Decoradores (`modules/auth/decorators.py`)

Los 5 decoradores de control de acceso se mueven de `app.py` a este módulo. Todos los blueprints que necesiten proteger rutas importan desde aquí:

```python
from modules.auth.decorators import login_required, director_required
```

### 4.5 Modelos — sin cambios, solo ajuste de import

Los modelos actualmente importan `db` desde `models/__init__.py`. El único cambio: `models/__init__.py` pasa a importar `db` desde `modules.extensions` en lugar de crearlo localmente.

```python
# models/__init__.py — único cambio
from modules.extensions import db  # antes: db = SQLAlchemy()
```

---

## 5. Rutas Preservadas (Compatibilidad Total de URLs)

Todas las rutas existentes mantienen exactamente las mismas URLs — no hay cambios de API:

| URL | Blueprint | Método |
|-----|-----------|--------|
| `/` | auth | GET |
| `/login` | auth | GET, POST |
| `/logout` | auth | GET |
| `/registrar-reporte` | casos | POST |
| `/api/casos` | casos | GET |
| `/api/casos/<id>/estado` | casos | POST |
| `/dashboard` | dashboard | GET |
| `/api/brechas` | dashboard | GET |
| `/api/osint/brechas` | dashboard | GET |
| `/api/osint/indicadores` | dashboard | GET |
| `/api_externa` | dashboard | GET, POST |
| `/health` | dashboard | GET |
| `/api/entidades` | inteligencia | GET |
| `/api/inteligencia/relaciones` | inteligencia | GET |
| `/api/intel/entidades` | inteligencia | GET |
| `/api/intel/hallazgos` | inteligencia | GET |
| `/api/intel/grafo` | inteligencia | GET |
| `/api/etl/status` | inteligencia | GET |
| `/osint/social/*` | osint.social | varios |
| `/osint/opendata/*` | osint.opendata | varios |
| `/osint/analytics/*` | osint.analytics | varios |

---

## 6. Optimizaciones de Base de Datos SQLite

### Por qué importan en este proyecto

Las 3 BDs reciben lecturas frecuentes (APIs JSON en cada request del dashboard) y escrituras ocasionales (registro de reportes nuevos). Sin optimizaciones, SQLite serializa todas las operaciones con un lock global.

### Optimizaciones aplicadas

| Pragma / Opción | Valor | Efecto |
|-----------------|-------|--------|
| `journal_mode` | WAL | Permite lecturas concurrentes mientras hay una escritura activa |
| `synchronous` | NORMAL | Reduce fsync; suficientemente seguro para datos de demostración |
| `cache_size` | 10000 páginas | ~10 MB de páginas en RAM por DB; reduce I/O en tablas frecuentes |
| `foreign_keys` | ON | Activa validación de integridad referencial (SQLite la desactiva por defecto) |
| `pool_pre_ping` | True | Verifica conexión viva antes de cada uso; evita errores silenciosos |
| `pool_recycle` | 1800s | Cierra y reabre conexiones idle cada 30 min; previene conexiones zombis |
| `check_same_thread` | False | Necesario para Flask que usa threads por request con SQLite |

---

## 7. Impacto en Tests

**`tests/conftest.py`** — único cambio:

```python
# Línea que cambia:
from modules import create_app   # antes era implícito desde app global

@pytest.fixture
def app():
    app = create_app(TestConfig)  # usa :memory: para las 3 DBs
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    return app.test_client()
```

Los 5 archivos de test (`test_nexo147_models.py`, `test_intel_models.py`, `test_osint_models.py`, `test_osint_api.py`, `test_migration.py`) no requieren cambios internos.

---

## 8. Resumen de Cambios

| Categoría | Archivos | Acción |
|-----------|----------|--------|
| Crear | `modules/__init__.py`, `modules/extensions.py`, `modules/config.py` | Nuevos |
| Crear | `modules/auth/__init__.py`, `routes.py`, `decorators.py` | Nuevos |
| Crear | `modules/casos/__init__.py`, `routes.py` | Nuevos |
| Crear | `modules/inteligencia/__init__.py`, `routes.py` | Nuevos |
| Crear | `modules/dashboard/__init__.py`, `routes.py` | Nuevos |
| Modificar | `app.py` | Reducir a 2 líneas |
| Modificar | `models/__init__.py` | Cambiar origen de `db` |
| Modificar | `tests/conftest.py` | Actualizar import y fixture |
| Mover | 4 templates | A subcarpetas por blueprint |
| Sin cambios | `modules/osint/`, `models/*.py`, `static/`, 5 test files | Intactos |

**Resultado final:** `app.py` pasa de 792 líneas a 2. Cada módulo queda acotado a su dominio, con una responsabilidad clara y menos de 300 líneas.
