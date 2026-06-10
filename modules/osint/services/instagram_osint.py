"""services/instagram_osint.py — Extrae perfiles de Instagram desde resultados DDG."""
from __future__ import annotations

import re

_INSTAGRAM_SYSTEM_PATHS = frozenset({
    "p", "reel", "reels", "stories", "explore", "accounts",
    "api", "login", "logout", "oauth", "privacy", "legal",
    "about", "help", "press", "developers", "direct", "hashtag",
    "shop", "tv", "ar",
})


def _extract_instagram_username(url: str) -> str | None:
    m = re.search(
        r'instagram\.com/([a-zA-Z0-9_.]{1,60})(?:/|$|\?|#)',
        url, re.IGNORECASE,
    )
    if m:
        username = m.group(1)
        if username.lower() not in _INSTAGRAM_SYSTEM_PATHS:
            return username
    return None


def _extract_follower_hint(snippet: str) -> str | None:
    if not snippet:
        return None
    m = re.search(r'([\d,.]+[KkMm]?)\s*(?:[Ff]ollowers?|seguidores)', snippet)
    return m.group(0)[:40] if m else None


def _extract_posts_hint(snippet: str) -> str | None:
    if not snippet:
        return None
    m = re.search(r'([\d,.]+[KkMm]?)\s*(?:[Pp]osts?|[Pp]ublicaciones?|[Ff]otos?)', snippet)
    return m.group(0)[:40] if m else None


def extract_instagram_profiles(dork_results: list[dict], objetivo: str) -> dict:
    profiles: list[dict] = []
    seen_usernames: set[str] = set()

    for r in dork_results:
        url     = r.get("url",     "")
        title   = r.get("title",   "")
        snippet = r.get("snippet", "")

        username = _extract_instagram_username(url)
        if not username:
            continue
        if username.lower() in seen_usernames:
            continue
        seen_usernames.add(username.lower())

        profiles.append({
            "username":      username,
            "url":           f"https://instagram.com/{username}",
            "title":         title[:120] if title else f"@{username} en Instagram",
            "bio_snippet":   snippet[:250] if snippet else None,
            "follower_hint": _extract_follower_hint(snippet),
            "posts_hint":    _extract_posts_hint(snippet),
            "source":        "duckduckgo_dork",
            "confianza":     "media",
        })

    return {
        "platform":    "Instagram",
        "objetivo":    objetivo,
        "profiles":    profiles,
        "total_found": len(profiles),
        "raw_count":   len(dork_results),
    }


def persist_instagram_profiles(instagram_data: dict, objetivo: str) -> int:
    from models import db
    from models.osint_graph import get_or_create_node, create_edge

    if not instagram_data.get("profiles"):
        return 0

    session  = db.session
    created  = 0
    slug_obj = objetivo.lower().replace(" ", "_")

    person, _ = get_or_create_node(
        session, "person", slug_obj, objetivo, "target",
        {"fuente_enriquecimiento": "instagram_dork"},
    )
    platform_node, _ = get_or_create_node(
        session, "platform", "instagram_platform", "Instagram", "instagram_platform",
        {"url": "https://instagram.com", "color_brand": "#E1306C"},
    )

    for p in instagram_data["profiles"]:
        profile_node, is_new = get_or_create_node(
            session,
            type  = "social_profile",
            value = p["url"],
            label = f"@{p['username']}",
            group = "instagram_profile",
            metadata_dict = {
                "username":      p["username"],
                "bio_snippet":   p.get("bio_snippet", ""),
                "follower_hint": p.get("follower_hint", ""),
                "posts_hint":    p.get("posts_hint", ""),
                "fuente":        "duckduckgo_dork",
                "confianza":     "media",
            },
        )
        if is_new:
            created += 1
        create_edge(session, person, profile_node, "TIENE_CUENTA_EN",
                    {"fuente": "instagram_dork", "plataforma": "Instagram"})
        create_edge(session, profile_node, platform_node, "PERTENECE_A",
                    {"fuente": "instagram_dork"})

    if instagram_data["profiles"]:
        create_edge(session, person, platform_node, "ACTIVO_EN",
                    {"perfiles_encontrados": instagram_data["total_found"]})

    session.commit()
    return created
