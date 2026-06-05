"""connectors/whois.py — WHOIS connector (python-whois + fallback API)."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from modules.osint.connectors.base import BaseConnector, ConnectorResult

try:
    import whois as _whois_lib
    _WHOIS_AVAILABLE = True
except ImportError:
    _WHOIS_AVAILABLE = False


def _date_str(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, list):
        val = val[0]
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


class WhoisConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "whois"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"domain"})

    @property
    def timeout_seconds(self) -> float:
        return 15.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        errors: list[str] = []
        t0 = time.monotonic()
        data: dict[str, Any] = {}

        if not _WHOIS_AVAILABLE:
            return ConnectorResult(
                connector=self.name,
                ok=False,
                data={},
                errors=["whois: python-whois no instalado — pip install python-whois"],
                metadata={"latency_ms": 0, "library_available": False},
            )

        try:
            w = _whois_lib.whois(target)
            name_servers = w.name_servers or []
            if isinstance(name_servers, str):
                name_servers = [name_servers]

            emails = w.emails or []
            if isinstance(emails, str):
                emails = [emails]

            registrant_name = None
            for attr in ("registrant_name", "name", "org"):
                val = getattr(w, attr, None)
                if val:
                    registrant_name = str(val)
                    break

            data = {
                "domain_name": w.domain_name,
                "registrar": w.registrar,
                "registrant_name": registrant_name,
                "creation_date": _date_str(w.creation_date),
                "expiration_date": _date_str(w.expiration_date),
                "updated_date": _date_str(w.updated_date),
                "name_servers": [ns.lower() for ns in name_servers if ns],
                "status": w.status,
                "emails": list({e.lower() for e in emails if e}),
                "dnssec": getattr(w, "dnssec", None),
                "country": getattr(w, "country", None),
            }
        except Exception as exc:
            errors.append(f"whois: error — {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=bool(data),
            data=data,
            errors=errors,
            metadata={
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "library_available": _WHOIS_AVAILABLE,
            },
        )
