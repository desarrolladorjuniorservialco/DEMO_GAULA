# Módulo OSINT — NEXO-147

Motor de inteligencia de fuentes abiertas integrado en la plataforma GAULA. Recopila, normaliza, correlaciona y califica el riesgo de información pública sobre un objetivo (usuario, dominio, IP, correo, teléfono, etc.).

---

## Estructura

```
modules/osint/
├── core/                   # Motor central y tipos de datos
│   ├── engine.py           # UniversalOsintEngine — punto de entrada principal
│   ├── schemas.py          # NormalizedResult, TargetDetection, SearchOutcome
│   ├── correlation.py      # IdentityCorrelationEngine — deduplicación y correlación
│   ├── findings.py         # FindingEngine — generación de hallazgos
│   ├── result_merger.py    # ResultMerger — unificación legacy + conectores
│   └── target_detection.py # Detección automática del tipo de objetivo
│
├── connectors/             # Adaptadores de fuentes externas (BaseConnector)
│   ├── base.py             # Contrato BaseConnector / ConnectorResult
│   ├── github.py
│   ├── reddit.py
│   ├── duckduckgo.py
│   ├── crtsh.py            # Certificados SSL (crt.sh)
│   ├── rdap.py             # Registro de dominios (RDAP)
│   ├── abuseipdb.py
│   ├── alienvault.py       # OTX AlienVault
│   ├── hibp.py             # Have I Been Pwned
│   ├── whois.py
│   └── social_stubs.py     # Stubs para redes sociales sin API oficial
│
├── engines/
│   └── orchestration.py    # OsintOrchestrator — ejecución concurrente de conectores
│
├── analyzers/
│   ├── risk.py             # RiskAnalyzer — puntuación LIMPIO / BAJO / MEDIO / ALTO / CRITICO
│   └── enrichment.py       # Enriquecimiento adicional de entidades
│
├── plugins/                # Sistema de plugins auto-descubiertos
│   ├── base.py             # BaseOsintPlugin — contrato mínimo
│   ├── registry.py         # Autodescubrimiento en arranque Flask
│   └── ejemplo_ip.py       # Plugin de ejemplo
│
├── social/                 # Scrapers de redes sociales
│   ├── routes.py           # _fetch_github, _fetch_reddit (HTTP directo)
│   └── scrapers/
│       └── facebook_playwright.py  # Playwright para Facebook
│
├── services/               # Servicios de búsqueda
│   ├── search_engine.py    # ejecutar_dork_universal — búsquedas OSINT genéricas
│   ├── x_osint.py          # extract_x_profiles — perfiles de X/Twitter
│   ├── tiktok_osint.py     # extract_tiktok_profiles — perfiles de TikTok
│   └── facebook_osint.py
│
├── analytics/
│   ├── routes.py
│   └── graph_builder.py    # build_graph — grafo de relaciones entre entidades
│
├── graph/                  # Persistencia y exportación del grafo
│   ├── builder.py
│   ├── persistence.py
│   └── exporters.py
│
├── cache/                  # Capas de caché (memoria, Redis, BD)
├── opendata/               # Fuentes de datos abiertos (IP geolocalización, RDAP)
├── open_data/               # Nueva capa de inteligencia de datos públicos
├── history/                # Repositorio de consultas históricas
├── dashboard/              # Rutas del panel OSINT
├── search/                 # Rutas de búsqueda web
├── watchlists/             # Listas de seguimiento
└── monitoring/             # Jobs de monitoreo continuo
```

---

## Flujo de una consulta

```
UniversalOsintEngine.search(target, source_hint)
  │
  ├─ detect_target_type()       → TargetDetection (username/email/domain/ip/…)
  ├─ _load_cache()              → retorna si hay hit válido (TTL 1 h)
  ├─ discover_sources()         → lista de fuentes según tipo + hint
  │
  ├─ run_collectors()           → ThreadPoolExecutor (≤6 workers)
  │    ├─ GitHub API
  │    ├─ Reddit API
  │    ├─ Facebook (Playwright)
  │    ├─ X/Twitter (dork)
  │    ├─ TikTok (dork)
  │    ├─ IP geolocalización
  │    ├─ RDAP + crt.sh
  │    └─ Plugins
  │
  ├─ OsintOrchestrator.run()    → conectores tipados en paralelo
  │    (GitHub, Reddit, DuckDuckGo, crt.sh, RDAP,
  │     AbuseIPDB, AlienVault, HIBP, Whois, stubs sociales)
  │
  ├─ _normalize_collected()     → list[NormalizedResult]
  ├─ ResultMerger.merge()       → combina legacy + conectores
  ├─ IdentityCorrelationEngine  → deduplicación y correlación de identidad
  ├─ FindingEngine.build()      → hallazgos + puntuación de riesgo
  ├─ build_graph()              → grafo de relaciones (nodos + enlaces)
  │
  └─ persist_results()          → BD (ConsultaOsint, ResultadoOsint, CacheConsulta, grafo)
```

---

## Tipos de objetivo soportados

| Tipo        | Fuentes activadas por defecto                           |
|-------------|--------------------------------------------------------|
| `username`  | GitHub, Reddit, Facebook, X, TikTok, plugins           |
| `email`     | GitHub, Reddit, Facebook, X, TikTok, HIBP, plugins     |
| `domain`    | RDAP, crt.sh, Whois, DuckDuckGo, plugins               |
| `ip`        | AbuseIPDB, AlienVault, geolocalización, plugins        |
| `phone`     | Facebook, plugins                                      |
| `hash`      | plugins                                                |
| `unknown`   | GitHub, Reddit, DuckDuckGo, plugins                    |

El parámetro `source_hint` permite sobreescribir las fuentes:

| Hint         | Fuentes                                               |
|--------------|------------------------------------------------------|
| `both`       | GitHub, Reddit                                       |
| `social`     | GitHub, Reddit, Facebook, X, TikTok, plugins         |
| `deep_all`   | Igual que `social`                                   |
| `network`    | IP, dominio, plugins                                 |
| `government` | Dominios, IP, DuckDuckGo, plugins                    |
| `osint_all`  | GitHub, Reddit, DuckDuckGo, dominio, IP, plugins     |

`government` queda reservado para consultas orientadas a registros y trazas publicas. En la version actual usa las fuentes existentes mas cercanas a ese perfil mientras se incorpora la nueva capa `modules/osint/open_data/`.

---

## Puntuación de riesgo

`RiskAnalyzer` agrega puntos por indicadores de conectores:

| Indicador             | Puntos     |
|-----------------------|-----------|
| Brecha HIBP           | 15 × (máx 5 brechas) |
| Paste HIBP            | 10 × (máx 3 pastes)  |
| AbuseIPDB ≥ 75 %      | 30        |
| AbuseIPDB 25–74 %     | 15        |
| Pulso OTX AlienVault  | 10 × (máx 5 pulsos)  |
| > 50 subdominios      | 5         |

Niveles resultantes: **LIMPIO** (0–9) · **BAJO** (10–24) · **MEDIO** (25–49) · **ALTO** (50–74) · **CRITICO** (75+)

---

## Extender el módulo

### Agregar un conector

```python
# modules/osint/connectors/mi_fuente.py
from modules.osint.connectors.base import BaseConnector, ConnectorResult

class MiFuenteConnector(BaseConnector):
    name = "mi_fuente"
    supported_target_types = frozenset({"username", "email"})

    def fetch(self, target: str, **kwargs) -> ConnectorResult:
        # Nunca lanzar excepciones; capturar y retornar ConnectorResult(ok=False)
        ...
```

Luego registrarlo en `OsintOrchestrator.default()` dentro de `engines/orchestration.py`.

### Agregar un plugin

```python
# modules/osint/plugins/mi_plugin.py
from modules.osint.plugins.base import BaseOsintPlugin

class MiPlugin(BaseOsintPlugin):
    name = "mi_plugin"
    category = "identity"

    def ejecutar(self, objetivo: str) -> dict:
        return {"status": "ok", "plugin": self.name, "data": {}}
```

El `registry.py` lo descubre automáticamente al iniciar Flask — sin registrarlo manualmente.

---

## Variables de entorno relevantes

| Variable              | Uso                                  |
|-----------------------|--------------------------------------|
| `GITHUB_TOKEN`        | Eleva el rate-limit de la API GitHub |
| `ABUSEIPDB_API_KEY`   | Consultas AbuseIPDB                  |
| `ALIENVAULT_API_KEY`  | Consultas OTX AlienVault             |
| `HIBP_API_KEY`        | Have I Been Pwned v3                 |

---

## Caché

Los resultados se almacenan en `CacheConsulta` con un TTL de **1 hora**. La clave es un SHA-256 de `target_type:source_hint:target`. Las consultas cacheadas incrementan el contador `hits` y no re-ejecutan los colectores.
