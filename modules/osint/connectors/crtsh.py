"""connectors/crtsh.py — crt.sh Certificate Transparency log connector."""
from __future__ import annotations

import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_URL = "https://crt.sh/"


class CrtShConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "crtsh"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"domain", "email"})

    @property
    def timeout_seconds(self) -> float:
        return 15.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        errors: list[str] = []
        t0 = time.monotonic()
        entries: list[dict] = []

        try:
            resp = requests.get(
                _URL,
                params={"q": target, "output": "json"},
                timeout=self.timeout_seconds,
                headers={"User-Agent": "NEXO-147-OSINT/1.0"},
            )
            if resp.status_code == 404:
                errors.append(f"crtsh: no se encontraron certificados para '{target}'.")
            else:
                resp.raise_for_status()
                raw = resp.json() or []
                seen: set[str] = set()
                for item in raw:
                    name = item.get("name_value", "").strip()
                    issuer = item.get("issuer_ca_id")
                    not_before = item.get("not_before", "")
                    not_after = item.get("not_after", "")
                    for cn in name.splitlines():
                        cn = cn.strip()
                        if cn and cn not in seen:
                            seen.add(cn)
                            entries.append({
                                "common_name": cn,
                                "issuer_ca_id": issuer,
                                "not_before": not_before,
                                "not_after": not_after,
                            })
        except requests.RequestException as exc:
            errors.append(f"crtsh: error de red — {exc}")
        except Exception as exc:
            errors.append(f"crtsh: error inesperado — {exc}")

        subdomains = sorted({
            e["common_name"] for e in entries
            if not e["common_name"].startswith("*")
        })

        return ConnectorResult(
            connector=self.name,
            ok=bool(entries),
            data={"entries": entries, "subdomains": subdomains},
            errors=errors,
            metadata={
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "cert_count": len(entries),
                "subdomain_count": len(subdomains),
            },
        )
