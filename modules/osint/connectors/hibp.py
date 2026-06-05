"""connectors/hibp.py — Have I Been Pwned v3 connector (requiere API key)."""
from __future__ import annotations

import os
import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_BASE = "https://haveibeenpwned.com/api/v3"
_HEADERS_BASE = {
    "User-Agent": "NEXO-147-OSINT/1.0",
    "hibp-api-key": "",
}


class HibpConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "hibp"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"email"})

    @property
    def needs_api_key(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> float:
        return 10.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        errors: list[str] = []
        t0 = time.monotonic()
        api_key = kwargs.get("api_key") or os.environ.get("HIBP_API_KEY", "")

        if not api_key:
            return ConnectorResult(
                connector=self.name,
                ok=False,
                data={},
                errors=["hibp: API key no configurada — establece HIBP_API_KEY."],
                metadata={"latency_ms": 0},
            )

        headers = {**_HEADERS_BASE, "hibp-api-key": api_key}
        breaches: list[dict] = []
        pastes: list[dict] = []

        try:
            resp = requests.get(
                f"{_BASE}/breachedaccount/{target}",
                headers=headers,
                params={"truncateResponse": False},
                timeout=self.timeout_seconds,
            )
            if resp.status_code == 404:
                pass  # dirección no encontrada en ninguna brecha — resultado limpio
            elif resp.status_code == 401:
                errors.append("hibp: API key inválida (401).")
            elif resp.status_code == 429:
                errors.append("hibp: rate limit (429) — espera antes de reintentar.")
            else:
                resp.raise_for_status()
                raw = resp.json() or []
                breaches = [
                    {
                        "name": b.get("Name"),
                        "domain": b.get("Domain"),
                        "breach_date": b.get("BreachDate"),
                        "pwn_count": b.get("PwnCount"),
                        "is_verified": b.get("IsVerified"),
                        "data_classes": b.get("DataClasses", []),
                    }
                    for b in raw
                ]
        except requests.RequestException as exc:
            errors.append(f"hibp: error de red — {exc}")

        try:
            r2 = requests.get(
                f"{_BASE}/pasteaccount/{target}",
                headers=headers,
                timeout=self.timeout_seconds,
            )
            if r2.status_code == 200:
                pastes = [
                    {
                        "source": p.get("Source"),
                        "id": p.get("Id"),
                        "title": p.get("Title"),
                        "date": p.get("Date"),
                        "email_count": p.get("EmailCount"),
                    }
                    for p in (r2.json() or [])
                ]
        except requests.RequestException as exc:
            errors.append(f"hibp [pastes]: error de red — {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=True,
            data={"breaches": breaches, "pastes": pastes},
            errors=errors,
            metadata={
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "breach_count": len(breaches),
                "paste_count": len(pastes),
            },
        )
