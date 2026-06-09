"""connectors/abuseipdb.py — AbuseIPDB v2 connector (requiere API key)."""
from __future__ import annotations

import os
import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_BASE = "https://api.abuseipdb.com/api/v2"


class AbuseIpDbConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "abuseipdb"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"ip"})

    @property
    def needs_api_key(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> float:
        return 10.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        errors: list[str] = []
        t0 = time.monotonic()
        api_key = kwargs.get("api_key") or os.environ.get("ABUSEIPDB_API_KEY", "")

        if not api_key:
            return ConnectorResult(
                connector=self.name,
                ok=False,
                data={},
                errors=["abuseipdb: API key no configurada — establece ABUSEIPDB_API_KEY."],
                metadata={"latency_ms": 0},
            )

        data: dict[str, Any] = {}
        try:
            resp = requests.get(
                f"{_BASE}/check",
                headers={"Key": api_key, "Accept": "application/json"},
                params={"ipAddress": target, "maxAgeInDays": 90, "verbose": False},
                timeout=self.timeout_seconds,
            )
            if resp.status_code == 401:
                errors.append("abuseipdb: API key inválida (401).")
            elif resp.status_code == 422:
                errors.append(f"abuseipdb: IP inválida '{target}' (422).")
            elif resp.status_code == 429:
                errors.append("abuseipdb: rate limit (429).")
            else:
                resp.raise_for_status()
                raw = resp.json().get("data", {})
                data = {
                    "ip_address": raw.get("ipAddress"),
                    "is_public": raw.get("isPublic"),
                    "ip_version": raw.get("ipVersion"),
                    "is_whitelisted": raw.get("isWhitelisted"),
                    "abuse_confidence_score": raw.get("abuseConfidenceScore"),
                    "country_code": raw.get("countryCode"),
                    "usage_type": raw.get("usageType"),
                    "isp": raw.get("isp"),
                    "domain": raw.get("domain"),
                    "total_reports": raw.get("totalReports"),
                    "num_distinct_users": raw.get("numDistinctUsers"),
                    "last_reported_at": raw.get("lastReportedAt"),
                }
        except requests.RequestException as exc:
            errors.append(f"abuseipdb: error de red — {exc}")
        except Exception as exc:
            errors.append(f"abuseipdb: error inesperado — {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=bool(data),
            data=data,
            errors=errors,
            metadata={"latency_ms": int((time.monotonic() - t0) * 1000)},
        )
