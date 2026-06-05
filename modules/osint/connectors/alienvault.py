"""connectors/alienvault.py — AlienVault OTX connector (API key opcional)."""
from __future__ import annotations

import os
import re
import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_BASE = "https://otx.alienvault.com/api/v1/indicators"
_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def _indicator_type(target: str) -> str:
    if _IP_RE.match(target):
        return "IPv4"
    if _EMAIL_RE.match(target):
        return "email"
    if "." in target:
        return "domain"
    return "hostname"


class AlienVaultConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "alienvault"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"ip", "domain", "email", "username"})

    @property
    def timeout_seconds(self) -> float:
        return 12.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        errors: list[str] = []
        t0 = time.monotonic()
        api_key = kwargs.get("api_key") or os.environ.get("OTX_API_KEY", "")
        headers: dict[str, str] = {"User-Agent": "NEXO-147-OSINT/1.0"}
        if api_key:
            headers["X-OTX-API-KEY"] = api_key

        ind_type = _indicator_type(target)
        sections = ["general", "reputation", "geo"]
        data: dict[str, Any] = {"indicator_type": ind_type, "sections": {}}

        for section in sections:
            url = f"{_BASE}/{ind_type}/{target}/{section}"
            try:
                resp = requests.get(url, headers=headers, timeout=self.timeout_seconds)
                if resp.status_code == 404:
                    errors.append(f"alienvault: '{target}' no encontrado en sección {section}.")
                    continue
                if resp.status_code == 403:
                    errors.append("alienvault: acceso denegado — establece OTX_API_KEY.")
                    break
                resp.raise_for_status()
                data["sections"][section] = resp.json()
            except requests.RequestException as exc:
                errors.append(f"alienvault [{section}]: error de red — {exc}")
            except Exception as exc:
                errors.append(f"alienvault [{section}]: error — {exc}")

        general = data["sections"].get("general", {})
        data["pulse_count"] = general.get("pulse_info", {}).get("count", 0)
        data["reputation"] = general.get("reputation", 0)
        data["country_code"] = data["sections"].get("geo", {}).get("country_code")
        data["asn"] = data["sections"].get("geo", {}).get("asn")

        return ConnectorResult(
            connector=self.name,
            ok=bool(data["sections"]),
            data=data,
            errors=errors,
            metadata={
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "indicator_type": ind_type,
                "api_key_used": bool(api_key),
            },
        )
