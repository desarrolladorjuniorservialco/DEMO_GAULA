# Guía de desarrollo — NEXO-147

---

## Configuración del entorno

```bash
# Clonar y entrar al proyecto
git clone <url> && cd DEMO_GAULA

# Entorno virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS

pip install -r requirements.txt
```

---

## Arrancar en modo desarrollo

```bash
python app.py
# → http://localhost:5000
# → Debug mode activo (recarga automática)
```

---

## Estructura de un blueprint

Cada dominio sigue la misma estructura:

```
modules/<dominio>/
├── __init__.py    # Define y exporta el Blueprint
└── routes.py      # Define las rutas del blueprint
```

### Plantilla de `__init__.py`

```python
from flask import Blueprint

mi_bp = Blueprint("mi_dominio", __name__)

from . import routes  # noqa: F401, E402
```

### Plantilla de `routes.py`

```python
from flask import jsonify, request
from . import mi_bp
from modules.auth.decorators import login_required

@mi_bp.route("/api/mi-endpoint")
@login_required
def mi_endpoint():
    return jsonify({"ok": True, "data": []})
```

### Registrar el blueprint en `modules/__init__.py`

```python
from modules.mi_dominio import mi_bp
app.register_blueprint(mi_bp)
```

---

## Agregar un modelo nuevo

1. Crear o editar el archivo en `models/`
2. Si es una nueva base de datos, declarar `__bind_key__`
3. Importar en `modules/__init__.py` dentro de `_create_tables_and_seed()`

```python
# models/mi_modelo.py
from modules.extensions import db

class MiModelo(db.Model):
    __tablename__ = "mi_tabla"
    # __bind_key__ = "intel"  # si va a intel.db

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
```

---

## Convenciones de código

### Rutas
- Rutas de página: sin prefijo `/api/`
- Rutas de datos: prefijo `/api/`
- Usar `@login_required` en todas las rutas que lo necesiten
- Retornar siempre `{"ok": true/false, ...}` en respuestas JSON

### Modelos
- Campos de auditoría en todos los modelos: `created_at`, `updated_at`, `created_by`, `updated_by`
- PKs siempre autoincrement (`Integer, primary_key=True`)
- UUIDs como strings en campos visibles al usuario (`VARCHAR(36)`)
- No usar FK explícita entre bases de datos distintas

### Seguridad
- Hashear siempre las contraseñas con Werkzeug
- Nunca almacenar texto plano
- Validar el rol antes de cualquier operación sensible
- No exponer IDs internos en la UI si hay UUIDs disponibles

---

## Tests

### Ejecutar los tests

```bash
# Todos los tests
pytest tests/ -v

# Con cobertura
pytest tests/ -v --cov=modules --cov=models --cov-report=term-missing

# Un archivo específico
pytest tests/test_nexo147_models.py -v

# Un test específico
pytest tests/test_nexo147_models.py::test_crear_caso -v
```

### Fixtures disponibles (`tests/conftest.py`)

| Fixture | Scope | Descripción |
|---|---|---|
| `app` | function | App Flask con `TestConfig` (DBs en memoria) |
| `session` | function | Sesión SQLAlchemy |
| `client` | function | Cliente de tests Flask |

```python
# Ejemplo de test
def test_crear_usuario(session):
    u = Usuario(username="test", nombre="Test", rol="operador")
    u.set_password("Test123*")
    session.add(u)
    session.commit()

    assert u.id is not None
    assert u.check_password("Test123*") is True
```

### Configuración de test (`TestConfig`)

```python
class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_BINDS = {
        "intel": "sqlite:///:memory:",
        "osint": "sqlite:///:memory:",
    }
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,   # Pool estático para tests en memoria
    }
```

### Archivos de tests

| Archivo | Cubre |
|---|---|
| `test_nexo147_models.py` | Usuario, UnidadGaula, Caso, Reportante, Evidencia, EventoCaso, MedioPago |
| `test_intel_models.py` | Persona, Telefono, Ubicacion, IntelNode, IntelEdge |
| `test_osint_models.py` | FuenteOsint, ConsultaOsint, CacheConsulta, IndicadorRiesgo |
| `test_osint_api.py` | Endpoints OSINT vía `client` |
| `test_migration.py` | Compatibilidad de esquema entre versiones |

---

## Flujo de trabajo Git

```bash
# Crear rama para feature
git checkout -b feat/nombre-feature

# Commits atómicos con mensajes descriptivos
git add modules/casos/routes.py
git commit -m "feat: agregar filtro por prioridad en /api/casos"

# Push y PR
git push origin feat/nombre-feature
```

### Convención de commits

```
feat:     nueva funcionalidad
fix:      corrección de bug
refactor: refactorización sin cambio funcional
chore:    tareas de mantenimiento (gitignore, deps, etc.)
test:     agregar o corregir tests
docs:     solo documentación
```

---

## Archivos que NO se versionan (`.gitignore`)

```
*.db             # Bases de datos SQLite
__pycache__/     # Caché de Python
.venv/           # Entorno virtual
*.pyc
.env             # Variables de entorno locales
logs/            # Logs de aplicación
```

---

## Dependencias principales

Ver `requirements.txt` para versiones exactas.

| Paquete | Propósito |
|---|---|
| `flask` | Framework web |
| `flask-sqlalchemy` | ORM |
| `werkzeug` | Password hashing, WSGI |
| `sqlalchemy` | SQL toolkit |
| `gunicorn` | Servidor WSGI producción |
| `pytest` | Framework de testing |
| `requests` | HTTP client |
| `beautifulsoup4` | Parsing HTML |
| `playwright` | Browser automation |
| `duckduckgo-search` | Búsquedas OSINT |
| `networkx` | Análisis de grafos |

---

## Variables de entorno para desarrollo

Crear un archivo `.env` (no versionado):

```env
SECRET_KEY=dev-key-solo-local
FLASK_ENV=development
FLASK_DEBUG=1
```

Cargar con `python-dotenv` si se desea inyección automática, o exportar manualmente:

```bash
# Windows PowerShell
$env:SECRET_KEY = "dev-key"
$env:FLASK_DEBUG = "1"

# Linux/macOS
export SECRET_KEY=dev-key
export FLASK_DEBUG=1
```
