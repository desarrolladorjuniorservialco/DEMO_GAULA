import re


def _extract_tiktok_username(url: str) -> str | None:
    m = re.search(
        r'tiktok\.com/@([a-zA-Z0-9_.]{1,64})(?:/|$|\?|#)',
        url, re.IGNORECASE,
    )
    return m.group(1) if m else None


def _extract_video_count_hint(snippet: str) -> str | None:
    if not snippet:
        return None
    m = re.search(
        r'([\d,.]+[KkMm]?)\s*(?:[Vv]ideos?|[Ll]ikes?|[Ff]ollowers?|seguidores)',
        snippet,
    )
    return m.group(0)[:40] if m else None


def _extract_hashtags(snippet: str) -> list[str]:
    if not snippet:
        return []
    return re.findall(r'#([a-zA-Z0-9_]{2,40})', snippet)[:10]


def extract_tiktok_profiles(dork_results: list[dict], objetivo: str) -> dict:
    profiles:       list[dict] = []
    seen_usernames: set[str]   = set()
    all_hashtags:   list[str]  = []

    for r in dork_results:
        url     = r.get("url",     "")
        title   = r.get("title",   "")
        snippet = r.get("snippet", "")

        username = _extract_tiktok_username(url)
        if not username:
            continue
        if username.lower() in seen_usernames:
            continue
        seen_usernames.add(username.lower())

        tags = _extract_hashtags(snippet)
        all_hashtags.extend(tags)

        profiles.append({
            "username":   username,
            "url":        f"https://tiktok.com/@{username}",
            "title":      title[:120] if title else f"@{username} en TikTok",
            "bio_snippet": snippet[:250] if snippet else None,
            "stats_hint": _extract_video_count_hint(snippet),
            "hashtags":   tags,
            "source":     "duckduckgo_dork",
            "confianza":  "media",
        })

    seen_tags: set[str] = set()
    unique_tags = [t for t in all_hashtags if not (t in seen_tags or seen_tags.add(t))]  # type: ignore

    return {
        "platform":            "TikTok",
        "objetivo":            objetivo,
        "profiles":            profiles,
        "total_found":         len(profiles),
        "raw_count":           len(dork_results),
        "hashtags_detectados": unique_tags[:15],
    }


def persist_tiktok_profiles(tiktok_data: dict, objetivo: str) -> int:
    from models import db
    from models.osint_graph import get_or_create_node, create_edge

    if not tiktok_data.get("profiles"):
        return 0

    session  = db.session
    created  = 0
    slug_obj = objetivo.lower().replace(" ", "_")

    person, _ = get_or_create_node(
        session, "person", slug_obj, objetivo, "target",
        {"fuente_enriquecimiento": "tiktok_dork"},
    )

    platform_node, _ = get_or_create_node(
        session, "platform", "tiktok_platform", "TikTok", "tiktok_platform",
        {"url": "https://tiktok.com", "color_brand": "#ff0050"},
    )

    for p in tiktok_data["profiles"]:
        profile_node, is_new = get_or_create_node(
            session,
            type  = "social_profile",
            value = p["url"],
            label = f"@{p['username']}",
            group = "tiktok_profile",
            metadata_dict = {
                "username":    p["username"],
                "bio_snippet": p.get("bio_snippet", ""),
                "stats_hint":  p.get("stats_hint", ""),
                "hashtags":    p.get("hashtags", []),
                "fuente":      "duckduckgo_dork",
                "confianza":   "media",
            },
        )
        if is_new:
            created += 1

        create_edge(session, person, profile_node, "TIENE_CUENTA_EN",
                    {"fuente": "tiktok_dork", "plataforma": "TikTok"})
        create_edge(session, profile_node, platform_node, "PERTENECE_A",
                    {"fuente": "tiktok_dork"})

    if tiktok_data["profiles"]:
        create_edge(session, person, platform_node, "ACTIVO_EN",
                    {"perfiles_encontrados": tiktok_data["total_found"],
                     "hashtags_detectados":  tiktok_data.get("hashtags_detectados", [])})

    session.commit()
    return created
