"""analyzers/risk.py — Puntuación de riesgo basada en indicadores OSINT."""
from __future__ import annotations

from typing import Any

from modules.osint.connectors.base import ConnectorResult

_RISK_WEIGHTS = {
    "hibp_breach": 15,
    "hibp_paste": 10,
    "abuse_score_high": 30,
    "abuse_score_medium": 15,
    "otx_pulse": 10,
    "domain_expired": 20,
    "many_subdomains": 5,
}

_RISK_LEVELS = [
    (75, "CRITICO"),
    (50, "ALTO"),
    (25, "MEDIO"),
    (10, "BAJO"),
    (0,  "LIMPIO"),
]


def _risk_level(score: int) -> str:
    for threshold, label in _RISK_LEVELS:
        if score >= threshold:
            return label
    return "LIMPIO"


class RiskAnalyzer:
    """Calcula una puntuación de riesgo consolidada de los resultados de conectores."""

    def score(self, results: dict[str, ConnectorResult]) -> dict[str, Any]:
        total = 0
        factors: list[dict[str, Any]] = []

        hibp = results.get("hibp")
        if hibp and hibp.ok:
            breach_count = len(hibp.data.get("breaches", []))
            paste_count = len(hibp.data.get("pastes", []))
            if breach_count:
                pts = _RISK_WEIGHTS["hibp_breach"] * min(breach_count, 5)
                total += pts
                factors.append({"factor": "hibp_breach", "points": pts, "detail": f"{breach_count} brechas"})
            if paste_count:
                pts = _RISK_WEIGHTS["hibp_paste"] * min(paste_count, 3)
                total += pts
                factors.append({"factor": "hibp_paste", "points": pts, "detail": f"{paste_count} pastes"})

        abuseipdb = results.get("abuseipdb")
        if abuseipdb and abuseipdb.ok:
            abuse_score = abuseipdb.data.get("abuse_confidence_score", 0) or 0
            if abuse_score >= 75:
                pts = _RISK_WEIGHTS["abuse_score_high"]
                total += pts
                factors.append({"factor": "abuse_score_high", "points": pts, "detail": f"score={abuse_score}"})
            elif abuse_score >= 25:
                pts = _RISK_WEIGHTS["abuse_score_medium"]
                total += pts
                factors.append({"factor": "abuse_score_medium", "points": pts, "detail": f"score={abuse_score}"})

        alienvault = results.get("alienvault")
        if alienvault and alienvault.ok:
            pulse_count = alienvault.data.get("pulse_count", 0) or 0
            if pulse_count > 0:
                pts = _RISK_WEIGHTS["otx_pulse"] * min(pulse_count, 5)
                total += pts
                factors.append({"factor": "otx_pulse", "points": pts, "detail": f"{pulse_count} pulsos OTX"})

        crtsh = results.get("crtsh")
        if crtsh and crtsh.ok:
            subdomain_count = crtsh.metadata.get("subdomain_count", 0) or 0
            if subdomain_count > 50:
                pts = _RISK_WEIGHTS["many_subdomains"]
                total += pts
                factors.append({"factor": "many_subdomains", "points": pts, "detail": f"{subdomain_count} subdominios"})

        total = min(total, 100)
        return {
            "score": total,
            "level": _risk_level(total),
            "factors": factors,
            "connector_inputs": list(results.keys()),
        }
