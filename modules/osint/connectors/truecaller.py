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
