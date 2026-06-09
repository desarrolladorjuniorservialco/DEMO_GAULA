# Módulo OSINT Universal - NEXO-147

Este documento define la arquitectura objetivo del módulo OSINT de NEXO-147. La meta es transformar la implementación actual en un motor universal de inteligencia de fuentes abiertas capaz de descubrir, correlacionar, almacenar, visualizar y monitorear información pública de forma automática.

La interfaz manual basada en selección explícita de plataforma deja de ser el flujo principal. En su lugar, el sistema recibe un objetivo y determina qué fuentes, conectores y estrategias aplicar según el tipo de entidad detectada.

---

## Principios de diseño

La solución debe construirse bajo estos principios:

- Clean Architecture
- SOLID
- Domain Driven Design (DDD)
- CQRS cuando aplique
- Repository Pattern
- Service Layer Pattern
- Plugin Architecture
- Event Driven Architecture
- Async Programming
- Caching multinivel
- Graph Intelligence

El objetivo no es solo recolectar datos, sino producir inteligencia correlacionada con trazabilidad, persistencia y capacidad de expansión sin tocar el núcleo.

---

## Flujo funcional objetivo

```
Usuario autenticado
  -> Ingresa un objetivo
  -> El sistema detecta el tipo de objetivo
  -> Descubre fuentes aplicables
  -> Ejecuta conectores y scrapers en paralelo
  -> Normaliza resultados
  -> Correlaciona identidades
  -> Calcula riesgo
  -> Persiste evidencias y grafo
  -> Renderiza dashboard, historial o vista de grafo
```

La experiencia mínima deseada es una búsqueda unificada:

```text
Buscar objetivo: [ victorpulido ] [ Buscar ]
```

Desde ese único punto de entrada el motor debe decidir qué fuentes consultar.

---

## Estructura objetivo

```text
modules/osint/
├── core/
│   ├── engine.py               # UniversalOsintEngine
│   ├── target_detection.py     # Detección del tipo de objetivo
│   ├── correlation.py          # IdentityCorrelationEngine
│   ├── findings.py             # FindingEngine
│   ├── risk.py                 # Cálculo de riesgo
│   └── schemas.py              # Contratos de datos normalizados
├── engines/
│   ├── dork_engine.py          # Generación inteligente de dorks
│   └── orchestration.py        # Coordinación de tareas y colas
├── scrapers/
│   ├── browser/
│   │   ├── playwright.py       # Scraping con navegador
│   │   └── anti_blocking.py    # Rotación, backoff, rate limiting
│   └── parsers/
│       ├── bs4_parser.py
│       ├── lxml_parser.py
│       └── selectolax_parser.py
├── connectors/
│   ├── base.py                 # BaseConnector
│   ├── github.py
│   ├── gitlab.py
│   ├── bitbucket.py
│   ├── reddit.py
│   ├── facebook.py
│   ├── instagram.py
│   ├── threads.py
│   ├── tiktok.py
│   ├── youtube.py
│   ├── linkedin.py
│   ├── pinterest.py
│   ├── telegram.py
│   ├── discord.py
│   ├── google.py
│   ├── bing.py
│   ├── duckduckgo.py
│   ├── brave.py
│   ├── rdap.py
│   ├── crtsh.py
│   ├── whois.py
│   ├── shodan.py
│   ├── censys.py
│   ├── virustotal.py
│   ├── abuseipdb.py
│   ├── alienvault.py
│   ├── hibp.py
│   └── intelligencex.py
├── analyzers/
│   ├── identity.py             # Similitud y deduplicación semántica
│   ├── risk.py
│   └── enrichment.py
├── graph/
│   ├── builder.py              # Construcción del grafo
│   ├── persistence.py          # Persistencia dual SQLite / Neo4j
│   └── exporters.py            # GraphML, JSON, CSV, PDF, Excel
├── cache/
│   ├── memory.py                # L1
│   ├── redis_cache.py          # L2
│   └── db_cache.py             # L3
├── history/
│   ├── models.py                # ConsultaOsint
│   ├── routes.py                # /osint/history
│   └── repository.py
├── monitoring/
│   ├── watchlists.py            # /osint/watchlists
│   └── jobs.py                  # APScheduler / Celery / RQ
├── exports/
│   ├── pdf.py
│   ├── excel.py
│   ├── csv.py
│   ├── json.py
│   └── graphml.py
├── plugins/
│   ├── base.py
│   ├── registry.py
│   └── examples/
└── routes/
    ├── search.py               # Entrada universal
    ├── dashboard.py            # /osint/dashboard
    ├── history.py              # /osint/history
    ├── watchlists.py           # /osint/watchlists
    └── graph.py                # /osint/graph
```

---

## Compatibilidad con la implementación actual

La versión existente del módulo ya expone piezas útiles como:

- `/osint/social/lookup`
- `/osint/opendata/lookup`
- `/osint/analytics/graph`
- sistema de plugins
- búsqueda por dorking en redes sociales

En la arquitectura objetivo, esos elementos pasan a ser adaptadores o fachadas sobre el motor universal. La compatibilidad con rutas actuales puede mantenerse, pero el flujo principal debe concentrarse en un único motor orquestador.

---

## Detección del tipo de objetivo

El motor debe detectar automáticamente el tipo de entidad antes de ejecutar conectores.

### Tipos de objetivo

- Usuario
- Alias
- Correo electrónico
- Teléfono
- Dominio
- URL
- IP
- Hash
- Empresa
- Organización
- Nombre completo

### Librerías sugeridas

- `re`
- `validators`
- `tldextract`
- `email_validator`
- `phonenumbers`
- `ipaddress`

### Estrategia

1. Normalizar el texto de entrada.
2. Detectar patrones obvios primero.
3. Resolver ambigüedades por prioridad.
4. Inferir tipo de objetivo cuando el patrón no sea concluyente.
5. Registrar la decisión para auditoría y reproducibilidad.

---

## Motor universal

### `UniversalOsintEngine`

Responsabilidades principales:

- `detect_target_type()`
- `discover_sources()`
- `run_collectors()`
- `correlate_results()`
- `calculate_risk()`
- `persist_results()`
- `build_graph()`

### Comportamiento esperado

- Orquestación asíncrona.
- Descubrimiento de fuentes según tipo de objetivo.
- Ejecución paralela con control de concurrencia.
- Fallback progresivo si una fuente falla.
- Persistencia de hallazgos, consultas y relaciones.
- Emisión de eventos para procesos diferidos.

---

## Conectores

### Interfaz base

```python
class BaseConnector:
    async def search(self, target):
        pass

    async def normalize(self, data):
        pass

    async def validate(self, data):
        pass
```

### Contrato normalizado

Toda respuesta debe convertirse a una forma común:

```json
{
  "source": "",
  "entity_type": "",
  "value": "",
  "confidence": 0.0,
  "url": "",
  "metadata": {}
}
```

### Descubrimiento automático

La arquitectura debe descubrir conectores mediante:

- `entry_points`
- `importlib`
- `inspect`

Esto permite agregar nuevas fuentes sin modificar el núcleo.

### Fuentes objetivo

El motor debe ser capaz de consultar, según aplique:

- GitHub
- GitLab
- Bitbucket
- Reddit
- Facebook
- Instagram
- Threads
- TikTok
- YouTube
- LinkedIn
- Pinterest
- Telegram público
- Discord público
- Google
- Bing
- DuckDuckGo
- Brave
- RDAP
- crt.sh
- WHOIS
- Shodan
- Censys
- VirusTotal
- AbuseIPDB
- AlienVault OTX
- Have I Been Pwned
- Intelligence X

---

## Scraping avanzado

El scraping debe ser híbrido:

- APIs oficiales cuando existan.
- Scraping solo cuando no haya una API adecuada.
- Parsers ligeros para contenido web estructurado.

### Herramientas sugeridas

- Playwright para:
  - Facebook
  - Instagram
  - TikTok
  - LinkedIn
  - Threads
- BeautifulSoup, lxml y selectolax para:
  - Foros
  - Blogs
  - Sitios web

### Estrategia anti bloqueo

El módulo debe incluir:

- Rotación de User-Agent
- Rotación de headers
- Backoff exponencial
- Retry automático
- Pool de sesiones
- Control de concurrencia
- Rate limiting

### Librerías sugeridas

- `fake-useragent`
- `tenacity`
- `aiohttp_retry`

---

## DorkEngine

El motor de dorking debe generar búsquedas automáticas por plataforma y tipo de objetivo.

### Ejemplos de dorks

- `site:github.com "objetivo"`
- `site:reddit.com "objetivo"`
- `site:x.com "objetivo"`
- `site:facebook.com "objetivo"`
- `site:linkedin.com "objetivo"`
- `"objetivo@gmail.com"`
- `inurl:"objetivo"`
- `intitle:"objetivo"`

### Primera capa

Utilizar `duckduckgo-search` como primera capa antes de escalar a otras fuentes.

### Requisitos

- Ejecución paralela.
- Detección de rate limit.
- Trazabilidad del query generado.
- Retorno estructurado por plataforma.

---

## Correlación de identidad

### `IdentityCorrelationEngine`

Debe consolidar evidencias de fuentes distintas mediante:

- Fuzzy Matching
- Alias Matching
- Username Similarity
- Email Similarity
- Phone Similarity
- Organization Similarity

### Librerías sugeridas

- `rapidfuzz`
- `thefuzz`
- `jellyfish`

### Objetivo

Reducir duplicados, unir identidades parciales y construir un perfil coherente de la entidad objetivo.

---

## Grafo de inteligencia

### Modelo

Se debe evaluar una migración desde SQLite hacia Neo4j o mantener compatibilidad dual.

### Entidades

- Person
- Alias
- Email
- Phone
- Organization
- Location
- Domain
- IP
- Repository
- SocialProfile
- URL
- Image
- Document

### Relaciones

- USES
- WORKS_FOR
- OWNS
- REGISTERED
- MENTIONS
- POSTED
- FOLLOWS
- CONNECTED_TO

### Librerías sugeridas

- `py2neo`
- `neo4j-driver`

### Reglas del grafo

- Persistencia idempotente.
- Dedupe por identidad canónica.
- Evidencia asociada a nodos y aristas.
- Carga incremental.
- Exportación a formatos abiertos.

---

## FindingEngine

El sistema de hallazgos debe detectar automáticamente:

- Exposición de correo electrónico
- Presencia en múltiples redes
- Repositorios públicos
- Infraestructura propia
- Posibles filtraciones
- Alias compartidos
- Patrones de identidad

Los hallazgos deben ser explicables y rastreables a los nodos y aristas que los originan.

---

## Riesgo

### Escala

| Rango | Nivel |
|---|---|
| 0-5 | Bajo |
| 6-10 | Medio |
| 11-15 | Alto |
| 16-20 | Crítico |

### Factores de cálculo

- Emails expuestos
- Teléfonos encontrados
- Brechas detectadas
- Infraestructura pública
- Redes sociales encontradas
- Repositorios sensibles

El riesgo debe actualizarse con base en las evidencias acumuladas y no solo por la cantidad de resultados.

---

## Historial de consultas

### `ConsultaOsint`

Campos esperados:

- `id`
- `user_id`
- `target`
- `target_type`
- `timestamp`
- `duration`
- `sources`
- `risk`
- `results_count`

### Ruta

`/osint/history`

### Capacidades

- Buscar consultas
- Filtrar por fecha
- Filtrar por fuente
- Filtrar por riesgo
- Exportar
- Repetir búsqueda
- Ver grafo

---

## Dashboard OSINT

### Ruta

`/osint/dashboard`

### Visualizaciones

- Consultas por día
- Fuentes utilizadas
- Objetivos frecuentes
- Riesgo acumulado
- Top entidades
- Mapa geográfico

### Librerías sugeridas

- Apache ECharts
- Chart.js
- Leaflet

---

## Watchlists

### Ruta

`/osint/watchlists`

### Funciones

- Agregar objetivo
- Configurar frecuencia
- Recibir alertas

### Motor de ejecución

- APScheduler
- Celery
- Redis Queue

Las watchlists deben operar como tareas diferidas, no como procesos bloqueantes dentro de la vista web.

---

## Caché multinivel

### Niveles

- L1 - Memoria
- L2 - Redis
- L3 - Base de datos

### Herramientas

- `redis`
- `cachetools`

### TTL configurable

- 15 minutos
- 1 hora
- 24 horas
- 7 días

El caché debe considerar:

- objetivo normalizado
- tipo de consulta
- fuente
- usuario
- timestamp de expiración

---

## Exportación

### Formatos

- PDF
- Excel
- CSV
- JSON
- GraphML

### Librerías

- `pandas`
- `openpyxl`
- `reportlab`
- `networkx`

Las exportaciones deben incluir evidencias, marcas de tiempo y metadatos de la consulta original.

---

## Seguridad

El módulo debe incluir controles de seguridad de nivel plataforma:

- Auditoría completa
- Registro de consultas
- RBAC
- Control de permisos
- Rate limiting
- Protección CSRF
- Protección XSS
- Protección SSRF
- Protección contra path traversal

### Librerías sugeridas

- `Flask-Limiter`
- `Flask-Talisman`
- `Bleach`

---

## Rendimiento

### Optimización

- Búsquedas asíncronas
- Task batching
- Connection pooling
- Response compression
- Lazy loading
- Incremental graph loading
- Redis cache
- Background processing

### Objetivos de servicio

- Tiempo de respuesta inicial menor a 3 segundos
- Consulta completa menor a 15 segundos
- Hasta 50 fuentes simultáneas
- Hasta 10.000 nodos en grafo

---

## Sistema de plugins

El sistema de plugins debe permitir la incorporación de nuevas fuentes sin modificar el núcleo.

### Requisitos

- Autodescubrimiento de plugins.
- Categorías flexibles.
- Posibilidad de requerir API keys.
- Ejecución aislada por plugin.
- Resultados normalizados.

### Interfaz esperada

```python
class BaseOsintPlugin(ABC):
    @property
    def name(self) -> str:
        ...

    @property
    def category(self) -> str:
        ...

    @property
    def needs_api_key(self) -> bool:
        ...

    def ejecutar(self, objetivo: str) -> dict:
        ...
```

---

## API y rutas objetivo

### Búsqueda universal

`GET /osint/search?q=<objetivo>`

### Compatibilidad con vistas específicas

- `GET /osint/social/lookup`
- `GET /osint/opendata/lookup`
- `GET /osint/graph`
- `GET /osint/history`
- `GET /osint/dashboard`
- `GET /osint/watchlists`

Las rutas actuales deben seguir funcionando como capa de compatibilidad, pero delegando en el motor universal.

---

## Formato de resultados

La respuesta consolidada debe devolver al menos:

```json
{
  "target": "",
  "target_type": "",
  "sources_used": [],
  "results": [],
  "findings": [],
  "risk": {
    "score": 0,
    "level": ""
  },
  "graph": {
    "nodes": [],
    "edges": []
  },
  "stats": {
    "duration_ms": 0,
    "results_count": 0,
    "sources_count": 0
  }
}
```

---

## Arquitectura de eventos

Para evitar bloquear la interfaz durante búsquedas extensas, el módulo debe emitir eventos para:

- inicio de consulta
- fuente iniciada
- fuente finalizada
- hallazgo generado
- grafo persistido
- exportación generada
- alerta disparada

Estos eventos pueden alimentar:

- colas de trabajo
- métricas
- auditoría
- watchlists

---

## Estado de migración recomendado

### Fase 1

- Crear `UniversalOsintEngine`.
- Definir `BaseConnector`.
- Normalizar formato de resultados.
- Mantener compatibilidad con las rutas existentes.

### Fase 2

- Introducir correlación de identidad.
- Añadir historial de consultas.
- Implementar caché multinivel.
- Exportación básica.

### Fase 3

- Integrar watchlists.
- Añadir dashboard.
- Habilitar búsqueda universal completa.
- Migrar o dualizar el grafo hacia Neo4j.

### Fase 4

- Consolidar plugins.
- Expandir conectores.
- Optimizar rendimiento y observabilidad.

---

## Resultado esperado

Al finalizar la migración, NEXO-147 debe contar con:

- Motor universal de búsqueda OSINT
- Descubrimiento automático de fuentes
- Scraping distribuido
- Correlación de identidades
- Grafo de inteligencia
- Historial de consultas
- Dashboard analítico
- Watchlists y alertas automáticas
- Exportación de evidencias
- Arquitectura extensible basada en plugins

La solución debe ser modular, desacoplada y preparada para incorporar nuevas fuentes OSINT sin modificar el núcleo del sistema.

---

## Recomendación operativa

Para un entorno profesional de investigación, prioriza APIs oficiales y datos públicos estructurados cuando existan y usa scraping solo cuando no haya una API adecuada. Esto mejora velocidad, estabilidad, trazabilidad y mantenimiento.

Para consultas pesadas, conviene introducir una cola de tareas con Celery + Redis para evitar que la interfaz quede bloqueada durante búsquedas extensas.

