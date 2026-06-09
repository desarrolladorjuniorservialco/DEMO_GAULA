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

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        target_type: str = kwargs.get("target_type", "unknown")
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
        safe = target.replace("'", "''")
        if target_type == "plate":
            return f"upper(placa)=upper('{safe}')"
        if target_type == "document":
            return f"numero_identificacion='{safe}'"
        if _PLATE_RE.match(target):
            return f"upper(placa)=upper('{safe}')"
        if target.isdigit():
            return f"numero_identificacion='{safe}'"
        return f"upper(nombre) like upper('%{safe}%')"
