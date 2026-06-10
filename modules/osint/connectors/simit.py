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
