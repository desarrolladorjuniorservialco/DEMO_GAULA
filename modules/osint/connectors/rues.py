"""connectors/rues.py — Registro Único Empresarial y Social (RUES).

Consulta pública por documento (NIT/cédula) o razón social usando el dataset
abierto de RUES en datos.gov.co (Socrata). Devuelve expedientes mercantiles:
razón social, matrícula, estado, cámara de comercio.

Fuente estable y legal (datos.gov.co), consultable por número de identificación
—incluida cédula de ciudadanía de comerciantes— sin token ni captcha. Si la API
falla, el conector degrada a ok=False sin propagar excepción.
"""
from __future__ import annotations

import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_API_URL = "https://www.datos.gov.co/resource/c82u-588k.json"
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

        where = self._build_where(target, target_type)
        params: dict[str, Any] = {"$where": where, "$limit": 50}
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

    def _build_where(self, target: str, target_type: str) -> str:
        safe = target.replace("'", "''")
        if target_type == "name":
            return f"upper(razon_social) like upper('%{safe}%')"
        return f"numero_identificacion='{safe}'"

    @staticmethod
    def _estado(r: dict) -> str:
        cancel = (r.get("fecha_cancelacion") or "").strip()
        if cancel and cancel not in ("00000000", "0", "99991231"):
            return "CANCELADA"
        return "ACTIVA"

    @classmethod
    def _parse(cls, payload: Any) -> list[dict]:
        registros: list = []
        if isinstance(payload, dict):
            registros = payload.get("registros") or payload.get("data") or []
            if isinstance(registros, dict):
                registros = [registros]
        elif isinstance(payload, list):
            registros = payload
        out: list[dict] = []
        for r in registros:
            if not isinstance(r, dict):
                continue
            out.append({
                "razon_social": r.get("razon_social") or "—",
                "matricula":    r.get("matricula") or "—",
                "estado":       r.get("estado") or cls._estado(r),
                "camara":       r.get("camara_comercio") or r.get("camara") or "—",
                "nit":          r.get("nit") or r.get("numero_identificacion") or "—",
            })
        return out
