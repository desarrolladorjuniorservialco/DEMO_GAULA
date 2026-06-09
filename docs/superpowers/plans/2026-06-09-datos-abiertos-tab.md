# Tab "Datos Abiertos" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir un cuarto tab "Datos Abiertos" al módulo OSINT con búsqueda universal que consulta SIMIT (datos.gov.co) y Truecaller en paralelo.

**Architecture:** Dos nuevos conectores (`SimitConnector`, `TruecallerConnector`) siguiendo `BaseConnector`. Un blueprint `opendata_bp` con un endpoint `/osint/opendata/lookup` que detecta el tipo de dato, usa `OsintOrchestrator` y renderiza un fragmento HTML con resumen unificado + detalle por fuente expandible.

**Tech Stack:** Python 3.11, Flask, Requests, Jinja2, pytest, datos.gov.co Socrata API, Truecaller API v4.

---

## Mapa de archivos

| Acción | Archivo |
|---|---|
| Crear | `modules/osint/connectors/simit.py` |
| Crear | `modules/osint/connectors/truecaller.py` |
| Crear | `modules/osint/opendata/__init__.py` |
| Crear | `modules/osint/opendata/routes.py` |
| Crear | `templates/osint/opendata_fragment.html` |
| Crear | `tests/test_opendata_connectors.py` |
| Crear | `tests/test_opendata_routes.py` |
| Modificar | `modules/__init__.py` |
| Modificar | `templates/casos/console.html` |

---

## Task 1: SimitConnector

**Files:**
- Create: `modules/osint/connectors/simit.py`
- Test: `tests/test_opendata_connectors.py`

- [ ] **Step 1: Escribir el test fallido**

```python
# tests/test_opendata_connectors.py
import pytest
from unittest.mock import patch, MagicMock
from modules.osint.connectors.simit import SimitConnector


def test_simit_connector_name():
    c = SimitConnector()
    assert c.name == "simit"


def test_simit_supported_types():
    c = SimitConnector()
    assert "document" in c.supported_target_types
    assert "plate" in c.supported_target_types
    assert "unknown" in c.supported_target_types


def test_simit_fetch_document_ok():
    c = SimitConnector()
    mock_rows = [
        {
            "nombre": "JUAN PEREZ",
            "numero_identificacion": "12345678",
            "placa": "ABC123",
            "valor_a_pagar": "150000",
            "estado": "PENDIENTE",
            "fecha_infraccion": "2024-01-15",
            "municipio": "BOGOTA",
        }
    ]
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_rows)
        result = c.fetch("12345678", target_type="document")

    assert result.ok is True
    assert result.connector == "simit"
    assert len(result.data["rows"]) == 1
    assert result.data["rows"][0]["nombre"] == "JUAN PEREZ"
    assert result.errors == []


def test_simit_fetch_no_results():
    c = SimitConnector()
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
        result = c.fetch("99999999", target_type="document")

    assert result.ok is False
    assert result.data["rows"] == []


def test_simit_fetch_network_error():
    import requests as req
    c = SimitConnector()
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.side_effect = req.RequestException("timeout")
        result = c.fetch("12345678", target_type="document")

    assert result.ok is False
    assert len(result.errors) == 1
    assert "timeout" in result.errors[0]
```

- [ ] **Step 2: Ejecutar el test — verificar que falla**

```
pytest tests/test_opendata_connectors.py -v
```
Esperado: `ModuleNotFoundError: No module named 'modules.osint.connectors.simit'`

- [ ] **Step 3: Crear `modules/osint/connectors/simit.py`**

```python
"""connectors/simit.py — SIMIT infracciones de tránsito (datos.gov.co)."""
from __future__ import annotations

import re
import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_API_URL = "https://www.datos.gov.co/resource/72nf-y4v3.json"
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

    def fetch(self, target: str, target_type: str = "unknown", **kwargs: Any) -> ConnectorResult:
        t0 = time.monotonic()
        errors: list[str] = []
        rows: list[dict] = []

        where = self._build_where(target, target_type)
        params: dict[str, Any] = {"$where": where, "$limit": 50}

        try:
            resp = requests.get(_API_URL, headers=_HEADERS, params=params, timeout=self.timeout_seconds)
            resp.raise_for_status()
            rows = resp.json() or []
        except requests.RequestException as exc:
            errors.append(f"simit: {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=len(rows) > 0,
            data={"rows": rows},
            errors=errors,
            metadata={"latency_ms": int((time.monotonic() - t0) * 1000), "count": len(rows)},
        )

    def _build_where(self, target: str, target_type: str) -> str:
        if target_type == "plate" or _PLATE_RE.match(target):
            return f"upper(placa)=upper('{target}')"
        if target_type == "document" or target.isdigit():
            return f"numero_identificacion='{target}'"
        safe = target.replace("'", "''")
        return f"upper(nombre) like upper('%{safe}%')"
```

- [ ] **Step 4: Ejecutar el test — verificar que pasa**

```
pytest tests/test_opendata_connectors.py -v
```
Esperado: 5 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add modules/osint/connectors/simit.py tests/test_opendata_connectors.py
git commit -m "feat(osint): SimitConnector datos.gov.co"
```

---

## Task 2: TruecallerConnector

**Files:**
- Modify: `tests/test_opendata_connectors.py` (añadir tests al final)
- Create: `modules/osint/connectors/truecaller.py`

- [ ] **Step 1: Añadir tests de Truecaller al final de `tests/test_opendata_connectors.py`**

```python
import os
from modules.osint.connectors.truecaller import TruecallerConnector


def test_truecaller_connector_name():
    c = TruecallerConnector()
    assert c.name == "truecaller"


def test_truecaller_supported_types():
    c = TruecallerConnector()
    assert "phone" in c.supported_target_types


def test_truecaller_unconfigured():
    c = TruecallerConnector()
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("TRUECALLER_API_KEY", None)
        result = c.fetch("+573001234567", target_type="phone")

    assert result.ok is False
    assert result.metadata.get("status") == "unconfigured"
    assert result.errors == []


def test_truecaller_fetch_ok():
    c = TruecallerConnector()
    mock_resp = {
        "data": [
            {
                "name": {"first": "CARLOS", "last": "GOMEZ"},
                "phones": [{"e164Format": "+573001234567", "numberType": "MOBILE",
                             "carrier": "CLARO", "countryCode": "CO"}],
                "addresses": [{"countryCode": "CO"}],
                "spamInfo": {"isSpam": False, "spamScore": 0},
            }
        ]
    }
    with patch("modules.osint.connectors.truecaller.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_resp)
        with patch.dict(os.environ, {"TRUECALLER_API_KEY": "test-key"}):
            result = c.fetch("+573001234567", target_type="phone")

    assert result.ok is True
    assert result.data["nombre"] == "CARLOS GOMEZ"
    assert result.data["operador"] == "CLARO"
    assert result.errors == []


def test_truecaller_fetch_not_found():
    c = TruecallerConnector()
    with patch("modules.osint.connectors.truecaller.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"data": []})
        with patch.dict(os.environ, {"TRUECALLER_API_KEY": "test-key"}):
            result = c.fetch("+573009999999", target_type="phone")

    assert result.ok is False
    assert result.data == {}
```

- [ ] **Step 2: Ejecutar los nuevos tests — verificar que fallan**

```
pytest tests/test_opendata_connectors.py::test_truecaller_connector_name -v
```
Esperado: `ModuleNotFoundError: No module named 'modules.osint.connectors.truecaller'`

- [ ] **Step 3: Crear `modules/osint/connectors/truecaller.py`**

```python
"""connectors/truecaller.py — Truecaller API v4."""
from __future__ import annotations

import os
import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_BASE_URL = "https://api4.truecaller.com/v1/details"
_HEADERS = {"Content-Type": "application/json", "User-Agent": "NEXO-147-OSINT/1.0"}


class TruecallerConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "truecaller"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"phone"})

    @property
    def needs_api_key(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> float:
        return 12.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        api_key = os.getenv("TRUECALLER_API_KEY", "").strip()
        if not api_key:
            return ConnectorResult(
                connector=self.name,
                ok=False,
                data={},
                errors=[],
                metadata={"status": "unconfigured"},
            )

        t0 = time.monotonic()
        errors: list[str] = []
        data: dict[str, Any] = {}

        try:
            resp = requests.get(
                _BASE_URL,
                headers={**_HEADERS, "Authorization": f"Bearer {api_key}"},
                params={"q": target, "type": 4, "countryCode": "CO"},
                timeout=self.timeout_seconds,
            )
            if resp.status_code == 401:
                errors.append("truecaller: API key inválida (401).")
            elif resp.status_code == 429:
                errors.append("truecaller: rate limit alcanzado (429).")
            else:
                resp.raise_for_status()
                items = resp.json().get("data", [])
                if items:
                    item = items[0]
                    phones = item.get("phones", [{}])
                    phone_info = phones[0] if phones else {}
                    spam = item.get("spamInfo", {})
                    name_obj = item.get("name", {})
                    full_name = f"{name_obj.get('first', '')} {name_obj.get('last', '')}".strip()
                    data = {
                        "nombre": full_name or "—",
                        "operador": phone_info.get("carrier", "—"),
                        "pais": phone_info.get("countryCode", "—"),
                        "tipo_linea": phone_info.get("numberType", "—"),
                        "spam_score": spam.get("spamScore", 0),
                        "es_spam": spam.get("isSpam", False),
                    }
        except requests.RequestException as exc:
            errors.append(f"truecaller: {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=bool(data),
            data=data,
            errors=errors,
            metadata={
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "status": "ok" if data else "not_found",
            },
        )
```

- [ ] **Step 4: Ejecutar todos los tests del archivo — verificar que pasan**

```
pytest tests/test_opendata_connectors.py -v
```
Esperado: 10 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add modules/osint/connectors/truecaller.py tests/test_opendata_connectors.py
git commit -m "feat(osint): TruecallerConnector con manejo de clave no configurada"
```

---

## Task 3: Blueprint opendata + ruta

**Files:**
- Create: `modules/osint/opendata/__init__.py`
- Create: `modules/osint/opendata/routes.py`
- Create: `tests/test_opendata_routes.py`

- [ ] **Step 1: Escribir los tests de la ruta**

```python
# tests/test_opendata_routes.py
import pytest
from unittest.mock import patch, MagicMock
from modules.osint.connectors.base import ConnectorResult


def _auth_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analista"
        sess["role"] = "analista"
        sess["name"] = "Analista Test"
    return client


def test_opendata_lookup_no_query(app):
    client = _auth_client(app)
    resp = client.get("/osint/opendata/lookup")
    assert resp.status_code == 200
    assert b"No se proporcion" in resp.data


def test_opendata_lookup_redirects_unauthenticated(app):
    client = app.test_client()
    resp = client.get("/osint/opendata/lookup?q=123456")
    assert resp.status_code == 302


def test_opendata_lookup_document(app):
    simit_result = ConnectorResult(
        connector="simit", ok=True,
        data={"rows": [{"nombre": "JUAN", "placa": "ABC123", "valor_a_pagar": "100000",
                        "estado": "PENDIENTE", "fecha_infraccion": "2024-01-01",
                        "municipio": "BOGOTA", "numero_identificacion": "12345678"}]},
        errors=[], metadata={"latency_ms": 50, "count": 1},
    )
    tc_result = ConnectorResult(
        connector="truecaller", ok=False, data={}, errors=[],
        metadata={"status": "unconfigured"},
    )
    with patch("modules.osint.opendata.routes._run_connectors",
               return_value={"simit": simit_result, "truecaller": tc_result}):
        client = _auth_client(app)
        resp = client.get("/osint/opendata/lookup?q=12345678")

    assert resp.status_code == 200
    assert b"JUAN" in resp.data


def test_opendata_detect_type_document():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("12345678") == "document"
    assert _detect_type("1234567") == "document"
    assert _detect_type("123456789012") == "unknown"


def test_opendata_detect_type_plate():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("ABC123") == "plate"
    assert _detect_type("abc123") == "plate"


def test_opendata_detect_type_phone():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("+573001234567") == "phone"
    assert _detect_type("3001234567") == "phone"


def test_opendata_detect_type_unknown():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("JUAN CARLOS PEREZ") == "unknown"
```

- [ ] **Step 2: Ejecutar los tests — verificar que fallan**

```
pytest tests/test_opendata_routes.py -v
```
Esperado: `ModuleNotFoundError: No module named 'modules.osint.opendata'`

- [ ] **Step 3: Crear `modules/osint/opendata/__init__.py`**

```python
from flask import Blueprint

opendata_bp = Blueprint("opendata_osint", __name__)

from modules.osint.opendata import routes  # noqa: E402, F401
```

- [ ] **Step 4: Crear `modules/osint/opendata/routes.py`**

```python
"""opendata/routes.py — Tab Datos Abiertos: búsqueda universal SIMIT + Truecaller."""
from __future__ import annotations

import re
from typing import Any

from flask import render_template, request, session

from modules.osint.auth import login_required
from modules.osint.connectors.base import ConnectorResult
from modules.osint.connectors.simit import SimitConnector
from modules.osint.connectors.truecaller import TruecallerConnector
from modules.osint.engines.orchestration import OsintOrchestrator
from modules.osint.opendata import opendata_bp

_PLATE_RE = re.compile(r"^[A-Za-z]{3}[0-9A-Za-z]{3}$")
_PHONE_RE = re.compile(r"^(\+57|57)?3\d{9}$")

_ORCHESTRATOR = OsintOrchestrator(
    connectors=[SimitConnector(), TruecallerConnector()],
    max_workers=2,
    timeout=20.0,
)


def _detect_type(q: str) -> str:
    q = q.strip()
    if _PHONE_RE.match(q) or q.startswith("+"):
        return "phone"
    if _PLATE_RE.match(q):
        return "plate"
    if q.isdigit() and 6 <= len(q) <= 10:
        return "document"
    return "unknown"


def _run_connectors(q: str, target_type: str) -> dict[str, ConnectorResult]:
    results = _ORCHESTRATOR.run(
        target=q,
        target_type=target_type,
        extra_kwargs={
            "simit": {"target_type": target_type},
        },
    )
    if "truecaller" not in results:
        results["truecaller"] = ConnectorResult(
            connector="truecaller", ok=False, data={}, errors=[],
            metadata={"status": "unconfigured"},
        )
    return results


@opendata_bp.route("/lookup")
@login_required
def lookup() -> Any:
    q = request.args.get("q", "").strip()

    if not q:
        return render_template(
            "osint/opendata_fragment.html",
            q=q,
            target_type="unknown",
            simit=None,
            truecaller=None,
            errors=["No se proporcionó un término de búsqueda."],
            sources_queried=0,
            findings_count=0,
        )

    target_type = _detect_type(q)
    results = _run_connectors(q, target_type)

    simit = results.get("simit")
    truecaller = results.get("truecaller")

    all_errors: list[str] = []
    if simit:
        all_errors.extend(simit.errors)
    if truecaller:
        all_errors.extend(truecaller.errors)

    sources_queried = sum(
        1 for r in [simit, truecaller]
        if r and r.metadata.get("status") != "unconfigured"
    )
    findings_count = sum([
        len(simit.data.get("rows", [])) if simit and simit.ok else 0,
        1 if truecaller and truecaller.ok else 0,
    ])

    return render_template(
        "osint/opendata_fragment.html",
        q=q,
        target_type=target_type,
        simit=simit,
        truecaller=truecaller,
        errors=all_errors,
        sources_queried=sources_queried,
        findings_count=findings_count,
    )
```

- [ ] **Step 5: Ejecutar los tests — verificar que pasan**

```
pytest tests/test_opendata_routes.py -v
```
Esperado: 7 tests PASSED

- [ ] **Step 6: Commit**

```bash
git add modules/osint/opendata/__init__.py modules/osint/opendata/routes.py tests/test_opendata_routes.py
git commit -m "feat(osint): blueprint opendata + endpoint /osint/opendata/lookup"
```

---

## Task 4: Template opendata_fragment.html

**Files:**
- Create: `templates/osint/opendata_fragment.html`

- [ ] **Step 1: Crear `templates/osint/opendata_fragment.html`**

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
.od-frag .warn-banner{background:#1a1200;border:1px solid #5c3a00;border-radius:4px;padding:.45rem .75rem;margin-bottom:.75rem;color:#f59e0b;font-size:.77rem}
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
  <!-- Resumen unificado -->
  <div class="summary-bar">
    <span class="summary-stat">Fuentes consultadas: <strong>{{ sources_queried }}</strong></span>
    <span class="summary-stat">Hallazgos: <strong>{{ findings_count }}</strong></span>
    {% if simit %}
      {% if simit.metadata.status == 'unconfigured' %}
        <span class="source-badge warn">SIMIT sin config</span>
      {% elif simit.ok %}
        <span class="source-badge ok">SIMIT ✓ ({{ simit.data.rows|length }})</span>
      {% else %}
        <span class="source-badge empty">SIMIT sin resultados</span>
      {% endif %}
    {% endif %}
    {% if truecaller %}
      {% if truecaller.metadata.status == 'unconfigured' %}
        <span class="source-badge warn">Truecaller sin config</span>
      {% elif truecaller.ok %}
        <span class="source-badge ok">Truecaller ✓</span>
      {% else %}
        <span class="source-badge empty">Truecaller sin resultados</span>
      {% endif %}
    {% endif %}
  </div>

  <!-- Sección SIMIT -->
  {% if simit %}
  <div class="section">
    <div class="section-hdr" onclick="odToggle('od-simit')">
      <span class="section-tag">SIMIT</span>
      <span>Infracciones de Tránsito</span>
      {% if simit.ok %}
        <span class="section-count">{{ simit.data.rows|length }} registro(s)</span>
      {% endif %}
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
                <th>Nombre</th><th>Identificación</th><th>Placa</th>
                <th>Valor</th><th>Estado</th><th>Fecha</th><th>Municipio</th>
              </tr>
            </thead>
            <tbody>
              {% for row in simit.data.rows %}
              <tr>
                <td>{{ row.nombre or '—' }}</td>
                <td>{{ row.numero_identificacion or '—' }}</td>
                <td>{{ row.placa or '—' }}</td>
                <td>{{ row.valor_a_pagar or '—' }}</td>
                <td>{{ row.estado or '—' }}</td>
                <td>{{ (row.fecha_infraccion or '')[:10] or '—' }}</td>
                <td>{{ row.municipio or '—' }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        <div style="font-size:.72rem;color:#4a5a6a;margin-top:.25rem">
          Fuente: <a href="https://www.datos.gov.co/resource/72nf-y4v3" target="_blank"
            rel="noopener" style="color:#4bc8a8">datos.gov.co/SIMIT</a>
          {% if simit.metadata.latency_ms %} — {{ simit.metadata.latency_ms }}ms{% endif %}
        </div>
      {% endif %}
    </div>
  </div>
  {% endif %}

  <!-- Sección Truecaller -->
  {% if truecaller %}
  <div class="section">
    <div class="section-hdr" onclick="odToggle('od-tc')">
      <span class="section-tag">TRUECALLER</span>
      <span>Información Telefónica</span>
      <span class="section-toggle" id="od-tc-icon">▼</span>
    </div>
    <div id="od-tc">
      {% if truecaller.metadata.status == 'unconfigured' %}
        <div class="warn-banner">
          ⚠ Truecaller no está configurado. Define
          <code>TRUECALLER_API_KEY</code> en el entorno para habilitar este conector.
        </div>
      {% elif not truecaller.ok %}
        <p class="empty-note">Sin resultados en Truecaller para <em>{{ q }}</em>.</p>
      {% else %}
        <table class="kv-table">
          <tbody>
            <tr><td class="k">Nombre registrado</td><td>{{ truecaller.data.nombre or '—' }}</td></tr>
            <tr><td class="k">Operador</td><td>{{ truecaller.data.operador or '—' }}</td></tr>
            <tr><td class="k">País</td><td>{{ truecaller.data.pais or '—' }}</td></tr>
            <tr><td class="k">Tipo de línea</td><td>{{ truecaller.data.tipo_linea or '—' }}</td></tr>
            <tr><td class="k">Spam score</td><td>{{ truecaller.data.spam_score }}</td></tr>
            <tr><td class="k">¿Es spam?</td><td>{{ 'Sí' if truecaller.data.es_spam else 'No' }}</td></tr>
          </tbody>
        </table>
        {% if truecaller.metadata.latency_ms %}
          <div style="font-size:.72rem;color:#4a5a6a;margin-top:.25rem">{{ truecaller.metadata.latency_ms }}ms</div>
        {% endif %}
      {% endif %}
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

- [ ] **Step 2: Verificar que la app arranca sin errores**

```
flask run --debug
```
Esperado: inicia sin errores de template.

- [ ] **Step 3: Commit**

```bash
git add templates/osint/opendata_fragment.html
git commit -m "feat(osint): template opendata_fragment.html"
```

---

## Task 5: Registrar blueprint en modules/__init__.py

**Files:**
- Modify: `modules/__init__.py`

- [ ] **Step 1: Añadir import y registro**

En `modules/__init__.py`, dentro de `_register_blueprints`, añadir estas dos líneas:

```python
# En el bloque de imports — después de "from modules.osint.watchlists import watchlists_osint_bp":
from modules.osint.opendata   import opendata_bp

# En el bloque de register_blueprint — después de "app.register_blueprint(watchlists_osint_bp, ...)":
app.register_blueprint(opendata_bp, url_prefix="/osint/opendata")
```

- [ ] **Step 2: Verificar que el endpoint existe**

```
flask routes | findstr opendata
```
Esperado: `opendata_osint.lookup   GET   /osint/opendata/lookup`

- [ ] **Step 3: Ejecutar todos los tests**

```
pytest tests/ -v
```
Esperado: todos en verde.

- [ ] **Step 4: Commit**

```bash
git add modules/__init__.py
git commit -m "feat(osint): registrar opendata_bp en la app"
```

---

## Task 6: Añadir Tab en console.html

**Files:**
- Modify: `templates/casos/console.html`

- [ ] **Step 1: Añadir botón del tab**

Localizar la línea (aprox. 801) con el botón `data-tab="graph"`:
```html
<button class="osint-tab-btn btn btn-secondary-tactical" data-tab="graph" onclick="osintSwitchTab('graph')">Grafo de Relaciones ...
```

Añadir inmediatamente después, antes del `</div>` que cierra `.osint-tabs`:
```html
<button class="osint-tab-btn btn btn-secondary-tactical" data-tab="opendata" onclick="osintSwitchTab('opendata')">Datos Abiertos</button>
```

- [ ] **Step 2: Añadir el panel del tab**

Después del cierre del panel `id="osint-tab-graph"`, añadir:

```html
<!-- Tab: Datos Abiertos -->
<div class="osint-tab-pane" id="osint-tab-opendata" style="display:none">
  <div class="dashboard-card double-bezel">
    <div class="inner-core">
      <h3>Datos Abiertos</h3>
      <p class="helper-text-mono">Consulta universal en fuentes gubernamentales. Ingresa cédula, nombre, placa o teléfono.</p>
      <div style="display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin-bottom:.75rem">
        <input type="text" id="osint-opendata-q" class="search-input-tactical"
               placeholder="cédula, nombre, placa o teléfono..."
               style="flex:1;min-width:150px"
               onkeydown="if(event.key==='Enter') osintFetchOpendata()">
        <span style="font-size:.73rem;font-family:'JetBrains Mono',monospace;color:#4f8a68;padding:.3rem .6rem;border:1px solid rgba(79,138,104,0.3);border-radius:4px;white-space:nowrap;letter-spacing:.04em;">▣ DATOS ABIERTOS</span>
        <button class="btn btn-primary-tactical" onclick="osintFetchOpendata()">CONSULTAR</button>
      </div>
      <div id="osint-opendata-spinner" style="display:none;color:#4f8a68;font-size:.8rem;margin-bottom:.5rem">⟳ Consultando fuentes...</div>
      <div id="osint-opendata-results" style="max-height:500px;overflow-y:auto"></div>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Añadir función JS `osintFetchOpendata`**

En el bloque `<script>` de console.html, localizar la función `osintFetchSocial` y añadir después:

```javascript
function osintFetchOpendata() {
  var q = document.getElementById('osint-opendata-q').value.trim();
  if (!q) return;
  var spinner = document.getElementById('osint-opendata-spinner');
  var results = document.getElementById('osint-opendata-results');
  spinner.style.display = 'block';
  results.innerHTML = '';
  var casoId = document.querySelector('[data-caso-id]')?.dataset?.casoId || '';
  fetch('/osint/opendata/lookup?q=' + encodeURIComponent(q) + (casoId ? '&caso_id=' + casoId : ''))
    .then(function(r) { return r.text(); })
    .then(function(html) {
      spinner.style.display = 'none';
      results.innerHTML = html;
    })
    .catch(function(err) {
      spinner.style.display = 'none';
      results.innerHTML = '<p style="color:#f87171;font-size:.8rem">Error: ' + err + '</p>';
    });
}
```

- [ ] **Step 4: Verificar que `osintSwitchTab` soporta el nuevo tab**

Buscar `function osintSwitchTab` en console.html. Si itera por clase `.osint-tab-pane` y `.osint-tab-btn`, el nuevo tab funciona sin cambios. Si usa una lista fija de nombres de tab, añadir `'opendata'` a esa lista.

- [ ] **Step 5: Probar en el navegador**

```
flask run --debug
```
1. Ir a la consola de un caso → clic en "Datos Abiertos"
2. Ingresar una cédula (ej. `12345678`) → clic CONSULTAR
3. Verificar: spinner aparece y desaparece, resumen unificado y sección SIMIT visible
4. Ingresar un número de teléfono (ej. `3001234567`) → verificar sección Truecaller con aviso de config

- [ ] **Step 6: Commit**

```bash
git add templates/casos/console.html
git commit -m "feat(osint): tab Datos Abiertos en console.html (SIMIT + Truecaller)"
```

---

## Verificación final

- [ ] **Suite completa**

```
pytest tests/ -v
```
Esperado: todos en verde incluyendo `test_opendata_connectors.py` y `test_opendata_routes.py`.

- [ ] **Smoke test manual**

1. `flask run`
2. Consola de un caso → tab "Datos Abiertos"
3. Búsqueda por cédula → tabla SIMIT + aviso Truecaller sin config
4. Búsqueda por teléfono → sección Truecaller activa (o aviso de API key)
5. Búsqueda por nombre → búsqueda `like` en SIMIT
