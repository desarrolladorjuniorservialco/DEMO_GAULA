"""connectors/phone.py — Lookup de número telefónico con prefijos colombianos y DDG."""
from __future__ import annotations

import re
import time
from typing import Any

from .base import BaseConnector, ConnectorResult

# Prefijos móviles Colombia (3 dígitos)
_CO_CARRIERS: dict[str, str] = {
    "300": "Claro",      "301": "Claro",      "302": "Claro",
    "303": "Claro",      "304": "ETB Móvil",  "305": "ETB Móvil",
    "310": "Claro",      "311": "Claro",      "312": "Claro",
    "313": "Claro",      "314": "Claro",
    "315": "Tigo",
    "316": "Wom",        "317": "Wom",
    "318": "Tigo/Une",   "319": "Tigo/Une",
    "320": "Tigo",       "321": "Tigo",       "322": "Tigo",
    "323": "Tigo",       "324": "Claro",
    "350": "Tigo",       "351": "Tigo",       "352": "Tigo",
    "353": "Tigo",       "354": "Tigo",
}

_NORMALIZE_RE = re.compile(r"[^\d]")


def _normalize_phone(raw: str) -> str:
    digits = _NORMALIZE_RE.sub("", raw)
    if digits.startswith("57") and len(digits) == 12:
        digits = digits[2:]
    return digits


def _carrier_info(digits: str) -> dict[str, str]:
    prefix3 = digits[:3]
    carrier = _CO_CARRIERS.get(prefix3)
    if carrier:
        return {"carrier": carrier, "country": "Colombia", "line_type": "mobile", "prefix": prefix3}
    if digits.startswith(("60", "61", "62", "63", "64", "65", "66", "67", "68", "69")):
        return {"carrier": "Línea fija", "country": "Colombia", "line_type": "landline", "prefix": prefix3}
    return {"carrier": "Desconocido", "country": "Unknown", "line_type": "unknown", "prefix": prefix3}


class PhoneConnector(BaseConnector):
    """Búsqueda de número telefónico: prefijo operador + menciones DDG."""

    @property
    def name(self) -> str:
        return "phone"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"phone"})

    @property
    def needs_api_key(self) -> bool:
        return False

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        normalized = _normalize_phone(target)
        carrier = _carrier_info(normalized)
        dork_results: list[dict] = []
        errors: list[str] = []

        queries = [
            f'"{target}"',
            f'"{normalized}" Colombia',
        ]

        try:
            from duckduckgo_search import DDGS
            from duckduckgo_search.exceptions import DuckDuckGoSearchException
            try:
                from duckduckgo_search.exceptions import RatelimitException
            except ImportError:
                RatelimitException = DuckDuckGoSearchException

            seen_urls: set[str] = set()
            with DDGS() as ddgs:
                for query in queries:
                    try:
                        raw = ddgs.text(query, max_results=15) or []
                        for r in raw:
                            url = r.get("href", "")
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                dork_results.append({
                                    "title":   r.get("title", "")[:120],
                                    "url":     url,
                                    "snippet": r.get("body", "")[:250],
                                    "query":   query,
                                })
                        time.sleep(1.5)
                    except RatelimitException:
                        errors.append("phone DDG: rate limit 429 — espera 60s.")
                        break
                    except DuckDuckGoSearchException as exc:
                        errors.append(f"phone DDG: {exc}")
        except ImportError:
            errors.append("duckduckgo-search no disponible.")

        return ConnectorResult(
            connector=self.name,
            ok=True,
            data={
                "phone_raw":        target,
                "phone_normalized": normalized,
                "carrier":          carrier,
                "dork_results":     dork_results,
                "mentions_count":   len(dork_results),
            },
            errors=errors,
            metadata={"carrier": carrier},
        )
