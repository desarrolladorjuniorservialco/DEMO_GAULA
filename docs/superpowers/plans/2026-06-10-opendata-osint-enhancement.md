# Tab "Datos Abiertos" OSINT — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer efectiva la búsqueda del tab Datos Abiertos por placa (SIMIT real desde dataset corregido), cédula (RUES + comparendos con identificación + dorking web) y teléfono (sin cambios funcionales).

**Architecture:** Cada fuente es un `Connector` (subclase de `BaseConnector`) que devuelve `ConnectorResult` y nunca lanza excepción. `OsintOrchestrator` los corre en paralelo. El router `opendata/routes.py` detecta el tipo de término y selecciona conectores. Un helper `web_dork.py` centraliza el dorking DuckDuckGo reutilizado por teléfono, cédula, placa y nombre.

**Tech Stack:** Python 3, Flask, requests, duckduckgo-search, phonenumbers (todo ya en `requirements.txt`). Tests con pytest + unittest.mock.

**Spec:** `docs/superpowers/specs/2026-06-10-opendata-osint-enhancement-design.md`

---

## File Structure

- **Create** `modules/osint/connectors/web_dork.py` — helper reutilizable de dorking DuckDuckGo.
- **Create** `modules/osint/connectors/rues.py` — `RuesConnector` (consulta empresarial por documento/nombre).
- **Modify** `modules/osint/connectors/simit.py` — corregir datasets y mapeo de campos; normalizar filas.
- **Modify** `modules/osint/connectors/phone.py` — delegar dorking a `web_dork.run_dork`.
- **Modify** `modules/osint/opendata/routes.py` — `_detect_type` con `name`; orquestar SIMIT+RUES+Phone+dork; recalcular conteos.
- **Modify** `templates/osint/opendata_fragment.html` — columnas SIMIT reales, sección RUES, sección menciones web genérica.
- **Modify** `tests/test_opendata_connectors.py` — actualizar al nuevo esquema; tests de RUES y web_dork.
- **Modify** `tests/test_opendata_routes.py` — `_detect_type` name; flujo por tipo.

**Convención de datos normalizados de SIMIT** (forma estable que la plantilla consume), cada fila:
```python
{
  "placa": str,            # "ABC123" o "—"
  "fecha": str,            # "25/01/2019" o "—"
  "valor": str,            # "414058" o "—"
  "lugar": str,            # "Bucaramanga, Santander" o "—"
  "estado": str,           # "Pagada" / "Pendiente" / "—"
  "vigencia": str,         # "2019" o "—"
  "identificacion": str,   # presente solo en búsqueda por documento; "" si no aplica
}
```

---

## Task 1: Helper de dorking web reutilizable (`web_dork.py`)

**Files:**
- Create: `modules/osint/connectors/web_dork.py`
- Test: `tests/test_opendata_connectors.py`

- [ ] **Step 1: Write the failing tests**

Añadir al final de `tests/test_opendata_connectors.py`:

```python
from modules.osint.connectors import web_dork


def test_web_dork_dedups_by_url():
    rows = [
        {"href": "https://a.com", "title": "A", "body": "ba"},
        {"href": "https://a.com", "title": "A dup", "body": "dup"},
        {"href": "https://b.com", "title": "B", "body": "bb"},
    ]
    with patch("modules.osint.connectors.web_dork.DDGS") as mock_ddgs:
        mock_ddgs.return_value.__enter__.return_value.text.return_value = rows
        results, errors = web_dork.run_dork(['"123"'], max_results=10, sleep_between=0)

    urls = [r["url"] for r in results]
    assert urls == ["https://a.com", "https://b.com"]
    assert errors == []


def test_web_dork_handles_ratelimit():
    from duckduckgo_search.exceptions import DuckDuckGoSearchException
    with patch("modules.osint.connectors.web_dork.DDGS") as mock_ddgs:
        inst = mock_ddgs.return_value.__enter__.return_value
        inst.text.side_effect = DuckDuckGoSearchException("ratelimit")
        results, errors = web_dork.run_dork(['"x"'], max_results=5, sleep_between=0)

    assert results == []
    assert len(errors) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_opendata_connectors.py::test_web_dork_dedups_by_url tests/test_opendata_connectors.py::test_web_dork_handles_ratelimit -v`
Expected: FAIL con `ModuleNotFoundError` / `ImportError` (web_dork no existe).

- [ ] **Step 3: Write the implementation**

Crear `modules/osint/connectors/web_dork.py`:

```python
"""connectors/web_dork.py — Helper reutilizable de dorking DuckDuckGo."""
from __future__ import annotations

import time
from typing import Any

try:
    from duckduckgo_search import DDGS
    from duckduckgo_search.exceptions import DuckDuckGoSearchException
    try:
        from duckduckgo_search.exceptions import RatelimitException
    except ImportError:
        RatelimitException = DuckDuckGoSearchException
    _AVAILABLE = True
except ImportError:
    DDGS = None  # type: ignore
    DuckDuckGoSearchException = Exception  # type: ignore
    RatelimitException = Exception  # type: ignore
    _AVAILABLE = False


def run_dork(
    queries: list[str],
    *,
    max_results: int = 10,
    sleep_between: float = 1.5,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Ejecuta dorks DuckDuckGo. Devuelve (resultados, errores). Nunca lanza."""
    if not _AVAILABLE:
        return [], ["duckduckgo-search no disponible."]

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_urls: set[str] = set()

    try:
        with DDGS() as ddgs:
            for query in queries:
                try:
                    for r in (ddgs.text(query, max_results=max_results) or []):
                        url = r.get("href", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            results.append({
                                "title":   r.get("title", "")[:120],
                                "url":     url,
                                "snippet": r.get("body", "")[:250],
                            })
                    if sleep_between:
                        time.sleep(sleep_between)
                except RatelimitException:
                    errors.append("DDG: rate limit — intenta en 60s.")
                    break
                except DuckDuckGoSearchException as exc:
                    errors.append(f"DDG: {exc}")
    except Exception as exc:  # noqa: BLE001 — el helper nunca debe propagar
        errors.append(f"DDG: {exc}")

    return results, errors
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_opendata_connectors.py::test_web_dork_dedups_by_url tests/test_opendata_connectors.py::test_web_dork_handles_ratelimit -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add modules/osint/connectors/web_dork.py tests/test_opendata_connectors.py
git commit -m "feat(osint): helper reutilizable web_dork para dorking DuckDuckGo"
```

---

## Task 2: Refactor `phone.py` para usar `web_dork`

**Files:**
- Modify: `modules/osint/connectors/phone.py:125-156` (bloque de dorking inline)
- Test: `tests/test_opendata_connectors.py` (los tests de phone existentes deben seguir pasando)

- [ ] **Step 1: Reemplazar el bloque de dorking inline**

En `modules/osint/connectors/phone.py`, dentro de `PhoneConnector.fetch`, reemplazar TODO el bloque que va desde `dork_results: list[dict] = []` hasta el final del `except ImportError:` (líneas ~125-156) por:

```python
        from modules.osint.connectors.web_dork import run_dork
        dork_results, errors = run_dork(
            [f'"{target}"', f'"{normalized}" Colombia'],
            max_results=10,
        )
```

Eliminar también el `import time` del encabezado si ya no se usa en el resto del archivo (verificar con `grep "time\." modules/osint/connectors/phone.py`; si no hay otros usos, eliminar la línea `import time`).

- [ ] **Step 2: Actualizar el test de phone que mockea DDGS directamente**

Los tests `test_phone_fetch_local_carrier`, `test_phone_fetch_numverify_enrichment`, `test_phone_fetch_no_numverify_key` parchean `duckduckgo_search.DDGS`. Ahora el dorking ocurre en `web_dork`, así que cambiar el parche en esos 3 tests de:

```python
        with _patch2("duckduckgo_search.DDGS") as mock_ddgs:
            mock_ddgs.return_value.__enter__.return_value.text.return_value = []
```

a:

```python
        with _patch2("modules.osint.connectors.web_dork.DDGS") as mock_ddgs:
            mock_ddgs.return_value.__enter__.return_value.text.return_value = []
```

(Mantener la indentación existente de cada test.)

- [ ] **Step 3: Run phone tests**

Run: `python -m pytest tests/test_opendata_connectors.py -k phone -v`
Expected: PASS (todos los `test_phone_*`).

- [ ] **Step 4: Commit**

```bash
git add modules/osint/connectors/phone.py tests/test_opendata_connectors.py
git commit -m "refactor(osint): phone delega dorking a web_dork.run_dork"
```

---

## Task 3: Corregir `SimitConnector` (datasets reales + normalización)

**Files:**
- Modify: `modules/osint/connectors/simit.py` (reescritura completa)
- Test: `tests/test_opendata_connectors.py` (actualizar tests de SIMIT al nuevo esquema)

- [ ] **Step 1: Reescribir los tests de SIMIT al esquema real**

En `tests/test_opendata_connectors.py`, reemplazar los tests `test_simit_fetch_document_ok`, `test_simit_fetch_no_results`, `test_simit_fetch_network_error` por:

```python
def test_simit_fetch_plate_ok():
    c = SimitConnector()
    mock_rows = [{
        "vigencia": "2019", "placa": "MIK715", "fecha_multa": "25/01/2019",
        "valor_multa": "414058", "departamento": "Santander",
        "ciudad": "Bucaramanga", "pagado_si_no": "SI",
    }]
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_rows)
        mock_get.return_value.raise_for_status = lambda: None
        result = c.fetch("MIK715", target_type="plate")

    assert result.ok is True
    assert result.connector == "simit"
    row = result.data["rows"][0]
    assert row["placa"] == "MIK715"
    assert row["valor"] == "414058"
    assert row["lugar"] == "Bucaramanga, Santander"
    assert row["estado"] == "Pagada"
    assert result.metadata["dataset"] == "72nf-y4v3"


def test_simit_fetch_document_uses_comparendos_dataset():
    c = SimitConnector()
    mock_rows = [{
        "identificacion": "12345678", "placa": "ABC123",
        "fecha": "2020-03-10", "infraccion": "C29", "valor": "390000",
    }]
    captured = {}
    def _fake_get(url, **kwargs):
        captured["url"] = url
        captured["where"] = kwargs["params"]["$where"]
        m = MagicMock(status_code=200, json=lambda: mock_rows)
        m.raise_for_status = lambda: None
        return m
    with patch("modules.osint.connectors.simit.requests.get", side_effect=_fake_get):
        result = c.fetch("12345678", target_type="document")

    assert "rfag-apa4" in captured["url"]
    assert "identificacion='12345678'" in captured["where"]
    assert result.ok is True
    assert result.data["rows"][0]["identificacion"] == "12345678"


def test_simit_fetch_no_results():
    c = SimitConnector()
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
        mock_get.return_value.raise_for_status = lambda: None
        result = c.fetch("XXX000", target_type="plate")

    assert result.ok is False
    assert result.data["rows"] == []


def test_simit_fetch_network_error():
    import requests as req
    c = SimitConnector()
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.side_effect = req.RequestException("timeout")
        result = c.fetch("MIK715", target_type="plate")

    assert result.ok is False
    assert len(result.errors) == 1
    assert "timeout" in result.errors[0]


def test_simit_build_where_sanitizes_quotes():
    c = SimitConnector()
    where = c._build_where("AB'C12", "plate")
    assert "''" in where
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_opendata_connectors.py -k simit -v`
Expected: FAIL (los nuevos tests esperan campos `valor`/`lugar`/`estado`/`dataset` y dataset `rfag-apa4` que aún no existen).

- [ ] **Step 3: Reescribir `simit.py`**

Reemplazar el contenido completo de `modules/osint/connectors/simit.py` por:

```python
"""connectors/simit.py — Infracciones de tránsito (SIMIT, datos.gov.co).

Placa  -> dataset 72nf-y4v3 (Historial de multas SIMIT, nacional 2019-2023).
Cédula -> dataset rfag-apa4 (Comparendos con campo 'identificacion').
"""
from __future__ import annotations

import re
import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_BASE = "https://www.datos.gov.co/resource/{dataset}.json"
_DATASET_PLATE = "72nf-y4v3"
_DATASET_DOC = "rfag-apa4"
_HEADERS = {"Accept": "application/json", "User-Agent": "NEXO-147-OSINT/1.0"}
_PLATE_RE = re.compile(r"^[A-Za-z]{3}[0-9A-Za-z]{3}$")


class SimitConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "simit"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"document", "plate", "unknown"})

    @property
    def timeout_seconds(self) -> float:
        return 15.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        target_type: str = kwargs.get("target_type", "unknown")
        t0 = time.monotonic()
        errors: list[str] = []
        raw_rows: list[dict] = []

        dataset = self._dataset_for(target, target_type)
        where = self._build_where(target, target_type)
        url = _BASE.format(dataset=dataset)
        params: dict[str, Any] = {"$where": where, "$limit": 50}

        try:
            resp = requests.get(url, headers=_HEADERS, params=params, timeout=self.timeout_seconds)
            resp.raise_for_status()
            raw_rows = resp.json() or []
        except requests.RequestException as exc:
            errors.append(f"simit: {exc}")

        rows = [self._normalize(r) for r in raw_rows]
        return ConnectorResult(
            connector=self.name,
            ok=len(rows) > 0,
            data={"rows": rows},
            errors=errors,
            metadata={
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "count": len(rows),
                "dataset": dataset,
            },
        )

    def _dataset_for(self, target: str, target_type: str) -> str:
        if target_type == "document" or (target_type != "plate" and target.isdigit()):
            return _DATASET_DOC
        return _DATASET_PLATE

    def _build_where(self, target: str, target_type: str) -> str:
        safe = target.replace("'", "''")
        if target_type == "document" or (target_type != "plate" and target.isdigit()):
            return f"identificacion='{safe}'"
        return f"upper(placa)=upper('{safe}')"

    @staticmethod
    def _normalize(r: dict) -> dict:
        ciudad = r.get("ciudad") or r.get("municipio") or ""
        depto = r.get("departamento") or ""
        lugar = ", ".join(p for p in (ciudad, depto) if p) or "—"

        pagado = (r.get("pagado_si_no") or "").strip().upper()
        if pagado in ("SI", "SÍ"):
            estado = "Pagada"
        elif pagado == "NO":
            estado = "Pendiente"
        else:
            estado = r.get("estado") or "—"

        return {
            "placa":          r.get("placa") or "—",
            "fecha":          (r.get("fecha_multa") or r.get("fecha") or "")[:10] or "—",
            "valor":          r.get("valor_multa") or r.get("valor") or "—",
            "lugar":          lugar,
            "estado":         estado,
            "vigencia":       r.get("vigencia") or "—",
            "identificacion": r.get("identificacion") or "",
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_opendata_connectors.py -k simit -v`
Expected: PASS (todos los `test_simit_*`).

- [ ] **Step 5: Commit**

```bash
git add modules/osint/connectors/simit.py tests/test_opendata_connectors.py
git commit -m "fix(osint): SIMIT usa datasets reales (placa 72nf-y4v3, doc rfag-apa4) y normaliza filas"
```

---

## Task 4: Nuevo `RuesConnector`

**Files:**
- Create: `modules/osint/connectors/rues.py`
- Test: `tests/test_opendata_connectors.py`

- [ ] **Step 1: Write the failing tests**

Añadir a `tests/test_opendata_connectors.py`:

```python
from modules.osint.connectors.rues import RuesConnector


def test_rues_connector_name_and_types():
    c = RuesConnector()
    assert c.name == "rues"
    assert "document" in c.supported_target_types
    assert "name" in c.supported_target_types
    assert c.needs_api_key is False


def test_rues_fetch_ok():
    c = RuesConnector()
    payload = {"registros": [{
        "razon_social": "COMERCIALIZADORA XYZ SAS",
        "matricula": "0001234",
        "estado_matricula": "ACTIVA",
        "camara_comercio": "BOGOTA",
        "nit": "900123456",
    }]}
    with patch("modules.osint.connectors.rues.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: payload)
        mock_get.return_value.raise_for_status = lambda: None
        result = c.fetch("900123456", target_type="document")

    assert result.ok is True
    assert result.connector == "rues"
    exp = result.data["expedientes"][0]
    assert exp["razon_social"] == "COMERCIALIZADORA XYZ SAS"
    assert exp["estado"] == "ACTIVA"


def test_rues_fetch_no_results():
    c = RuesConnector()
    with patch("modules.osint.connectors.rues.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"registros": []})
        mock_get.return_value.raise_for_status = lambda: None
        result = c.fetch("000", target_type="document")

    assert result.ok is False
    assert result.data["expedientes"] == []


def test_rues_fetch_non_json_fails_gracefully():
    c = RuesConnector()
    def _raise_json():
        raise ValueError("no json")
    with patch("modules.osint.connectors.rues.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=_raise_json)
        mock_get.return_value.raise_for_status = lambda: None
        result = c.fetch("900123456", target_type="document")

    assert result.ok is False
    assert len(result.errors) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_opendata_connectors.py -k rues -v`
Expected: FAIL con `ModuleNotFoundError` (rues.py no existe).

- [ ] **Step 3: Write the implementation**

Crear `modules/osint/connectors/rues.py`:

```python
"""connectors/rues.py — Registro Único Empresarial y Social (RUES).

Consulta pública por documento (NIT/cédula) o razón social. Devuelve
expedientes mercantiles: razón social, matrícula, estado, cámara.

El endpoint público de RUES expone búsqueda por NIT/razón social. Si la API
cambia o bloquea, el conector degrada a ok=False sin propagar excepción.
"""
from __future__ import annotations

import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_API_URL = "https://ruesapi.rues.org.co/api/v1/expedientes/buscar"
_HEADERS = {"Accept": "application/json", "User-Agent": "NEXO-147-OSINT/1.0"}


class RuesConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "rues"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"document", "name"})

    @property
    def needs_api_key(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> float:
        return 12.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        target_type: str = kwargs.get("target_type", "document")
        t0 = time.monotonic()
        errors: list[str] = []
        expedientes: list[dict] = []

        params = self._build_params(target, target_type)
        try:
            resp = requests.get(
                _API_URL, headers=_HEADERS, params=params, timeout=self.timeout_seconds
            )
            resp.raise_for_status()
            payload = resp.json()
            expedientes = self._parse(payload)
        except requests.RequestException as exc:
            errors.append(f"rues: {exc}")
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"rues: respuesta no interpretable — {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=len(expedientes) > 0,
            data={"expedientes": expedientes},
            errors=errors,
            metadata={
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "count": len(expedientes),
            },
        )

    def _build_params(self, target: str, target_type: str) -> dict[str, Any]:
        if target_type == "name":
            return {"razon_social": target, "tipo": "razon_social"}
        return {"nit": target, "tipo": "nit"}

    @staticmethod
    def _parse(payload: Any) -> list[dict]:
        registros = []
        if isinstance(payload, dict):
            registros = payload.get("registros") or payload.get("data") or []
        elif isinstance(payload, list):
            registros = payload
        out: list[dict] = []
        for r in registros:
            if not isinstance(r, dict):
                continue
            out.append({
                "razon_social": r.get("razon_social") or r.get("razonSocial") or "—",
                "matricula":    r.get("matricula") or "—",
                "estado":       r.get("estado_matricula") or r.get("estado") or "—",
                "camara":       r.get("camara_comercio") or r.get("camara") or "—",
                "nit":          r.get("nit") or r.get("identificacion") or "—",
            })
        return out
```

> **Nota de implementación:** `_API_URL` y los nombres de parámetros (`nit`, `razon_social`) son la mejor estimación del API público de RUES. Durante la ejecución, hacer UNA llamada real de verificación (ver Task 7, Step 1) y ajustar `_API_URL`/`_build_params`/`_parse` a la forma real. El contrato del conector (entrada `fetch(target, target_type)` → salida `data["expedientes"]`) no cambia; los tests usan respuestas mockeadas y siguen siendo válidos.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_opendata_connectors.py -k rues -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add modules/osint/connectors/rues.py tests/test_opendata_connectors.py
git commit -m "feat(osint): RuesConnector — consulta empresarial por documento/razon social"
```

---

## Task 5: Router — `_detect_type` con `name` y orquestación por tipo

**Files:**
- Modify: `modules/osint/opendata/routes.py` (reescritura completa)
- Test: `tests/test_opendata_routes.py`

- [ ] **Step 1: Actualizar/añadir tests del router**

En `tests/test_opendata_routes.py`:

(a) Reemplazar `test_opendata_detect_type_unknown` por:

```python
def test_opendata_detect_type_name():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("JUAN CARLOS PEREZ") == "name"


def test_opendata_detect_type_unknown():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("???") == "unknown"
```

(b) Reemplazar `test_opendata_lookup_document` por (ahora el router usa `_gather`):

```python
def test_opendata_lookup_document(app):
    simit_result = ConnectorResult(
        connector="simit", ok=True,
        data={"rows": [{"placa": "ABC123", "fecha": "2020-03-10", "valor": "390000",
                        "lugar": "Bogota", "estado": "Pendiente", "vigencia": "2020",
                        "identificacion": "12345678"}]},
        errors=[], metadata={"latency_ms": 50, "count": 1, "dataset": "rfag-apa4"},
    )
    rues_result = ConnectorResult(
        connector="rues", ok=True,
        data={"expedientes": [{"razon_social": "XYZ SAS", "matricula": "0001",
                               "estado": "ACTIVA", "camara": "BOGOTA", "nit": "12345678"}]},
        errors=[], metadata={"count": 1},
    )
    ctx = {"simit": simit_result, "rues": rues_result, "phone": None,
           "dork": ([], [])}
    with patch("modules.osint.opendata.routes._gather", return_value=ctx):
        client = _auth_client(app)
        resp = client.get("/osint/opendata/lookup?q=12345678")

    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    assert "ABC123" in body
    assert "XYZ SAS" in body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_opendata_routes.py -v`
Expected: FAIL (`_gather` no existe; `_detect_type("JUAN CARLOS PEREZ")` aún devuelve `unknown`).

- [ ] **Step 3: Reescribir `routes.py`**

Reemplazar el contenido completo de `modules/osint/opendata/routes.py` por:

```python
"""opendata/routes.py — Tab Datos Abiertos: SIMIT + RUES + Phone + dorking web."""
from __future__ import annotations

import re
from typing import Any

from flask import render_template, request

from modules.osint.auth import login_required
from modules.osint.connectors.base import ConnectorResult
from modules.osint.connectors.phone import PhoneConnector
from modules.osint.connectors.rues import RuesConnector
from modules.osint.connectors.simit import SimitConnector
from modules.osint.connectors.web_dork import run_dork
from modules.osint.opendata import opendata_bp

_PLATE_RE = re.compile(r"^[A-Za-z]{3}[0-9A-Za-z]{3}$")
_PHONE_RE = re.compile(r"^(\+57|57)?3\d{9}$")
_NAME_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÑáéíóúñ]+(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ]+)+$")

_SIMIT = SimitConnector()
_RUES = RuesConnector()
_PHONE = PhoneConnector()


def _detect_type(q: str) -> str:
    q = q.strip()
    if _PHONE_RE.match(q) or q.startswith("+"):
        return "phone"
    if _PLATE_RE.match(q):
        return "plate"
    if q.isdigit() and 6 <= len(q) <= 10:
        return "document"
    if _NAME_RE.match(q):
        return "name"
    return "unknown"


def _gather(q: str, target_type: str) -> dict[str, Any]:
    """Ejecuta los conectores aplicables al tipo y devuelve el contexto."""
    simit: ConnectorResult | None = None
    rues: ConnectorResult | None = None
    phone: ConnectorResult | None = None

    if target_type in ("plate", "document"):
        simit = _SIMIT.fetch(q, target_type=target_type)
    if target_type in ("document", "name"):
        rues = _RUES.fetch(q, target_type=target_type)
    if target_type == "phone":
        phone = _PHONE.fetch(q)

    dork: tuple[list[dict], list[str]] = ([], [])
    if target_type in ("plate", "document", "name", "unknown"):
        queries = [f'"{q}"']
        if target_type in ("document", "plate"):
            queries.append(f'"{q}" Colombia')
        dork = run_dork(queries, max_results=8)

    return {"simit": simit, "rues": rues, "phone": phone, "dork": dork}


@opendata_bp.route("/lookup")
@login_required
def lookup() -> Any:
    q = request.args.get("q", "").strip()

    def _render(**ctx: Any) -> Any:
        base = {
            "q": q, "target_type": "unknown", "simit": None, "rues": None,
            "phone": None, "dork_results": [], "errors": [],
            "sources_queried": 0, "findings_count": 0,
        }
        base.update(ctx)
        return render_template("osint/opendata_fragment.html", **base)

    if not q:
        return _render(errors=["No se proporcionó un término de búsqueda."])
    if len(q) > 100:
        return _render(errors=["Consulta demasiado larga (máximo 100 caracteres)."])

    target_type = _detect_type(q)
    ctx = _gather(q, target_type)
    simit, rues, phone = ctx["simit"], ctx["rues"], ctx["phone"]
    dork_results, dork_errors = ctx["dork"]

    errors: list[str] = []
    for r in (simit, rues, phone):
        if r:
            errors.extend(r.errors)
    errors.extend(dork_errors)

    sources = [r for r in (simit, rues, phone) if r is not None]
    sources_queried = len(sources) + (1 if dork_results or not sources else 0)
    findings_count = sum([
        len(simit.data.get("rows", [])) if simit and simit.ok else 0,
        len(rues.data.get("expedientes", [])) if rues and rues.ok else 0,
        1 if phone and phone.ok else 0,
        len(dork_results),
    ])

    return _render(
        target_type=target_type, simit=simit, rues=rues, phone=phone,
        dork_results=dork_results, errors=errors,
        sources_queried=sources_queried, findings_count=findings_count,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_opendata_routes.py -v`
Expected: PASS (todos). `test_opendata_lookup_no_query` y `test_opendata_lookup_redirects_unauthenticated` siguen pasando.

- [ ] **Step 5: Commit**

```bash
git add modules/osint/opendata/routes.py tests/test_opendata_routes.py
git commit -m "feat(osint): router opendata orquesta SIMIT+RUES+Phone+dork por tipo de termino"
```

---

## Task 6: Plantilla — columnas SIMIT reales, sección RUES, menciones web

**Files:**
- Modify: `templates/osint/opendata_fragment.html` (reescritura completa)

- [ ] **Step 1: Reescribir la plantilla**

Reemplazar el contenido completo de `templates/osint/opendata_fragment.html` por:

```html
<style>
.od-frag{font-family:'JetBrains Mono',monospace;color:#d0d8e8;font-size:.82rem}
.od-frag .summary-bar{display:flex;gap:.75rem;flex-wrap:wrap;align-items:center;background:#0d1a2e;border:1px solid #1e2d42;border-radius:4px;padding:.5rem .75rem;margin-bottom:1rem}
.od-frag .summary-stat{font-size:.78rem;color:#8ab4cc}
.od-frag .summary-stat strong{color:#4bc8a8}
.od-frag .source-badge{font-size:.7rem;padding:2px 8px;border-radius:3px;border:1px solid #2a4060;background:#091524;letter-spacing:.05em}
.od-frag .source-badge.ok{color:#4bc8a8;border-color:#1a4030}
.od-frag .source-badge.empty{color:#6b8aaa}
.od-frag .source-badge.warn{color:#f59e0b;border-color:#5c3a00}
.od-frag .section{margin-bottom:1.25rem;border-top:1px solid #1e2535;padding-top:.875rem}
.od-frag .section-hdr{display:flex;align-items:center;gap:.5rem;cursor:pointer;user-select:none;margin-bottom:.6rem}
.od-frag .section-tag{background:#0d1a2e;border:1px solid #2a4060;color:#4bc8a8;padding:2px 8px;border-radius:3px;font-size:.72rem;letter-spacing:.05em}
.od-frag .section-count{color:#6b8aaa;font-size:.72rem}
.od-frag .section-toggle{margin-left:auto;color:#4a5a6a;font-size:.75rem}
.od-frag .data-table{width:100%;border-collapse:collapse;margin-bottom:.75rem}
.od-frag .data-table th{color:#6b8aaa;font-weight:500;text-align:left;font-size:.75rem;padding:4px 8px;border-bottom:1px solid #1e2535}
.od-frag .data-table td{padding:4px 8px;border-bottom:1px solid #111d2e;vertical-align:top;font-size:.78rem}
.od-frag .table-wrap{overflow-x:auto;max-height:260px;overflow-y:auto}
.od-frag .kv-table td{padding:3px 8px;border-bottom:1px solid #111d2e;font-size:.78rem}
.od-frag .kv-table .k{color:#6b8aaa;width:130px;white-space:nowrap}
.od-frag .empty-note{color:#4a5a6a;font-size:.78rem;padding:.4rem 0}
.od-frag .error-block{background:#1a0a0a;border:1px solid #5c1a1a;border-radius:4px;padding:.5rem .75rem;margin-bottom:1rem}
.od-frag .error-line{color:#f87171;margin:2px 0;font-size:.78rem}
.od-frag .results-meta{margin-bottom:.5rem;font-size:.77rem;color:#6b8aaa}
</style>

<div class="od-frag">

  <div class="results-meta">
    Búsqueda: <strong>{{ q }}</strong> —
    Tipo detectado: <span style="color:#4bc8a8">{{ target_type }}</span>
  </div>

  {% if errors %}
  <div class="error-block">
    {% for err in errors %}<p class="error-line">⚠ {{ err }}</p>{% endfor %}
  </div>
  {% endif %}

  {% if q %}
  <div class="summary-bar">
    <span class="summary-stat">Fuentes consultadas: <strong>{{ sources_queried }}</strong></span>
    <span class="summary-stat">Hallazgos: <strong>{{ findings_count }}</strong></span>
    {% if simit %}
      {% if simit.ok %}<span class="source-badge ok">SIMIT ✓ ({{ simit.data.rows|length }})</span>
      {% else %}<span class="source-badge empty">SIMIT sin resultados</span>{% endif %}
    {% endif %}
    {% if rues %}
      {% if rues.ok %}<span class="source-badge ok">RUES ✓ ({{ rues.data.expedientes|length }})</span>
      {% else %}<span class="source-badge empty">RUES sin resultados</span>{% endif %}
    {% endif %}
    {% if phone %}
      {% if phone.ok %}<span class="source-badge ok">TEL ✓{% if phone.metadata.enriched %} +NumVerify{% endif %}</span>
      {% else %}<span class="source-badge empty">TEL sin resultados</span>{% endif %}
    {% endif %}
    {% if dork_results %}<span class="source-badge ok">WEB ✓ ({{ dork_results|length }})</span>{% endif %}
  </div>

  {% if simit %}
  <div class="section">
    <div class="section-hdr" onclick="odToggle('od-simit')">
      <span class="section-tag">SIMIT</span>
      <span>Infracciones de Tránsito</span>
      {% if simit.ok %}<span class="section-count">{{ simit.data.rows|length }} registro(s)</span>{% endif %}
      <span class="section-toggle" id="od-simit-icon">▼</span>
    </div>
    <div id="od-simit">
      {% if not simit.ok %}
        <p class="empty-note">Sin resultados en SIMIT para <em>{{ q }}</em>.</p>
      {% else %}
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                {% if target_type == 'document' %}<th>Identificación</th>{% endif %}
                <th>Placa</th><th>Fecha</th><th>Valor</th>
                <th>Estado</th><th>Lugar</th><th>Vigencia</th>
              </tr>
            </thead>
            <tbody>
              {% for row in simit.data.rows %}
              <tr>
                {% if target_type == 'document' %}<td>{{ row.identificacion or '—' }}</td>{% endif %}
                <td>{{ row.placa }}</td>
                <td>{{ row.fecha }}</td>
                <td>{{ row.valor }}</td>
                <td>{{ row.estado }}</td>
                <td>{{ row.lugar }}</td>
                <td>{{ row.vigencia }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        <div style="font-size:.72rem;color:#4a5a6a;margin-top:.25rem">
          Fuente: <a href="https://www.datos.gov.co/resource/{{ simit.metadata.dataset }}" target="_blank"
            rel="noopener" style="color:#4bc8a8">datos.gov.co/SIMIT</a>
          {% if simit.metadata.latency_ms %} — {{ simit.metadata.latency_ms }}ms{% endif %}
        </div>
      {% endif %}
    </div>
  </div>
  {% endif %}

  {% if rues %}
  <div class="section">
    <div class="section-hdr" onclick="odToggle('od-rues')">
      <span class="section-tag">RUES</span>
      <span>Actividad Empresarial</span>
      {% if rues.ok %}<span class="section-count">{{ rues.data.expedientes|length }} expediente(s)</span>{% endif %}
      <span class="section-toggle" id="od-rues-icon">▼</span>
    </div>
    <div id="od-rues">
      {% if not rues.ok %}
        <p class="empty-note">Sin actividad empresarial registrada en RUES para <em>{{ q }}</em>.</p>
      {% else %}
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th>Razón Social</th><th>Matrícula</th><th>Estado</th><th>Cámara</th><th>NIT/ID</th></tr>
            </thead>
            <tbody>
              {% for e in rues.data.expedientes %}
              <tr>
                <td>{{ e.razon_social }}</td><td>{{ e.matricula }}</td>
                <td>{{ e.estado }}</td><td>{{ e.camara }}</td><td>{{ e.nit }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        <div style="font-size:.72rem;color:#4a5a6a;margin-top:.25rem">
          Fuente: <a href="https://www.rues.org.co/" target="_blank" rel="noopener" style="color:#4bc8a8">RUES</a>
        </div>
      {% endif %}
    </div>
  </div>
  {% endif %}

  {% if phone %}
  <div class="section">
    <div class="section-hdr" onclick="odToggle('od-phone')">
      <span class="section-tag">TELÉFONO</span>
      <span>Información Telefónica</span>
      {% if phone.ok %}<span class="section-count">{{ phone.data.mentions_count }} mención(es)</span>{% endif %}
      <span class="section-toggle" id="od-phone-icon">▼</span>
    </div>
    <div id="od-phone">
      {% if not phone.ok %}
        <p class="empty-note">Sin resultados telefónicos para <em>{{ q }}</em>.</p>
      {% else %}
        <table class="kv-table">
          <tbody>
            <tr><td class="k">Número internacional</td><td>{{ phone.data.international or '—' }}</td></tr>
            <tr><td class="k">Válido</td><td>{{ 'Sí' if phone.data.valid else 'No' }}</td></tr>
            <tr><td class="k">Operador</td><td>{{ phone.data.carrier or '—' }}</td></tr>
            <tr><td class="k">Tipo de línea</td><td>{{ phone.data.line_type or '—' }}</td></tr>
            <tr><td class="k">País</td><td>{{ phone.data.country or '—' }}</td></tr>
            <tr><td class="k">Ubicación</td><td>{{ phone.data.location or '—' }}</td></tr>
            {% if phone.data.timezone %}
            <tr><td class="k">Zona horaria</td><td>{{ phone.data.timezone | join(', ') }}</td></tr>
            {% endif %}
            {% if phone.metadata.enriched %}
            <tr><td class="k">Fuente</td><td><span style="color:#4bc8a8">NumVerify ✓</span></td></tr>
            {% endif %}
          </tbody>
        </table>
        {% if phone.data.dork_results %}
        <div style="margin-top:.75rem">
          <div style="font-size:.75rem;color:#6b8aaa;margin-bottom:.4rem">Menciones web ({{ phone.data.mentions_count }})</div>
          {% for r in phone.data.dork_results[:5] %}
          <div style="margin-bottom:.5rem;font-size:.77rem">
            <a href="{{ r.url }}" target="_blank" rel="noopener" style="color:#4bc8a8;word-break:break-all">{{ r.title or r.url }}</a>
            {% if r.snippet %}<div style="color:#8ab4cc;margin-top:2px">{{ r.snippet }}</div>{% endif %}
          </div>
          {% endfor %}
        </div>
        {% endif %}
      {% endif %}
    </div>
  </div>
  {% endif %}

  {% if dork_results %}
  <div class="section">
    <div class="section-hdr" onclick="odToggle('od-web')">
      <span class="section-tag">WEB</span>
      <span>Menciones en la Web Abierta</span>
      <span class="section-count">{{ dork_results|length }} resultado(s)</span>
      <span class="section-toggle" id="od-web-icon">▼</span>
    </div>
    <div id="od-web">
      {% for r in dork_results[:10] %}
      <div style="margin-bottom:.5rem;font-size:.77rem">
        <a href="{{ r.url }}" target="_blank" rel="noopener" style="color:#4bc8a8;word-break:break-all">{{ r.title or r.url }}</a>
        {% if r.snippet %}<div style="color:#8ab4cc;margin-top:2px">{{ r.snippet }}</div>{% endif %}
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}

  {% endif %}

</div>

<script>
function odToggle(id) {
  var el = document.getElementById(id);
  var icon = document.getElementById(id + '-icon');
  if (!el) return;
  var hidden = el.style.display === 'none';
  el.style.display = hidden ? '' : 'none';
  if (icon) icon.textContent = hidden ? '▼' : '▶';
}
</script>
```

- [ ] **Step 2: Run the full opendata test suite**

Run: `python -m pytest tests/test_opendata_routes.py tests/test_opendata_connectors.py -v`
Expected: PASS (todos). Las aserciones `"ABC123"` y `"XYZ SAS"` del router validan que SIMIT y RUES rendericen.

- [ ] **Step 3: Commit**

```bash
git add templates/osint/opendata_fragment.html
git commit -m "feat(osint): plantilla opendata con SIMIT corregido, RUES y menciones web"
```

---

## Task 7: Verificación manual end-to-end

**Files:** ninguno (verificación en vivo)

- [ ] **Step 1: Verificar el API real de RUES**

Hacer una llamada real para confirmar endpoint/parámetros (ver nota en Task 4, Step 3):

```bash
curl -s "https://ruesapi.rues.org.co/api/v1/expedientes/buscar?nit=900123456" | head -c 500
```

Si el endpoint no responde como se espera, abrir DevTools en rues.org.co → pestaña Network al hacer una búsqueda real, identificar el endpoint vigente y actualizar `modules/osint/connectors/rues.py` (`_API_URL`, `_build_params`, `_parse`). Re-correr `python -m pytest tests/test_opendata_connectors.py -k rues -v`. Commit si hubo ajuste:

```bash
git add modules/osint/connectors/rues.py
git commit -m "fix(osint): ajustar endpoint RUES al API vigente"
```

- [ ] **Step 2: Arrancar la app y probar el tab**

Run: `python app.py` (o el comando de arranque del proyecto) y abrir el tab Datos Abiertos. Probar:
- Una placa real (ej. de una multa conocida) → ver filas SIMIT con valor/estado reales (no guiones).
- Una cédula → ver RUES y/o comparendos y/o menciones web sin error 500.
- Un teléfono `+573xxxxxxxxx` → comportamiento idéntico al actual.

Expected: cada sección renderiza; fuentes que fallan muestran aviso sin tumbar la página.

- [ ] **Step 3: Suite completa**

Run: `python -m pytest tests/ -v`
Expected: sin regresiones.

---

## Self-Review

- **Cobertura del spec:** §3 detección/orquestación → Task 5; §4.1 SIMIT → Task 3; §4.2 RUES → Task 4; §4.3 web_dork → Task 1; §4.4 phone → Task 2; §4.5 router → Task 5; §4.6 plantilla → Task 6; §5 errores → manejo en cada conector + agregación en router; §6 deps → ninguna nueva (verificado en requirements.txt); §7 testing → tests en Tasks 1-6; §8 criterios → Task 7.
- **Sin placeholders:** todo el código está completo; la única incógnita externa (endpoint RUES) tiene contrato fijo y test mockeado, con verificación explícita en Task 7, Step 1.
- **Consistencia de tipos:** SIMIT `data["rows"]` (forma normalizada con `placa/fecha/valor/lugar/estado/vigencia/identificacion`) usada igual en Task 3, 5 (test) y 6 (plantilla). RUES `data["expedientes"]` (con `razon_social/matricula/estado/camara/nit`) consistente en Task 4, 5, 6. `run_dork(...) -> (results, errors)` con `results[*] = {title,url,snippet}` consistente en Task 1, 2, 5, 6.
