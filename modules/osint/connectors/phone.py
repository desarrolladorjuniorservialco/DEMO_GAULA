"""connectors/phone.py — Lookup de número telefónico: phonenumbers + NumVerify + DDG."""
from __future__ import annotations

import os
import re
import time
from typing import Any

import requests

from .base import BaseConnector, ConnectorResult

_NUMVERIFY_URL = "https://api.apilayer.com/number_verification/validate"

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


def _local_carrier(digits: str) -> dict[str, str]:
    prefix3 = digits[:3]
    carrier = _CO_CARRIERS.get(prefix3)
    if carrier:
        return {"carrier": carrier, "country": "Colombia", "line_type": "mobile", "prefix": prefix3}
    if digits.startswith(("60", "61", "62", "63", "64", "65", "66", "67", "68", "69")):
        return {"carrier": "Línea fija", "country": "Colombia", "line_type": "landline", "prefix": prefix3}
    return {"carrier": "Desconocido", "country": "Unknown", "line_type": "unknown", "prefix": prefix3}


def _phonenumbers_parse(raw: str) -> dict[str, Any]:
    try:
        import phonenumbers
        from phonenumbers import carrier as ph_carrier, geocoder, timezone as ph_timezone

        phone = phonenumbers.parse(raw, "CO")
        if phonenumbers.is_valid_number(phone):
            return {
                "valid": True,
                "international": phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
                "e164": phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164),
                "carrier": ph_carrier.name_for_number(phone, "es") or "",
                "region": geocoder.description_for_number(phone, "es") or "",
                "timezone": list(ph_timezone.time_zones_for_number(phone)),
            }
        return {"valid": False}
    except Exception:
        return {"valid": False}


def _numverify_enrich(phone_e164: str) -> dict[str, Any]:
    key = os.getenv("NUMVERIFY_API_KEY", "").strip()
    if not key:
        return {}
    try:
        resp = requests.get(
            _NUMVERIFY_URL,
            headers={"apikey": key},
            params={"number": phone_e164},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("valid"):
            return {
                "carrier":              data.get("carrier", ""),
                "line_type":            data.get("line_type", ""),
                "country":              data.get("country_name", ""),
                "location":             data.get("location", ""),
                "international_format": data.get("international_format", ""),
            }
    except Exception:
        pass
    return {}


class PhoneConnector(BaseConnector):

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
        local = _local_carrier(normalized)
        parsed = _phonenumbers_parse(target)
        e164 = parsed.get("e164", f"+57{normalized}")
        numverify = _numverify_enrich(e164)

        carrier_name = (
            numverify.get("carrier")
            or parsed.get("carrier")
            or local.get("carrier", "—")
        )
        line_type = numverify.get("line_type") or local.get("line_type", "—")
        country = numverify.get("country") or local.get("country", "—")
        location = numverify.get("location") or parsed.get("region", "—")

        dork_results: list[dict] = []
        errors: list[str] = []

        try:
            from duckduckgo_search import DDGS
            from duckduckgo_search.exceptions import DuckDuckGoSearchException
            try:
                from duckduckgo_search.exceptions import RatelimitException
            except ImportError:
                RatelimitException = DuckDuckGoSearchException

            seen_urls: set[str] = set()
            with DDGS() as ddgs:
                for query in [f'"{target}"', f'"{normalized}" Colombia']:
                    try:
                        for r in (ddgs.text(query, max_results=10) or []):
                            url = r.get("href", "")
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                dork_results.append({
                                    "title":   r.get("title", "")[:120],
                                    "url":     url,
                                    "snippet": r.get("body", "")[:250],
                                })
                        time.sleep(1.5)
                    except RatelimitException:
                        errors.append("DDG: rate limit — intenta en 60s.")
                        break
                    except DuckDuckGoSearchException as exc:
                        errors.append(f"DDG: {exc}")
        except ImportError:
            errors.append("duckduckgo-search no disponible.")

        return ConnectorResult(
            connector=self.name,
            ok=True,
            data={
                "phone_raw":        target,
                "phone_normalized": normalized,
                "international":    parsed.get("international", ""),
                "valid":            parsed.get("valid", False),
                "carrier":          carrier_name,
                "line_type":        line_type,
                "country":          country,
                "location":         location,
                "timezone":         parsed.get("timezone", []),
                "numverify":        numverify,
                "dork_results":     dork_results,
                "mentions_count":   len(dork_results),
            },
            errors=errors,
            metadata={"enriched": bool(numverify)},
        )
