import re

_X_SYSTEM_PATHS = frozenset({
    "home", "search", "explore", "notifications", "messages", "settings",
    "i", "intent", "hashtag", "compose", "login", "logout", "signup",
    "privacy", "tos", "about", "jobs", "help", "status", "account",
    "oauth", "widgets", "twitter", "x",
})


def _extract_username(url: str) -> str | None:
    m = re.search(
        r'(?:x\.com|twitter\.com)/([a-zA-Z0-9_]{1,50})(?:/|$|\?|#)',
        url, re.IGNORECASE,
    )
    if m:
        username = m.group(1)
        if username.lower() not in _X_SYSTEM_PATHS:
            return username
    return None


def _extract_follower_hint(snippet: str) -> str | None:
    if not snippet:
        return None
    m = re.search(r'([\d,.]+[KkMm]?)\s*(?:Followers|followers|seguidores)', snippet)
    return m.group(0)[:40] if m else None


def extract_x_profiles(dork_results: list[dict], objetivo: str) -> dict:
    profiles: list[dict] = []
    seen_usernames: set[str] = set()

    for r in dork_results:
        url     = r.get("url",     "")
        title   = r.get("title",   "")
        snippet = r.get("snippet", "")

        username = _extract_username(url)
        if not username:
            continue
        if username.lower() in seen_usernames:
            continue
        seen_usernames.add(username.lower())

        profiles.append({
            "username":      username,
            "url":           f"https://x.com/{username}",
            "title":         title[:120] if title else f"@{username} en X",
            "bio_snippet":   snippet[:250] if snippet else None,
            "follower_hint": _extract_follower_hint(snippet),
            "source":        "duckduckgo_dork",
            "confianza":     "media",
        })

    intel_summary = next(
        (p["bio_snippet"] for p in profiles if p.get("bio_snippet")), None
    )

    return {
        "platform":      "X",
        "objetivo":      objetivo,
        "profiles":      profiles,
        "total_found":   len(profiles),
        "raw_count":     len(dork_results),
        "intel_summary": intel_summary,
    }


def persist_x_profiles(x_data: dict, objetivo: str) -> int:
    from models import db
    from models.osint_graph import get_or_create_node, create_edge

    if not x_data.get("profiles"):
        return 0

    session  = db.session
    created  = 0
    slug_obj = objetivo.lower().replace(" ", "_")

    person, _ = get_or_create_node(
        session, "person", slug_obj, objetivo, "target",
        {"fuente_enriquecimiento": "x_dork"},
    )

    platform_node, _ = get_or_create_node(
        session, "platform", "x_platform", "X (Twitter)", "x_platform",
        {"url": "https://x.com", "color_brand": "#1DA1F2"},
    )

    for p in x_data["profiles"]:
        profile_node, is_new = get_or_create_node(
            session,
            type  = "social_profile",
            value = p["url"],
            label = f"@{p['username']}",
            group = "x_profile",
            metadata_dict = {
                "username":      p["username"],
                "bio_snippet":   p.get("bio_snippet", ""),
                "follower_hint": p.get("follower_hint", ""),
                "fuente":        "duckduckgo_dork",
                "confianza":     "media",
            },
        )
        if is_new:
            created += 1

        create_edge(session, person, profile_node, "TIENE_CUENTA_EN",
                    {"fuente": "x_dork", "plataforma": "X"})
        create_edge(session, profile_node, platform_node, "PERTENECE_A",
                    {"fuente": "x_dork"})

    if x_data["profiles"]:
        create_edge(session, person, platform_node, "ACTIVO_EN",
                    {"perfiles_encontrados": x_data["total_found"]})

    session.commit()
    return created
