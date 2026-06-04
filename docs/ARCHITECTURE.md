# Arquitectura — NEXO-147

## Visión general

La aplicación sigue el patrón **Application Factory** de Flask combinado con **Domain-Driven Blueprints**. Cada dominio funcional es un Blueprint independiente con sus propias rutas, y toda la inicialización pasa por `create_app()`.

```
app.py  (4 líneas — punto de entrada)
  └── modules/__init__.py::create_app()
        ├── Configuración (Config / TestConfig)
        ├── SQLAlchemy + pragmas WAL
        ├── Registro de 7 Blueprints
        ├── Creación de tablas (db.create_all)
        ├── Seed de usuarios y unidades GAULA
        └── Descubrimiento de plugins OSINT
```

---

## Estructura de directorios

```
DEMO_GAULA/
├── app.py                          # Punto de entrada
├── requirements.txt
├── .gitignore
│
├── modules/                        # Núcleo de la aplicación
│   ├── __init__.py                 # Application Factory: create_app()
│   ├── config.py                   # Config y TestConfig
│   ├── extensions.py               # Instancia db + pragmas SQLite
│   │
│   ├── auth/                       # Autenticación
│   │   ├── __init__.py             # Blueprint: auth_bp
│   │   ├── routes.py               # /login, /logout, /
│   │   └── decorators.py           # @login_required, @admin_required, etc.
│   │
│   ├── casos/                      # Gestión de casos
│   │   ├── __init__.py             # Blueprint: casos_bp
│   │   └── routes.py               # /registrar-reporte, /api/casos, /api/casos/<id>/estado
│   │
│   ├── dashboard/                  # Dashboard operacional
│   │   ├── __init__.py             # Blueprint: dashboard_bp
│   │   └── routes.py               # /dashboard, /health, /api/brechas, etc.
│   │
│   ├── inteligencia/               # Análisis de inteligencia
│   │   ├── __init__.py             # Blueprint: intel_bp
│   │   └── routes.py               # /api/intel/*, /api/etl/status
│   │
│   └── osint/                      # Inteligencia de fuentes abiertas
│       ├── auth.py                 # Decorador de auth para OSINT
│       ├── social/                 # Blueprint: social_osint_bp (/osint/social)
│       ├── opendata/               # Blueprint: opendata_osint_bp (/osint/opendata)
│       ├── analytics/              # Blueprint: analytics_osint_bp (/osint/analytics)
│       ├── plugins/                # Sistema de plugins extensible
│       └── services/               # Implementaciones de scraping
│
├── models/                         # Modelos SQLAlchemy
│   ├── __init__.py
│   ├── nexo147.py                  # Modelos core (casos, usuarios, reportantes...)
│   ├── intel.py                    # Modelos de inteligencia
│   ├── osint.py                    # Modelos OSINT (consultas, resultados, caché)
│   └── osint_graph.py              # Modelos de grafo para visualización
│
├── templates/                      # Plantillas Jinja2
│   ├── base.html
│   ├── footer.html
│   ├── auth/login.html
│   ├── casos/console.html
│   ├── casos/index.html
│   ├── dashboard/dashboard.html
│   ├── dashboard/brechas_seguridad.html
│   └── osint/
│       ├── social_fragment.html
│       └── opendata_fragment.html
│
├── static/                         # Assets estáticos
│   ├── styles_pc.css
│   ├── styles_media.css
│   ├── scripts.js
│   ├── console.js
│   ├── tablas.js
│   ├── js/dashboard.js
│   └── assets/logo.png
│
├── data/                           # Bases de datos SQLite (generadas en runtime)
│   ├── nexo147.db
│   ├── intel.db
│   └── osint.db
│
├── tests/                          # Suite de pruebas pytest
│   ├── conftest.py
│   ├── test_nexo147_models.py
│   ├── test_intel_models.py
│   ├── test_osint_models.py
│   ├── test_osint_api.py
│   └── test_migration.py
│
└── docs/                           # Documentación
```

---

## Blueprints registrados

| Blueprint | Prefijo URL | Archivo | Responsabilidad |
|---|---|---|---|
| `auth_bp` | `/` | `modules/auth/` | Login, logout, redirección por rol |
| `casos_bp` | `/` | `modules/casos/` | Registro y consulta de casos |
| `dashboard_bp` | `/` | `modules/dashboard/` | Dashboard director/admin |
| `intel_bp` | `/` | `modules/inteligencia/` | APIs de inteligencia y grafo |
| `social_osint_bp` | `/osint/social` | `modules/osint/social/` | Scraping redes sociales |
| `opendata_osint_bp` | `/osint/opendata` | `modules/osint/opendata/` | IP, dominios, certificados |
| `analytics_osint_bp` | `/osint/analytics` | `modules/osint/analytics/` | Construcción de grafos OSINT |

---

## Bases de datos múltiples

El sistema usa tres bases de datos SQLite con binds de SQLAlchemy:

| Bind | Archivo | Contenido |
|---|---|---|
| `(default)` | `data/nexo147.db` | Casos, usuarios, reportantes, evidencias, unidades GAULA |
| `"intel"` | `data/intel.db` | Personas, entidades, relaciones, grafo de inteligencia |
| `"osint"` | `data/osint.db` | Fuentes OSINT, consultas, resultados, indicadores de riesgo |

Los modelos declaran su bind con `__bind_key__`:
```python
class Persona(db.Model):
    __bind_key__ = "intel"
    __tablename__ = "personas"
```

Los modelos sin `__bind_key__` van a la base de datos principal (`nexo147.db`).

---

## Flujo de una solicitud HTTP

```
Browser/API Client
      │
      ▼
  Flask app (app.py)
      │
      ▼
  Blueprint Router (URL matching)
      │
      ├── auth_bp → modules/auth/routes.py
      ├── casos_bp → modules/casos/routes.py
      ├── dashboard_bp → modules/dashboard/routes.py
      ├── intel_bp → modules/inteligencia/routes.py
      └── *_osint_bp → modules/osint/*/routes.py
              │
              ▼
      Decoradores de rol (@login_required, @admin_required...)
              │
              ▼
      Lógica de negocio + consultas SQLAlchemy
              │
              ▼
      SQLite (nexo147.db / intel.db / osint.db)
              │
              ▼
      JSON response o render_template(Jinja2)
              │
              ▼
      Browser (HTML + CSS + JS)
```

---

## Application Factory

```python
# modules/__init__.py
def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_class)

    db.init_app(app)
    _apply_sqlite_pragmas(app)          # WAL, sync=NORMAL, cache, FK
    _register_blueprints(app)           # Los 7 blueprints
    _create_tables_and_seed(app)        # db.create_all() + seed

    @app.after_request
    def no_cache(response):             # Cache-control headers
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response

    return app
```

---

## Pragmas SQLite

Configurados en `modules/extensions.py` vía el evento `connect` de SQLAlchemy:

| Pragma | Valor | Propósito |
|---|---|---|
| `journal_mode` | `WAL` | Escrituras concurrentes sin bloquear lecturas |
| `synchronous` | `NORMAL` | Balance entre rendimiento y durabilidad |
| `cache_size` | `10000` | 10K páginas en caché de memoria |
| `foreign_keys` | `ON` | Integridad referencial activada |
