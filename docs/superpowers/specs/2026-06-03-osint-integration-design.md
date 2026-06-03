# Diseño: Integración del módulo OSINT en DEMO_GAULA

**Fecha:** 2026-06-03  
**Proyecto:** DEMO_GAULA (NEXO-147)  
**Fuente:** PRUEBA_OSINT (módulo independiente en `C:\Users\Victor Pulido\Documents\GIT\PRUEBA_OSINT`)

---

## Objetivo

Integrar todas las funcionalidades del módulo PRUEBA_OSINT dentro de DEMO_GAULA como una única aplicación Flask, exponiendo el módulo completo desde la pestaña "Correlaciones e OSINT" (`panel-inteligencia`) del `console.html`, mediante sub-tabs con carga de resultados vía `fetch()` sin abandonar la consola.

---

## Decisiones clave

| Pregunta | Decisión |
|---|---|
| Arquitectura | Una sola aplicación Flask (sin iframe, sin servicio separado) |
| Acceso desde panel | Sub-tabs dentro del panel con AJAX/fetch — sin recarga de página |
| Base de datos grafo | Tablas `node` y `edge` en el `osint.db` existente (`__bind_key__ = "osint"`) |
| Estrategia de integración | Blueprints registrados con prefijo `/osint/*`, tres adaptaciones mecánicas al código copiado |

---

## Arquitectura general

### Estructura de directorios nueva

```
DEMO_GAULA/
  modules/
    osint/
      __init__.py
      social/
        __init__.py
        routes.py
        scrapers/
          facebook_playwright.py
      opendata/
        __init__.py
        routes.py
      analytics/
        __init__.py
        routes.py
        graph_builder.py
      plugins/
        __init__.py
        base.py
        registry.py
        ejemplo_ip.py
      services/
        __init__.py
        facebook_osint.py
        search_engine.py
        tiktok_osint.py
        x_osint.py
  models/
    osint_graph.py            ← NUEVO
  templates/
    osint/
      social_fragment.html
      opendata_fragment.html
```

### Fuente del código

Todo el código en `modules/osint/` proviene directamente de PRUEBA_OSINT con tres adaptaciones mecánicas descritas abajo. No se escribe lógica nueva en los blueprints.

---

## Capa de datos

### `models/osint_graph.py`

Copia exacta de `app/models.py` de PRUEBA_OSINT (`Node`, `Edge`, `JSONType`, `get_or_create_node`, `create_edge`) con una única adición por modelo:

```python
class Node(db.Model):
    __tablename__ = "node"
    __bind_key__  = "osint"   # escritura en osint.db
    ...

class Edge(db.Model):
    __tablename__ = "edge"
    __bind_key__  = "osint"
    ...
```

El modelo `User` (Flask-Login) de PRUEBA_OSINT **no se copia** — la autenticación usa el sistema de sesión de DEMO_GAULA.

### Creación automática de tablas

`seed_db()` en `app.py` ya llama `db.create_all()`. Solo hay que agregar el import:

```python
from models.osint_graph import Node, Edge  # noqa: F401
```

Esto crea `node` y `edge` en `osint.db` en el primer arranque.

---

## Adaptaciones mecánicas al copiar código de PRUEBA_OSINT

Tres cambios aplicados en **todos** los archivos copiados a `modules/osint/`:

### 1. Autenticación

```python
# ANTES (Flask-Login):
from flask_login import login_required

# DESPUÉS (DEMO_GAULA session-based):
from modules.osint.auth import login_required
```

Se crea `modules/osint/auth.py` con el decorador extraído de `app.py`:

```python
# modules/osint/auth.py
from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper
```

Esto evita importar desde `app.py` (que causaría importación circular) y mantiene el comportamiento idéntico al decorador existente.

### 2. Objeto de base de datos

```python
# ANTES:
from app.extensions import db

# DESPUÉS:
from models import db
```

### 3. Ruta de import del sistema de plugins

En `modules/osint/plugins/registry.py`:

```python
# ANTES:
module_path = f"app.plugins.{module_info.name}"

# DESPUÉS:
module_path = f"modules.osint.plugins.{module_info.name}"
```

---

## Registro de blueprints en `app.py`

Agregar en `app.py` (después de las importaciones existentes de models):

```python
# ── Módulo OSINT integrado ────────────────────────────────────────────────────
from modules.osint.social    import social_osint_bp
from modules.osint.opendata  import opendata_osint_bp
from modules.osint.analytics import analytics_osint_bp

nexo.register_blueprint(social_osint_bp,    url_prefix="/osint/social")
nexo.register_blueprint(opendata_osint_bp,  url_prefix="/osint/opendata")
nexo.register_blueprint(analytics_osint_bp, url_prefix="/osint/analytics")
```

Agregar también el llamado al autodescubrimiento de plugins en `seed_db()`:

```python
with nexo.app_context():
    from modules.osint.plugins.registry import discover_plugins
    discover_plugins()
```

---

## Templates de fragmentos

Los tres templates en `templates/osint/` son las plantillas de PRUEBA_OSINT con los siguientes cambios:

- Eliminar `{% extends "base.html" %}` y los bloques `{% block content %}...{% endblock %}`
- El HTML resultante es un fragmento puro que se inyecta en el `innerHTML` del área de resultados del panel
- Las clases CSS se adaptan a las existentes en `styles_pc.css` de DEMO_GAULA donde sea necesario (tabla, cards, botones)

### `templates/osint/social_fragment.html`
Adaptado de `PRUEBA_OSINT/app/templates/social/results.html`. Muestra: perfil GitHub, posts Reddit, datos Facebook, perfiles X/TikTok, errores.

### `templates/osint/opendata_fragment.html`
Adaptado de `PRUEBA_OSINT/app/templates/opendata/results.html`. Muestra: geolocalización IP, datos RDAP, certificados crt.sh.

### Grafo de Relaciones — sin template propio
El grafo se renderiza directamente en `console.html` via JavaScript. La ruta `/osint/analytics/graph` retorna JSON; Cytoscape.js lo consume inline. La ruta `/view` de PRUEBA_OSINT (que renderizaba una página completa con `analytics/graph.html`) **no se registra ni se necesita**.

---

## UI: panel-inteligencia en console.html

### Cambios en `console.html`

1. **Agregar Cytoscape.js en `<head>`:**
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
```

2. **Reemplazar el contenido de `<section id="panel-inteligencia">`** (líneas 685–742 actuales) con el nuevo layout de sub-tabs.

### Layout del panel

```
panel-inteligencia
├── Header: "Correlaciones de Redes Extorsivas y OSINT"
├── Sub-tabs: [Redes Sociales] [Datos Abiertos] [Grafo de Relaciones]
│
├── Tab 1 — Redes Sociales (activo por defecto)
│   ├── Input: objetivo (usuario / alias)
│   ├── Selector fuente:
│   │     Extracción directa: GitHub / Reddit / GitHub+Reddit
│   │     Dorking DDG: Facebook / X / TikTok / Profunda (FB+X+TikTok)
│   │     Combinado paralelo: Todas las fuentes
│   ├── Botón "EJECUTAR"
│   └── div#osint-social-results (fragmento inyectado via fetch)
│
├── Tab 2 — Datos Abiertos
│   ├── Input: IP o dominio
│   ├── Selector fuente: Geoloc. IP / Dominio RDAP+Certs
│   ├── Botón "EJECUTAR"
│   └── div#osint-opendata-results (fragmento inyectado via fetch)
│
└── Tab 3 — Grafo de Relaciones
    ├── Input: objetivo (filtro BFS del subgrafo)
    ├── Botón "CARGAR GRAFO"
    └── div#osint-graph-canvas (Cytoscape.js, 400px altura)
```

### Flujo fetch — Redes Sociales y Datos Abiertos

```
usuario presiona EJECUTAR
  → fetch(`/osint/social/lookup?q=${objetivo}&source=${fuente}`)
  → response.text()
  → document.getElementById("osint-social-results").innerHTML = html
```

Las rutas de los blueprints retornan `render_template("osint/social_fragment.html", ...)` en lugar de la página completa. El fragmento ya incluye manejo de errores (`{% if errors %}`) de PRUEBA_OSINT.

### Flujo fetch — Grafo

```
usuario presiona CARGAR GRAFO
  → fetch(`/osint/analytics/graph?q=${objetivo}`)
  → response.json()
  → Cytoscape({ container: document.getElementById("osint-graph-canvas"),
                elements: convertir_node_link_a_cytoscape(data) })
```

La ruta `/osint/analytics/graph` retorna JSON en formato `node_link_data` (sin cambios). La conversión al formato de elementos Cytoscape (`{data:{id,label,...}}`) se hace en JavaScript en el panel.

---

## Control de acceso

Sin cambios. El nav-item "Correlaciones e OSINT" en `console.html` ya está restringido a `["admin", "analista", "director"]` con Jinja2. Las rutas `/osint/*` usan el `@login_required` de DEMO_GAULA que verifica `session["user"]`.

---

## Dependencias (`requirements.txt`)

Agregar:

```
networkx
duckduckgo-search
playwright
```

`flask-login` se instala como dependencia transitiva de playwright; no es necesario declararlo directamente ya que la auth se delega al sistema de DEMO_GAULA.

### Degradación suave (preservada de PRUEBA_OSINT)

| Dependencia | Ausente → comportamiento |
|---|---|
| `duckduckgo-search` | X, TikTok, Facebook dorking: error en fragmento. GitHub/Reddit funcionan. |
| `playwright` | Facebook scraping: error parcial, no colapsa búsqueda paralela. |
| `networkx` | Grafo en memoria (fallback): retorna elementos vacíos con mensaje de error. |

---

## Manejo de errores en el panel

- `fetch` falla (red, 500, timeout): el área de resultados muestra un mensaje de error inline con clase CSS de error de la consola. No colapsa el panel ni la consola.
- Los fragmentos HTML incluyen los bloques `{% if errors %}` de PRUEBA_OSINT — se preservan sin cambios.
- El canvas Cytoscape muestra estado vacío si `/osint/analytics/graph` retorna `{ nodes: [], links: [] }`.

---

## Tests

No se agregan tests nuevos. El código de PRUEBA_OSINT está probado de forma independiente. Los tests existentes en `DEMO_GAULA/tests/` no se modifican.

---

## Fuera de alcance

- Unificación de los datos de `osint.db` (FuenteOsint, ConsultaOsint) con los nuevos Node/Edge — son esquemas independientes que coexisten en el mismo archivo SQLite.
- Migración de datos existentes de PRUEBA_OSINT hacia DEMO_GAULA.
- Auth de Facebook (Playwright) en entornos de producción — requiere configuración separada de credenciales `.env`.
