"""analyzers/enrichment.py — Enriquecimiento cruzado de resultados de conectores."""
from __future__ import annotations

from typing import Any

from modules.osint.connectors.base import ConnectorResult


class EnrichmentAnalyzer:
    """Agrega y normaliza datos de múltiples conectores en un perfil unificado."""

    def enrich(self, results: dict[str, ConnectorResult]) -> dict[str, Any]:
        profile: dict[str, Any] = {
            "geo": {},
            "network": {},
            "registrar_info": {},
            "subdomains": [],
            "reputation": {},
            "certificates": [],
            "social_presence": [],
        }

        av = results.get("alienvault")
        if av and av.ok:
            profile["geo"]["country_code"] = av.data.get("country_code")
            profile["geo"]["asn"] = av.data.get("asn")
            profile["network"]["reputation_score"] = av.data.get("reputation", 0)
            profile["reputation"]["alienvault_pulses"] = av.data.get("pulse_count", 0)

        abuse = results.get("abuseipdb")
        if abuse and abuse.ok:
            if not profile["geo"].get("country_code"):
                profile["geo"]["country_code"] = abuse.data.get("country_code")
            profile["network"]["isp"] = abuse.data.get("isp")
            profile["network"]["usage_type"] = abuse.data.get("usage_type")
            profile["reputation"]["abuse_confidence"] = abuse.data.get("abuse_confidence_score", 0)
            profile["reputation"]["abuse_reports"] = abuse.data.get("total_reports", 0)

        rdap = results.get("rdap")
        if rdap and rdap.ok:
            profile["registrar_info"]["registrar"] = rdap.data.get("registrar")
            profile["registrar_info"]["creation_date"] = (rdap.data.get("events") or {}).get("registration")
            profile["registrar_info"]["expiration_date"] = (rdap.data.get("events") or {}).get("expiration")
            profile["registrar_info"]["status"] = rdap.data.get("status", [])
            profile["registrar_info"]["nameservers"] = rdap.data.get("nameservers", [])

        whois_r = results.get("whois")
        if whois_r and whois_r.ok and not profile["registrar_info"].get("registrar"):
            profile["registrar_info"]["registrar"] = whois_r.data.get("registrar")
            profile["registrar_info"]["creation_date"] = whois_r.data.get("creation_date")
            profile["registrar_info"]["expiration_date"] = whois_r.data.get("expiration_date")

        crtsh = results.get("crtsh")
        if crtsh and crtsh.ok:
            profile["subdomains"] = crtsh.data.get("subdomains", [])
            profile["certificates"] = [
                {"cn": e.get("common_name"), "not_after": e.get("not_after")}
                for e in (crtsh.data.get("entries") or [])[:20]
            ]

        gh = results.get("github")
        if gh and gh.ok:
            p = gh.data.get("profile") or {}
            profile["social_presence"].append({
                "platform": "github",
                "url": p.get("html_url", ""),
                "followers": p.get("followers", 0),
                "public_repos": p.get("public_repos", 0),
            })

        reddit_r = results.get("reddit")
        if reddit_r and reddit_r.ok:
            p = reddit_r.data.get("profile") or {}
            profile["social_presence"].append({
                "platform": "reddit",
                "url": f"https://reddit.com/u/{p.get('name', '')}",
                "karma": (p.get("link_karma", 0) or 0) + (p.get("comment_karma", 0) or 0),
            })

        hibp = results.get("hibp")
        if hibp and hibp.ok:
            profile["reputation"]["hibp_breaches"] = len(hibp.data.get("breaches", []))
            profile["reputation"]["hibp_pastes"] = len(hibp.data.get("pastes", []))

        return profile
