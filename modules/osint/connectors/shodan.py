"""connectors/shodan.py — Shodan API connector (requiere API key gratuita)."""
from __future__ import annotations

import os
import re
import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_BASE = "https://api.shodan.io"
_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


class ShodanApiConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "shodan"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"ip", "domain"})

    @property
    def needs_api_key(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> float:
        return 12.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        errors: list[str] = []
        t0 = time.monotonic()
        api_key = kwargs.get("api_key") or os.environ.get("SHODAN_API_KEY", "")

        if not api_key:
            return ConnectorResult(
                connector=self.name,
                ok=False,
                data={},
                errors=["shodan: API key no configurada — establece SHODAN_API_KEY."],
                metadata={"latency_ms": 0},
            )

        data: dict[str, Any] = {}
        try:
            ip = self._resolve_ip(target, api_key, errors)
            if not ip:
                return ConnectorResult(
                    connector=self.name,
                    ok=False,
                    data={},
                    errors=errors or [f"shodan: no se pudo resolver '{target}' a IP."],
                    metadata={"latency_ms": int((time.monotonic() - t0) * 1000)},
                )

            resp = requests.get(
                f"{_BASE}/shodan/host/{ip}",
                params={"key": api_key},
                timeout=self.timeout_seconds,
            )
            if resp.status_code == 401:
                errors.append("shodan: API key inválida (401).")
            elif resp.status_code == 404:
                errors.append(f"shodan: host '{ip}' no encontrado (404).")
            elif resp.status_code == 429:
                errors.append("shodan: rate limit alcanzado (429).")
            else:
                resp.raise_for_status()
                raw = resp.json()
                data = {
                    "ip":           raw.get("ip_str", ip),
                    "org":          raw.get("org"),
                    "isp":          raw.get("isp"),
                    "asn":          raw.get("asn"),
                    "country_code": raw.get("country_code"),
                    "country_name": raw.get("country_name"),
                    "city":         raw.get("city"),
                    "os":           raw.get("os"),
                    "ports":        raw.get("ports", []),
                    "hostnames":    raw.get("hostnames", []),
                    "domains":      raw.get("domains", []),
                    "vulns":        list(raw.get("vulns", {}).keys()),
                    "tags":         raw.get("tags", []),
                    "last_update":  raw.get("last_update"),
                    "query_input":  target,
                }
        except requests.RequestException as exc:
            errors.append(f"shodan: error de red — {exc}")
        except Exception as exc:
            errors.append(f"shodan: error inesperado — {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=bool(data),
            data=data,
            errors=errors,
            metadata={"latency_ms": int((time.monotonic() - t0) * 1000)},
        )

    def _resolve_ip(self, target: str, api_key: str, errors: list[str]) -> str:
        """Si target es dominio, resuelve a IP vía Shodan DNS; si ya es IP la retorna."""
        if _IP_RE.match(target):
            return target
        try:
            resp = requests.get(
                f"{_BASE}/dns/resolve",
                params={"hostnames": target, "key": api_key},
                timeout=8.0,
            )
            resp.raise_for_status()
            resolved = resp.json().get(target, "")
            if resolved:
                return str(resolved)
            errors.append(f"shodan: DNS no resolvió '{target}'.")
        except Exception as exc:
            errors.append(f"shodan: error resolviendo DNS — {exc}")
        return ""
