# NEXO-147 — Integration Map
*Generado: Sprint 0 — Auditoría | 2026-06-05*

---

## 1. Flujo de Datos Actual

```
HTTP GET /osint/search?q=<target>&source=<hint>
    │
    ▼
search/routes.py:search()
    │
    ▼
UniversalOsintEngine.search(target, source_hint)        [engine.py]
    │
    ├─► detect_target_type(target)                      [line 485]
    │       → ip / email / url / domain / hash / phone / full_name / alias / username / unknown
    │
    ├─► Cache lookup SHA-256 (CacheConsulta)            [line 486-490]
    │       → EARLY RETURN si cache hit no expirado
    │
    ├─► discover_sources(target_type, source_hint)      [line 492]
    │       → list[str]: ["github","reddit","facebook","x","tiktok","plugins"]
    │
    ├─► run_collectors(target, sources)                 [line 493]
    │       ThreadPoolExecutor(max_workers=6)
    │       → dict[str, dict[str, Any]]  (raw, heterogéneo por fuente)
    │
    ├─► _normalize_collected(collected, target)         [line 494]
    │       → list[NormalizedResult]
    │
    ├─► IdentityCorrelationEngine.correlate(normalized) [line 494]
    │       → list[NormalizedResult] (deduplicado)
    │
    ├─► FindingEngine.build(normalized)                 [line 495]
    │       → (findings: list[dict], risk: dict)
    │
    ├─► build_graph(target, collected)                  [line 496]
    │       ⚠️ Consume el dict RAW, no NormalizedResult
    │       → {"nodes": [...], "links": [...], "findings": [...], "stats": {...}}
    │
    └─► persist_results()                               [lines 520-533]
            → DB: ConsultaOsint, CacheConsulta, ResultadoOsint, graph nodes/edges
```

### Sistema paralelo HUÉRFANO (no conectado al flujo principal)

```
WatchlistService._check_one()   [monitoring/watchlists.py]
    │
    ▼
OsintOrchestrator.default().run(target, target_type)    [engines/orchestration.py]
    │
    ▼
dict[str, ConnectorResult]
    │
    └─► Solo se usa .ok para contar éxitos.
        .data de cada conector es DESCARTADO completamente.
```

---

## 2. Schemas de Datos

### NormalizedResult (`modules/osint/core/schemas.py`, líneas 16-33)

```python
@dataclass(slots=True)
class NormalizedResult:
    source: str          # e.g. "github", "reddit", "ip-api", "rdap"
    entity_type: str     # e.g. "social_profile", "email", "repository", "domain", "ip", "organization"
    value: str           # el valor canónico de esta entidad
    confidence: float    # 0.0–1.0
    url: str = ""        # URL directa a la evidencia (opcional)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]: ...
```

### SearchOutcome (`modules/osint/core/schemas.py`, líneas 36-51)

```python
@dataclass(slots=True)
class SearchOutcome:
    source: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    results: list[NormalizedResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]: ...
```

> **⚠️ ADVERTENCIA**: `SearchOutcome` es **código muerto** — nunca se instancia en ninguna ruta de código activa. Sprint 1 debería adoptarlo como tipo estándar de salida del `ResultMerger` o eliminarlo.

### ConnectorResult (`modules/osint/connectors/base.py`, líneas 8-24)

```python
@dataclass(slots=True)
class ConnectorResult:
    connector: str           # nombre snake_case, e.g. "github", "reddit"
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]: ...
```

---

## 3. Firma de build_graph()

**Archivo canónico**: `modules/osint/graph/builder.py`, línea 104
*(`modules/osint/analytics/graph_builder.py` es un shim puro que re-exporta desde `graph/builder.py`)*

```python
def build_graph(
    username: str,
    github_profile: dict | None = None,
    github_repos:   list | None = None,
    reddit_profile: dict | None = None,
    facebook_data:  dict | None = None,
    ip_data:        dict | None = None,
    rdap_data:      dict | None = None,
) -> dict:
```

**Retorna**: `{"nodes": list[dict], "links": list[dict], "findings": list[dict], "stats": dict}`

**Campos consumidos por parámetro**:

| Parámetro | Campos consumidos |
|---|---|
| `github_profile` | `email`, `company`, `blog`, `twitter_username`, `location` |
| `github_repos` | `name`, `language`, `stargazers_count`, `html_url`, `updated_at` |
| `reddit_profile` | `name`, `total_karma`, `link_karma` |
| `facebook_data` | `is_mock`, `email_hints[]`, `og["og:title"]`, `mutual_connections[]` |
| `ip_data` | `query`, `isp`, `org`, `country`, `city`, `lat`, `lon` |
| `rdap_data` | `ldhName`, `status`, `nameservers[]`, `entities[].name`, `entities[].roles` |

> **⚠️ GAP CRÍTICO**: `build_graph()` **NO** acepta datos de X/TikTok, DuckDuckGo, HIBP, AbuseIPDB, AlienVault, Whois, ni CrtSH. Los conectores de `OsintOrchestrator` que producen esos datos no tienen camino hacia `build_graph()`.

---

## 4. FindingEngine y IdentityCorrelationEngine

### FindingEngine (`modules/osint/core/findings.py`, línea 18)

> **Nota**: El método es `build()`, no `generate()`. No existe `generate()`.

```python
def build(self, results: Iterable[NormalizedResult]) -> tuple[list[dict], dict]:
```

**Retorna**: `(findings_list, {"score": int (máx 20), "level": str})`
Cada finding dict tiene claves: `nivel`, `titulo`, `descripcion`, `tipo`

### IdentityCorrelationEngine (`modules/osint/core/correlation.py`, línea 35)

```python
def correlate(self, results: Iterable[NormalizedResult]) -> list[NormalizedResult]:
```

Agrupa por `(entity_type.lower(), value.strip().lower())`. Si hay múltiples items en un bucket: toma la mayor confianza, primera URL no vacía, fusiona todos los metadatos, añade `metadata["sources"]` y `metadata["merged_count"]`. Retorna lista ordenada.

---

## 5. Fractura de Integración

### Diagnóstico preciso

`OsintOrchestrator` está definido en `modules/osint/engines/orchestration.py`. Su método `run()` retorna `dict[str, ConnectorResult]`. Es instanciado en **exactamente un lugar**: `modules/osint/monitoring/watchlists.py:_check_one()`. Ahí, el `ConnectorResult` solo se usa para contar cuántos fueron `ok`. El `.data` de cada conector es descartado.

`UniversalOsintEngine.search()` en `modules/osint/core/engine.py` tiene **cero imports** de `modules.osint.engines.orchestration` y **cero imports** de `modules.osint.connectors.*`. Importa funciones legacy directamente de `modules/osint/social/routes.py`.

### Duplicación de implementación

```
GitHub API ──► social/routes.py:_fetch_github()       # legacy, retorna dict raw
GitHub API ──► connectors/github.py:GitHubConnector   # typed, retorna ConnectorResult
```

Las mismas llamadas HTTP están duplicadas. Las dos implementaciones son independientes.

### Datos de X y TikTok silenciosamente nulos

En `engine.py` líneas 78 y 84, `extract_x_profiles` y `extract_tiktok_profiles` se referencian como nombres sin importar. Son siempre `None`/falsy. **X y TikTok nunca producen datos en el flujo actual.**

---

## 6. Puntos de Integración para Sprint 1

### Sitio de inyección exacto en `engine.py`

```python
# engine.py líneas 492-494 (estado actual):
sources    = self.discover_sources(detection.target_type, source_hint)
collected  = self.run_collectors(target, sources)   # ← PUNTO DE INYECCIÓN
normalized = self._normalize_collected(collected, target)
```

**Sprint 1 modifica entre líneas 493 y 494**:

```python
# DESPUÉS — Sprint 1:
sources       = self.discover_sources(detection.target_type, source_hint)
collected     = self.run_collectors(target, sources)         # legacy intacto
orch_results  = OsintOrchestrator.default().run(target, detection.target_type)
collected     = ResultMerger.merge_into_collected(collected, orch_results)  # NUEVO
normalized    = self._normalize_collected(collected, target)
```

---

## 7. Transformación: ConnectorResult → formato collected

| Campo ConnectorResult | Mapea a en `collected[name]` | Notas |
|---|---|---|
| `.data` (passthrough directo) | top-level de `collected[name]` | `github.data == {"profile": ..., "repos": [...]}` coincide exactamente |
| `.errors` | `collected[name]["errors"]` | misma clave |
| `.metadata` | `collected[name]["_metadata"]` | no consumido por código actual |
| `.connector` | clave del dict: `collected[connector]` | `GitHubConnector.name == "github"` alineado |
| `.ok` | `collected[name]["_ok"]` | no en formato actual |

Para `github` y `reddit`, el layout de `.data` del conector coincide exactamente con lo que `_normalize_collected()` espera. Para conectores sin cobertura en `_normalize_collected()` (hibp, abuseipdb, alienvault, whois, crtsh, duckduckgo), sus datos entran en `collected` pero son ignorados silenciosamente.

---

## 8. Riesgos y Advertencias para Sprint 1

1. **Exception silenciosa en persist**: Línea 533 captura todas las excepciones con solo `db.session.rollback()` y sin logging. Si la escritura DB falla silenciosamente, el cache nunca se escribe.

2. **X y TikTok son datos nulos**: `extract_x_profiles` y `extract_tiktok_profiles` no están importadas (líneas 78 y 84 de `engine.py`). Sprint 1 no debe contar con estas fuentes.

3. **Dos instancias de UniversalOsintEngine**: `social/routes.py` instancia un segundo `_ENGINE` en línea 121. Dos instancias comparten tablas DB pero no estado en memoria.

4. **Nombres de clave de `collected` son críticos**: `build_graph()` usa `collected.get("github", {})`. Si Sprint 1 introduce una clave con nombre diferente, el grafo perderá esos datos silenciosamente.

5. **`WatchlistService` descarta datos del orquestador**: Si Sprint 1 intenta usar `WatchlistService` como fuente secundaria, hay que extenderlo para pasar resultados a `_normalize_collected()`.

6. **`SearchOutcome` es código muerto**: Limpiar o adoptar como tipo de salida de `ResultMerger`.

7. **Alineación de nombre de conector**: Verificar que todos los conectores de `OsintOrchestrator` usen el mismo nombre que las claves legacy en `collected`.

8. **CrtSH recopilado pero no grafado**: `_collect_domain()` obtiene datos de CrtSH en `collected["domain"]["crt_data"]` pero `build_graph()` los ignora.

9. **`HibpConnector` requiere `HIBP_API_KEY`**: Retorna `ConnectorResult(ok=False)` silenciosamente si la env var no está configurada.

---

## 9. Mapa de Archivos Clave

| Archivo | Rol en Sprint 1 |
|---|---|
| `modules/osint/core/engine.py` | **Modificar**: inyectar OsintOrchestrator + ResultMerger |
| `modules/osint/graph/builder.py` | **No modificar**: solo leer para entender build_graph() |
| `modules/osint/core/schemas.py` | **Leer**: contratos NormalizedResult, SearchOutcome |
| `modules/osint/connectors/base.py` | **Leer**: ConnectorResult, BaseConnector ABC |
| `modules/osint/engines/orchestration.py` | **No modificar**: wiring solo en engine.py |
| `modules/osint/core/correlation.py` | **No modificar**: ya funcional |
| `modules/osint/core/findings.py` | **No modificar**: ya funcional |
| `modules/osint/connectors/github.py` | **Verificar**: que `.name == "github"` |
| `modules/osint/connectors/reddit.py` | **Verificar**: que `.name == "reddit"` |
| `modules/osint/social/routes.py` | **No modificar**: legacy intacto |
| `modules/osint/monitoring/watchlists.py` | **No modificar en Sprint 1** |
| `modules/osint/connectors/social_stubs.py` | **Informativo**: 19 stubs, siempre ok=False |

---

*Documento generado por Sprint 0 — Auditoría. Requerido antes de Sprint 1.*
