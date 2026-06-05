"""
scrapers/browser/playwright.py — Scraper hibrido de Facebook con Playwright.

Movido desde modules/osint/social/scrapers/facebook_playwright.py.
El modulo original mantiene un shim de re-exportacion para compatibilidad.
"""
import re
import json
import urllib.parse

TIMEOUT_MS    = 18000
NOT_PUBLIC    = "No publico"
NOT_AVAILABLE = "No disponible"

_EMPTY_INTEL = {
    "ubicacion_actual": NOT_PUBLIC,
    "origen":           NOT_PUBLIC,
    "trabajo":          NOT_AVAILABLE,
    "educacion":        NOT_AVAILABLE,
    "bio":              NOT_AVAILABLE,
    "relacion":         NOT_AVAILABLE,
}

_FB_NON_PROFILE = re.compile(
    r'facebook\.com/'
    r'(?:search|login|logout|groups|events|pages|marketplace|help|'
    r'privacy|settings|notifications|messages|checkpoint|recover|'
    r'video|photo|stories|watch|gaming|fundraisers|jobs|live|'
    r'share|sharer|dialog|plugins|hashtag|reel)/',
    re.IGNORECASE,
)


def _dork_facebook_url(query: str) -> str | None:
    """Usa DuckDuckGo para encontrar la URL real de un perfil de Facebook."""
    try:
        from modules.osint.engines.dork_engine import ejecutar_dork_universal
        results = ejecutar_dork_universal(query, ["facebook"], max_results=5)
        for r in results.get("facebook", {}).get("results", []):
            url = r.get("url", "")
            if not url or "facebook.com/" not in url.lower():
                continue
            if _FB_NON_PROFILE.search(url):
                continue
            path_segments = [s for s in url.split("/") if s and "facebook.com" not in s]
            if path_segments:
                return url
    except Exception:
        pass
    return None


def _build_target(query: str) -> tuple[str, str]:
    q = query.strip()
    if " " in q:
        encoded = urllib.parse.quote(q)
        return f"https://www.facebook.com/search/people/?q={encoded}", "search"
    return f"https://www.facebook.com/{q}", "profile"


def _extract_og(html: str) -> dict:
    og = {}
    for tag in re.findall(r"<meta\s+([^>]+?)/?>\s*", html, re.IGNORECASE | re.DOTALL):
        prop    = re.search(r'(?:property|name)\s*=\s*["\']([^"\']+)["\']', tag, re.IGNORECASE)
        content = re.search(r'content\s*=\s*["\']([^"\']*)["\']',           tag, re.IGNORECASE)
        if prop and content and prop.group(1).lower().startswith("og:"):
            og[prop.group(1).lower()] = content.group(1)
    return og


def _is_login_wall(url: str, html: str) -> bool:
    if any(kw in url.lower() for kw in ("login", "checkpoint", "recover", "disabled")):
        return True
    sample = html[:5000].lower()
    return any(kw in sample for kw in (
        "you must log in", "log into facebook",
        "create new account", "iniciar sesion", "crear cuenta nueva",
    ))


def _extract_intel(page, og: dict) -> dict:
    intel = dict(_EMPTY_INTEL)
    body_text = ""
    try:
        body_text = page.evaluate("document.body.innerText") or ""
    except Exception:
        pass

    PATTERNS: dict[str, list[str]] = {
        "ubicacion_actual": [
            r"(?:Lives in|Vive en|Ciudad actual|Current [Cc]ity)[:\s]+([^\n]{2,80})",
            r"(?:Actualmente vive en)[:\s]+([^\n]{2,80})",
        ],
        "origen": [
            r"(?:From|De|Hometown|Ciudad de origen)[:\s]+([^\n]{2,80})",
        ],
        "trabajo": [
            r"(?:Works at|Trabaja en|Employer|Work)[:\s]+([^\n]{2,80})",
        ],
        "educacion": [
            r"(?:Studied at|Estudio en|Went to|School|University)[:\s]+([^\n]{2,80})",
        ],
        "relacion": [
            r"(?:Relationship status|Estado sentimental)[:\s]+([^\n]{2,60})",
        ],
    }

    for field, field_patterns in PATTERNS.items():
        for pattern in field_patterns:
            try:
                m = re.search(pattern, body_text, re.IGNORECASE)
                if m:
                    value = m.group(1).strip()[:120]
                    if value:
                        intel[field] = value
                        break
            except Exception:
                pass

    try:
        scripts: list[str] = page.evaluate(
            'Array.from(document.querySelectorAll(\'script[type="application/ld+json"]\')'
            ').map(s => s.textContent)'
        ) or []
        for raw in scripts:
            try:
                data = json.loads(raw)
                if not isinstance(data, dict):
                    continue
                if data.get("description") and intel["bio"] == NOT_AVAILABLE:
                    intel["bio"] = data["description"][:200]
                addr = data.get("address", {})
                if isinstance(addr, dict):
                    locality = addr.get("addressLocality", "")
                    if locality and intel["ubicacion_actual"] == NOT_PUBLIC:
                        intel["ubicacion_actual"] = locality
            except Exception:
                pass
    except Exception:
        pass

    if intel["bio"] == NOT_AVAILABLE and og.get("og:description"):
        intel["bio"] = og["og:description"][:200]
    return intel


def _load_mock_data(query: str) -> dict:
    q          = query.strip()
    slug       = q.replace(" ", "")
    encoded    = urllib.parse.quote(q)
    query_type = "search" if " " in q else "profile"
    return {
        "username": query, "query_type": query_type, "platform": "facebook",
        "scraped": False, "is_mock": True, "blocked": True, "status_code": None,
        "og": {}, "profile_image": None,
        "profile_url":  f"https://www.facebook.com/{slug}",
        "search_url":   f"https://www.facebook.com/search/people/?q={encoded}",
        "mobile_url":   f"https://m.facebook.com/{slug}",
        "profile": {"name": f"{q.title()} [DEMO]", "location": "Ciudad de Mexico, Mexico",
                    "work": "Consultoria Digital S.A.",
                    "education": "Universidad Nacional Autonoma de Mexico",
                    "friends_count": 487},
        "intel": {"ubicacion_actual": "Ciudad de Mexico, Mexico",
                  "origen": "Guadalajara, Jalisco",
                  "trabajo": "Consultoria Digital S.A.", "educacion": "UNAM",
                  "bio": "Apasionado por la tecnologia.", "relacion": NOT_AVAILABLE},
        "recent_posts": [],
        "mutual_connections": ["Ana Garcia", "Roberto Sanchez"],
        "email_hints": [f"{slug}@protonmail.com", f"{slug}@gmail.com"],
    }


def scrape_facebook_profile(query: str) -> tuple[dict, list[str]]:
    """Scraper hibrido de Facebook. Retorna (result_dict, errors_list)."""
    errors: list[str] = []
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        q       = query.strip()
        slug    = q.replace(" ", "")
        encoded = urllib.parse.quote(q)

        dork_url = _dork_facebook_url(query)
        if dork_url:
            url, query_type = dork_url, "dork_profile"
            errors.append(f"Facebook: URL encontrada via dorking: {dork_url[:80]}")
        else:
            url, query_type = _build_target(query)

        with sync_playwright() as p:
            with p.chromium.launch(headless=True) as browser:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    locale="es-MX",
                    timezone_id="America/Mexico_City",
                )
                page = context.new_page()
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                    page.wait_for_timeout(2000)
                except PWTimeout:
                    errors.append("Facebook (Playwright): timeout — datos DEMO.")
                    return _load_mock_data(query), errors

                current_url = page.url
                html        = page.content()
                if _is_login_wall(current_url, html):
                    errors.append("Facebook: login wall detectado — datos DEMO.")
                    return _load_mock_data(query), errors

                og            = _extract_og(html)
                profile_image = og.get("og:image") or None
                intel         = _extract_intel(page, og)

        profile_name = og.get("og:title", q)
        return {
            "username": query, "query_type": query_type, "platform": "facebook",
            "scraped": True, "is_mock": False, "blocked": False, "status_code": 200,
            "og": og, "profile_image": profile_image,
            "profile_url":  f"https://www.facebook.com/{slug}",
            "search_url":   f"https://www.facebook.com/search/people/?q={encoded}",
            "mobile_url":   f"https://m.facebook.com/{slug}",
            "profile": {"name": profile_name,
                        "location":  intel.get("ubicacion_actual", NOT_PUBLIC),
                        "work":      intel.get("trabajo",          NOT_AVAILABLE),
                        "education": intel.get("educacion",        NOT_AVAILABLE),
                        "friends_count": None},
            "intel": intel, "recent_posts": [], "mutual_connections": [], "email_hints": [],
        }, errors

    except ImportError:
        errors.append("Facebook: Playwright no instalado — datos DEMO. Ejecuta: playwright install chromium")
        return _load_mock_data(query), errors
    except Exception as exc:
        errors.append(f"Facebook (Playwright): error inesperado ({exc}) — datos DEMO.")
        return _load_mock_data(query), errors
