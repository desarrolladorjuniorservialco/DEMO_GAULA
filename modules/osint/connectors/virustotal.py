"""connectors/virustotal.py — VirusTotal v3 API connector (requiere API key gratuita)."""
from __future__ import annotations

import base64
import os
import re
import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_BASE = "https://www.virustotal.com/api/v3"
_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_HASH_RE = re.compile(r"^[a-fA-F0-9]{32,64}$")


def _vt_url_id(url: str) -> str:
    """VirusTotal v3 requiere URLs codificadas en base64 sin padding."""
    return base64.urlsafe_b64encode(url.encode()).rstrip(b"=").decode()


class VirusTotalApiConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "virustotal"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"ip", "domain", "hash", "url"})

    @property
    def needs_api_key(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> float:
        return 12.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        errors: list[str] = []
        t0 = time.monotonic()
        api_key = kwargs.get("api_key") or os.environ.get("VIRUSTOTAL_API_KEY", "")
        target_type: str = kwargs.get("target_type", "")

        if not api_key:
            return ConnectorResult(
                connector=self.name,
                ok=False,
                data={},
                errors=["virustotal: API key no configurada — establece VIRUSTOTAL_API_KEY."],
                metadata={"latency_ms": 0},
            )

        endpoint = self._endpoint(target, target_type)
        if not endpoint:
            return ConnectorResult(
                connector=self.name,
                ok=False,
                data={},
                errors=[f"virustotal: tipo de objetivo no reconocido para '{target}'."],
                metadata={"latency_ms": 0},
            )

        data: dict[str, Any] = {}
        try:
            resp = requests.get(
                endpoint,
                headers={"x-apikey": api_key},
                timeout=self.timeout_seconds,
            )
            if resp.status_code == 401:
                errors.append("virustotal: API key inválida (401).")
            elif resp.status_code == 404:
                errors.append(f"virustotal: recurso '{target}' no encontrado (404).")
            elif resp.status_code == 429:
                errors.append("virustotal: rate limit alcanzado (429) — free tier: 4 req/min.")
            else:
                resp.raise_for_status()
                attrs = resp.json().get("data", {}).get("attributes", {})
                stats = attrs.get("last_analysis_stats", {})
                data = {
                    "target":                     target,
                    "target_type":                target_type,
                    "last_analysis_stats":        stats,
                    "malicious":                  stats.get("malicious", 0),
                    "suspicious":                 stats.get("suspicious", 0),
                    "harmless":                   stats.get("harmless", 0),
                    "undetected":                 stats.get("undetected", 0),
                    "reputation":                 attrs.get("reputation"),
                    "asn":                        attrs.get("asn"),
                    "as_owner":                   attrs.get("as_owner"),
                    "country":                    attrs.get("country"),
                    "network":                    attrs.get("network"),
                    "regional_internet_registry": attrs.get("regional_internet_registry"),
                    "last_analysis_date":         attrs.get("last_analysis_date"),
                    "tags":                       attrs.get("tags", []),
                }
        except requests.RequestException as exc:
            errors.append(f"virustotal: error de red — {exc}")
        except Exception as exc:
            errors.append(f"virustotal: error inesperado — {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=bool(data),
            data=data,
            errors=errors,
            metadata={"latency_ms": int((time.monotonic() - t0) * 1000)},
        )

    def _endpoint(self, target: str, target_type: str) -> str:
        if target_type == "ip":
            return f"{_BASE}/ip_addresses/{target}"
        if target_type == "domain":
            return f"{_BASE}/domains/{target}"
        if target_type == "hash":
            return f"{_BASE}/files/{target}"
        if target_type == "url":
            return f"{_BASE}/urls/{_vt_url_id(target)}"
        # Inferencia si target_type no se especificó explícitamente
        if _IP_RE.match(target):
            return f"{_BASE}/ip_addresses/{target}"
        if _HASH_RE.match(target):
            return f"{_BASE}/files/{target}"
        if target.startswith(("http://", "https://")):
            return f"{_BASE}/urls/{_vt_url_id(target)}"
        if "." in target:
            return f"{_BASE}/domains/{target}"
        return ""
