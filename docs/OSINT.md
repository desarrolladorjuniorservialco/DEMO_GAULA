# Módulo OSINT — NEXO-147

El módulo OSINT (Open Source Intelligence) permite a analistas consultar fuentes públicas de información para correlacionar datos con los casos registrados en el sistema.

---

## Arquitectura del módulo

```
modules/osint/
├── auth.py                  # Decorador @osint_login_required
├── social/                  # Scraping de redes sociales
│   ├── __init__.py          # Blueprint: social_osint_bp (prefijo /osint/social)
│   ├── routes.py            # Endpoints de consulta social
│   └── scrapers/
│       ├── __init__.py
│       └── facebook_playwright.py  # Scraper de Facebook con Playwright
├── opendata/                # Datos públicos (IP, dominios, certificados)
│   ├── __init__.py          # Blueprint: opendata_osint_bp (prefijo /osint/opendata)
│   └── routes.py
├── analytics/               # Construcción de grafos
│   ├── __init__.py          # Blueprint: analytics_osint_bp (prefijo /osint/analytics)
│   ├── routes.py
│   └── graph_builder.py
├── plugins/                 # Sistema de plugins extensible
│   ├── __init__.py
│   ├── base.py              # BaseOsintPlugin (clase abstracta)
│   ├── registry.py          # Auto-descubrimiento de plugins
│   └── ejemplo_ip.py        # Plugin de ejemplo: IpGeoPlugin
└── services/                # Implementaciones de servicios
    ├── __init__.py
    ├── search_engine.py     # Motor de búsqueda universal (dorks)
    ├── x_osint.py           # Servicio X/Twitter
    ├── tiktok_osint.py      # Servicio TikTok
    └── facebook_osint.py    # Servicio Facebook
```

---

## Blueprints OSINT

| Blueprint | Prefijo | Blueprints registrados en |
|---|---|---|
| `social_osint_bp` | `/osint/social` | `modules/__init__.py` |
| `opendata_osint_bp` | `/osint/opendata` | `modules/__init__.py` |
| `analytics_osint_bp` | `/osint/analytics` | `modules/__init__.py` |

---

## Fuentes de datos

### Redes sociales (`/osint/social`)

| Fuente | Endpoint | Método | Descripción |
|---|---|---|---|
| GitHub | `/osint/social/github/<username>` | GET | Perfil, repos, organizaciones |
| Reddit | `/osint/social/reddit/<username>` | GET | Perfil, posts, karma |
| X/Twitter | `/osint/social/x/<username>` | GET | Descubrimiento de cuenta |
| TikTok | `/osint/social/tiktok/<username>` | GET | Perfil público |
| Facebook | `/osint/social/facebook` | POST | Scraping con Playwright |

### Open Data (`/osint/opendata`)

| Fuente | Endpoint | API externa | Descripción |
|---|---|---|---|
| IP Geolocation | `/osint/opendata/ip/<ip>` | ip-api.com | País, ciudad, ASN, coordenadas |
| RDAP Dominio | `/osint/opendata/domain/<domain>` | rdap.org | Registrador, fechas, nameservers |
| Cert Transparency | `/osint/opendata/certs/<domain>` | crt.sh | Certificados SSL históricos |

### Analytics (`/osint/analytics`)

| Endpoint | Descripción |
|---|---|
| `POST /osint/analytics/grafo` | Construye grafo desde resultados OSINT |

---

## Sistema de plugins

El módulo OSINT implementa un sistema de plugins auto-descubribles para facilitar la extensión sin modificar el núcleo.

### Clase base

```python
# modules/osint/plugins/base.py
from abc import ABC, abstractmethod

class BaseOsintPlugin(ABC):
    name: str           # Nombre único del plugin
    description: str    # Descripción
    source_type: str    # api | scraper | search

    @abstractmethod
    def query(self, value: str, **kwargs) -> dict:
        """Ejecuta la consulta OSINT."""
        ...

    @abstractmethod
    def get_result_schema(self) -> dict:
        """Retorna el esquema JSON de los resultados."""
        ...
```

### Registro automático

```python
# modules/osint/plugins/registry.py
class OsintPluginRegistry:
    _plugins: dict[str, BaseOsintPlugin] = {}

    @classmethod
    def register(cls, plugin_class):
        instance = plugin_class()
        cls._plugins[instance.name] = instance

    @classmethod
    def get(cls, name) -> BaseOsintPlugin:
        return cls._plugins.get(name)

    @classmethod
    def all(cls) -> list:
        return list(cls._plugins.values())
```

El registro se ejecuta en `create_app()` al arrancar la aplicación.

### Crear un plugin nuevo

```python
# modules/osint/plugins/mi_plugin.py
from .base import BaseOsintPlugin
from .registry import OsintPluginRegistry

class MiNuevoPlugin(BaseOsintPlugin):
    name = "mi_plugin"
    description = "Consulta mi fuente de datos"
    source_type = "api"

    def query(self, value: str, **kwargs) -> dict:
        # Implementar lógica de consulta
        response = requests.get(f"https://mi-api.com/buscar/{value}")
        return response.json()

    def get_result_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "resultado": {"type": "string"}
            }
        }

# Auto-registro
OsintPluginRegistry.register(MiNuevoPlugin)
```

### Plugin de ejemplo: `IpGeoPlugin`

```python
# modules/osint/plugins/ejemplo_ip.py
class IpGeoPlugin(BaseOsintPlugin):
    name = "ip_geo"
    description = "Geolocalización de IP via ip-api.com"
    source_type = "api"

    def query(self, value: str, **kwargs) -> dict:
        r = requests.get(f"http://ip-api.com/json/{value}")
        return r.json()
```

---

## Servicios

### Motor de búsqueda universal (`search_engine.py`)

Ejecuta búsquedas con operadores avanzados (dorks) usando DuckDuckGo Search.

```python
from modules.osint.services.search_engine import SearchEngine

engine = SearchEngine()
results = engine.search('site:github.com "username"', max_results=10)
```

### Scraper de Facebook (`facebook_playwright.py`)

Usa Playwright para navegar perfiles de Facebook. Requiere `playwright install chromium`.

```python
# Ejemplo de uso interno
from modules.osint.social.scrapers.facebook_playwright import scrape_facebook_profile

data = await scrape_facebook_profile("https://facebook.com/ejemplo")
```

> **Nota:** El scraping de Facebook puede requerir autenticación y está sujeto a los términos de servicio de la plataforma.

---

## Base de datos OSINT

Ver [DATABASE.md](DATABASE.md) para el esquema completo. El flujo de datos es:

```
FuenteOsint → ConsultaOsint → CacheConsulta (TTL)
                           └─→ ResultadoOsint (N)

ResultadoOsint → IndicadorRiesgo (si se detecta riesgo)
ResultadoOsint → Node / OsintEdge (para grafos)
```

### Caché de consultas

Las consultas se cachean en `cache_consultas` con un hash SHA-256 de los parámetros. Esto evita solicitudes repetidas a APIs externas y respeta los rate limits.

```python
hash_clave = hashlib.sha256(
    f"{tipo_consulta}:{valor_consultado}:{fuente_id}".encode()
).hexdigest()
```

---

## Integración con el dashboard

Los indicadores de riesgo OSINT aparecen en el dashboard del director via:

```
GET /api/osint/indicadores  →  IndicadorRiesgo activos
GET /api/brechas            →  HaveIBeenPwned consultas
```

---

## Dependencias requeridas

```
requests>=2.32.3
beautifulsoup4>=4.13.4
playwright>=1.60.0          # Solo para scraping Facebook
duckduckgo-search>=6.2.0
networkx>=3.3
```

Para activar Playwright por primera vez:
```bash
playwright install chromium
```

---

## Consideraciones legales y éticas

- Las consultas OSINT se limitan a fuentes **públicamente accesibles**
- Los datos recopilados se usan exclusivamente en el contexto de investigaciones GAULA autorizadas
- El caché limita el impacto en servicios de terceros (rate limiting)
- No se almacenan credenciales de terceros en el sistema
- Las consultas a Facebook con Playwright deben realizarse con cuentas autorizadas
