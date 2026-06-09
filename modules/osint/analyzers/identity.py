"""analyzers/identity.py — Correlación de identidad entre resultados de conectores."""
from __future__ import annotations

import re
from typing import Any

from modules.osint.connectors.base import ConnectorResult

try:
    from rapidfuzz import fuzz as _fuzz
    _RAPIDFUZZ_AVAILABLE = True
except ImportError:
    _RAPIDFUZZ_AVAILABLE = False

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\+?[\d\s\-\(\)]{7,20}")
_URL_RE = re.compile(r"https?://[^\s\"'>]+")


def _flatten(obj: Any, depth: int = 4) -> list[str]:
    if depth <= 0:
        return []
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        results = []
        for v in obj.values():
            results.extend(_flatten(v, depth - 1))
        return results
    if isinstance(obj, (list, tuple)):
        results = []
        for item in obj:
            results.extend(_flatten(item, depth - 1))
        return results
    return [str(obj)] if obj is not None else []


class IdentityAnalyzer:
    """Extrae y correlaciona indicadores de identidad de múltiples ConnectorResult."""

    def analyze(self, results: dict[str, ConnectorResult]) -> dict[str, Any]:
        all_text = " ".join(_flatten(r.data) for r in results.values())

        emails = list({m.lower() for m in _EMAIL_RE.findall(all_text)})
        phones = list({m for m in _PHONE_RE.findall(all_text) if len(m.replace(" ", "").replace("-", "")) >= 7})
        urls = list({m for m in _URL_RE.findall(all_text)})

        usernames: list[str] = []
        real_names: list[str] = []
        accounts: list[dict[str, str]] = []

        for connector_name, result in results.items():
            if not result.ok:
                continue
            data = result.data

            if connector_name == "github":
                profile = data.get("profile") or {}
                if profile.get("login"):
                    usernames.append(profile["login"])
                if profile.get("name"):
                    real_names.append(profile["name"])
                if profile.get("email"):
                    emails.append(profile["email"].lower())
                accounts.append({"platform": "github", "url": profile.get("html_url", "")})

            elif connector_name == "reddit":
                profile = data.get("profile") or {}
                if profile.get("name"):
                    usernames.append(profile["name"])
                accounts.append({"platform": "reddit", "url": f"https://reddit.com/u/{profile.get('name', '')}"})

        return {
            "emails": sorted(set(e for e in emails if e)),
            "phones": sorted(set(phones)),
            "urls": urls[:50],
            "usernames": sorted(set(usernames)),
            "real_names": sorted(set(real_names)),
            "accounts": accounts,
            "connector_count": len(results),
            "successful_connectors": [n for n, r in results.items() if r.ok],
        }


def fuzzy_match_usernames(
    names: list[str],
    threshold: float = 0.85,
) -> list[tuple[str, str, float]]:
    """
    Encuentra pares de usernames similares usando rapidfuzz.

    Args:
        names: Lista de nombres/usernames a comparar.
        threshold: Umbral de similitud (0.0–1.0). Por defecto 0.85.

    Returns:
        Lista de tuplas (name_a, name_b, score) donde score >= threshold.
        Score es un valor entre 0.0 y 1.0 (la función divide por 100 el resultado de rapidfuzz).
    """
    if not _RAPIDFUZZ_AVAILABLE or len(names) < 2:
        return []

    matches: list[tuple[str, str, float]] = []
    seen: set[frozenset[str]] = set()

    for i, a in enumerate(names):
        for b in names[i + 1:]:
            pair = frozenset({a, b})
            if pair in seen:
                continue
            seen.add(pair)
            score = _fuzz.ratio(a.lower(), b.lower()) / 100.0
            if score >= threshold:
                matches.append((a, b, round(score, 4)))

    return sorted(matches, key=lambda t: t[2], reverse=True)
