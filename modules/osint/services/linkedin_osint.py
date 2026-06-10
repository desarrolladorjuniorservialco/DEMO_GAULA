"""services/linkedin_osint.py — Extrae perfiles y empresas de LinkedIn desde resultados DDG."""
from __future__ import annotations

import re

_LINKEDIN_SYSTEM_PATHS = frozenset({
    "feed", "notifications", "messaging", "mynetwork", "jobs",
    "search", "learning", "pulse", "login", "signup", "oauth",
    "tos", "privacy", "about", "help", "legal", "page", "auth",
    "checkpoint", "start", "comm",
})


def _extract_linkedin_entity(url: str) -> tuple[str | None, str]:
    m_profile = re.search(
        r'linkedin\.com/in/([a-zA-Z0-9_%\-]{3,100})(?:/|$|\?|#)',
        url, re.IGNORECASE,
    )
    if m_profile:
        slug = m_profile.group(1)
        if slug.lower() not in _LINKEDIN_SYSTEM_PATHS:
            return slug, "profile"

    m_company = re.search(
        r'linkedin\.com/company/([a-zA-Z0-9_%\-]{2,100})(?:/|$|\?|#)',
        url, re.IGNORECASE,
    )
    if m_company:
        return m_company.group(1), "company"

    return None, "unknown"


def _extract_connections_hint(snippet: str) -> str | None:
    if not snippet:
        return None
    m = re.search(
        r'([\d,.]+[KkMm\+]?)\s*(?:connections?|conexiones?|seguidores|followers)',
        snippet, re.IGNORECASE,
    )
    return m.group(0)[:40] if m else None


def _extract_title_hint(snippet: str) -> str | None:
    if not snippet:
        return None
    m = re.search(r'(?:·|—|-)\s*(.{5,80}?)(?:\s*·|\s*—|\s*at\s|\s*en\s|$)', snippet)
    return m.group(1).strip()[:80] if m else None


def extract_linkedin_profiles(dork_results: list[dict], objetivo: str) -> dict:
    profiles:  list[dict] = []
    companies: list[dict] = []
    seen: set[str] = set()

    for r in dork_results:
        url     = r.get("url",     "")
        title   = r.get("title",   "")
        snippet = r.get("snippet", "")

        entity_id, entity_type = _extract_linkedin_entity(url)
        if not entity_id:
            continue
        key = f"{entity_type}:{entity_id.lower()}"
        if key in seen:
            continue
        seen.add(key)

        entry = {
            "entity_id":        entity_id,
            "entity_type":      entity_type,
            "url":              url,
            "title":            title[:120] if title else entity_id,
            "bio_snippet":      snippet[:250] if snippet else None,
            "connections_hint": _extract_connections_hint(snippet),
            "position_hint":    _extract_title_hint(snippet),
            "source":           "duckduckgo_dork",
            "confianza":        "media",
        }
        if entity_type == "company":
            companies.append(entry)
        else:
            profiles.append(entry)

    return {
        "platform":    "LinkedIn",
        "objetivo":    objetivo,
        "profiles":    profiles,
        "companies":   companies,
        "total_found": len(profiles) + len(companies),
        "raw_count":   len(dork_results),
    }


def persist_linkedin_data(linkedin_data: dict, objetivo: str) -> int:
    from models import db
    from models.osint_graph import get_or_create_node, create_edge

    if not linkedin_data.get("profiles") and not linkedin_data.get("companies"):
        return 0

    session  = db.session
    created  = 0
    slug_obj = objetivo.lower().replace(" ", "_")

    person, _ = get_or_create_node(
        session, "person", slug_obj, objetivo, "target",
        {"fuente_enriquecimiento": "linkedin_dork"},
    )
    platform_node, _ = get_or_create_node(
        session, "platform", "linkedin_platform", "LinkedIn", "linkedin_platform",
        {"url": "https://linkedin.com", "color_brand": "#0A66C2"},
    )

    for p in linkedin_data.get("profiles", []):
        profile_node, is_new = get_or_create_node(
            session,
            type  = "social_profile",
            value = p["url"],
            label = p.get("title") or p["entity_id"],
            group = "linkedin_profile",
            metadata_dict = {
                "entity_id":        p["entity_id"],
                "connections_hint": p.get("connections_hint", ""),
                "position_hint":    p.get("position_hint", ""),
                "fuente":           "duckduckgo_dork",
                "confianza":        "media",
            },
        )
        if is_new:
            created += 1
        create_edge(session, person, profile_node, "TIENE_PERFIL",
                    {"fuente": "linkedin_dork", "plataforma": "LinkedIn"})
        create_edge(session, profile_node, platform_node, "PERTENECE_A",
                    {"fuente": "linkedin_dork"})

    for c in linkedin_data.get("companies", []):
        org_node, is_new = get_or_create_node(
            session,
            type  = "organization",
            value = c["url"],
            label = c.get("title") or c["entity_id"],
            group = "linkedin_company",
            metadata_dict = {
                "entity_id": c["entity_id"],
                "fuente":    "duckduckgo_dork",
                "confianza": "media",
            },
        )
        if is_new:
            created += 1
        create_edge(session, person, org_node, "VINCULADO_A",
                    {"fuente": "linkedin_dork", "tipo": "empresa"})
        create_edge(session, org_node, platform_node, "PERTENECE_A",
                    {"fuente": "linkedin_dork"})

    session.commit()
    return created
