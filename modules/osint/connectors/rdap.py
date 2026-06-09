"""connectors/rdap.py — RDAP (Registration Data Access Protocol) connector."""
from __future__ import annotations

import re
import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_RDAP = "https://rdap.org"
_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$|^[0-9a-fA-F:]{3,}$")


def _entity_emails(entities: list[dict]) -> list[str]:
    emails: list[str] = []
    for ent in entities or []:
        vcard = ent.get("vcardArray", [])
        if isinstance(vcard, list) and len(vcard) > 1:
            for item in vcard[1]:
                if isinstance(item, list) and len(item) >= 4:
                    if item[0] == "email":
                        emails.append(str(item[3]))
    return emails


class RdapConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "rdap"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"domain", "ip"})

    @property
    def timeout_seconds(self) -> float:
        return 10.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        errors: list[str] = []
        t0 = time.monotonic()
        data: dict[str, Any] = {}

        kind = "ip" if _IP_RE.match(target) else "domain"
        url = f"{_RDAP}/{kind}/{target}"

        try:
            resp = requests.get(
                url,
                timeout=self.timeout_seconds,
                headers={"User-Agent": "NEXO-147-OSINT/1.0", "Accept": "application/rdap+json"},
            )
            if resp.status_code == 404:
                errors.append(f"rdap: '{target}' no encontrado.")
            else:
                resp.raise_for_status()
                raw = resp.json()
                events = {
                    e.get("eventAction"): e.get("eventDate")
                    for e in raw.get("events", [])
                    if e.get("eventAction")
                }
                data = {
                    "handle": raw.get("handle"),
                    "ldh_name": raw.get("ldhName"),
                    "unicode_name": raw.get("unicodeName"),
                    "status": raw.get("status", []),
                    "events": events,
                    "registrar": None,
                    "registrant_emails": _entity_emails(raw.get("entities", [])),
                    "nameservers": [
                        ns.get("ldhName") for ns in raw.get("nameservers", [])
                    ],
                    "kind": kind,
                }
                for ent in raw.get("entities", []):
                    if "registrar" in (ent.get("roles") or []):
                        vcard = ent.get("vcardArray", [])
                        if isinstance(vcard, list) and len(vcard) > 1:
                            for item in vcard[1]:
                                if isinstance(item, list) and item[0] == "fn":
                                    data["registrar"] = item[3]
        except requests.RequestException as exc:
            errors.append(f"rdap: error de red — {exc}")
        except Exception as exc:
            errors.append(f"rdap: error inesperado — {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=bool(data),
            data=data,
            errors=errors,
            metadata={"latency_ms": int((time.monotonic() - t0) * 1000), "kind": kind},
        )
