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
