import re
import json
import urllib.parse

TIMEOUT_MS    = 18000       # ms — mayor margen para páginas pesadas de FB
NOT_PUBLIC    = "No público"
NOT_AVAILABLE = "No disponible"

# Valores por defecto para el bloque de inteligencia
_EMPTY_INTEL = {
    "ubicacion_actual": NOT_PUBLIC,
    "origen":           NOT_PUBLIC,
    "trabajo":          NOT_AVAILABLE,
    "educacion":        NOT_AVAILABLE,
    "bio":              NOT_AVAILABLE,
    "relacion":         NOT_AVAILABLE,
}


# ─── Routing ─────────────────────────────────────────────────

# Rutas de Facebook que NO son perfiles de usuario
_FB_NON_PROFILE = re.compile(
    r'facebook\.com/'
    r'(?:search|login|logout|groups|events|pages|marketplace|help|'
    r'privacy|settings|notifications|messages|checkpoint|recover|'
    r'video|photo|stories|watch|gaming|fundraisers|jobs|live|'
    r'share|sharer|dialog|plugins|hashtag|reel)/',
    re.IGNORECASE,
)


def _dork_facebook_url(query: str) -> str | None:
    """
    Paso 1 híbrido: usa DuckDuckGo para encontrar la URL real de un perfil
    de Facebook ANTES de lanzar Playwright.

    Ventaja: evita llegar directamente al login wall de facebook.com raíz;
    DDG devuelve URLs de perfiles públicos cacheadas que Playwright puede
    cargar con mayor probabilidad de ver contenido real.

    Retorna la primera URL de perfil válida encontrada, o None.
    """
    try:
        from modules.osint.services.search_engine import ejecutar_dork_universal
        results = ejecutar_dork_universal(query, ["facebook"], max_results=5)
        for r in results.get("facebook", {}).get("results", []):
            url = r.get("url", "")
            if not url:
                continue
            if "facebook.com/" not in url.lower():
                continue
            if _FB_NON_PROFILE.search(url):
                continue
            # Debe tener al menos un segmento de ruta además del dominio
            path_segments = [s for s in url.split("/") if s and "facebook.com" not in s]
            if path_segments:
                return url
    except Exception:
        pass
    return None


def _build_target(query: str) -> tuple[str, str]:
    """
    Decide la URL a scrapear según el tipo de consulta.
    - Con espacios (nombre completo) → endpoint de búsqueda de personas codificado.
    - Sin espacios (alias/username)  → URL de perfil directo.
    Retorna (url, query_type).
    """
    q = query.strip()
    if " " in q:
        encoded = urllib.parse.quote(q)
        return f"https://www.facebook.com/search/people/?q={encoded}", "search"
    return f"https://www.facebook.com/{q}", "profile"


# ─── Extracción HTML ─────────────────────────────────────────

def _extract_og(html: str) -> dict:
    """
    Extrae todas las etiquetas Open Graph del HTML crudo.
    La imagen se obtiene siempre del atributo 'content' de og:image,
    no de etiquetas <img>, para evadir restricciones de carga.
    """
    og = {}
    for tag in re.findall(r"<meta\s+([^>]+?)/?>\s*", html, re.IGNORECASE | re.DOTALL):
        prop    = re.search(r'(?:property|name)\s*=\s*["\']([^"\']+)["\']', tag, re.IGNORECASE)
        content = re.search(r'content\s*=\s*["\']([^"\']*)["\']',           tag, re.IGNORECASE)
        if prop and content and prop.group(1).lower().startswith("og:"):
            og[prop.group(1).lower()] = content.group(1)
    return og


def _is_login_wall(url: str, html: str) -> bool:
    """Detecta si Facebook redirigió a login, checkpoint o pantalla de bloqueo."""
    if any(kw in url.lower() for kw in ("login", "checkpoint", "recover", "disabled")):
        return True
    sample = html[:5000].lower()
    return any(kw in sample for kw in (
        "you must log in", "log into facebook",
        "create new account", "iniciar sesión", "crear cuenta nueva",
    ))


# ─── Extracción de inteligencia profunda ─────────────────────

def _extract_intel(page, og: dict) -> dict:
    """
    Intenta extraer datos de perfil (intro/about) del DOM renderizado.

    Estrategia en 3 pasos:
    1. document.body.innerText con regex de patrones de etiqueta (EN + ES).
    2. Bloques JSON-LD <script> para datos estructurados.
    3. og:description como bio de respaldo.

    Cada extracción está aislada en try/except — nunca lanza excepciones.
    Valores no encontrados quedan como NOT_PUBLIC / NOT_AVAILABLE.
    """
    intel = dict(_EMPTY_INTEL)

    # ── Paso 1: pattern matching sobre texto renderizado ─────
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
            r"(?:From|De|Hometown|Ciudad de origen|Home [Tt]own)[:\s]+([^\n]{2,80})",
            r"(?:Lugar de origen|Originario de)[:\s]+([^\n]{2,80})",
        ],
        "trabajo": [
            r"(?:Works at|Trabaja en|Employer|Work)[:\s]+([^\n]{2,80})",
            r"(?:Cargo|Position)[:\s]+([^\n]{2,80})",
        ],
        "educacion": [
            r"(?:Studied at|Estudió en|Went to|School|University|College)[:\s]+([^\n]{2,80})",
            r"(?:Education|Educación)[:\s]+([^\n]{2,80})",
        ],
        "relacion": [
            r"(?:Relationship status|Estado sentimental)[:\s]+([^\n]{2,60})",
            r"(?:Married to|In a relationship with)[^\n]{0,60}",
            r"(?:Casad[ao] con|En una relación con)[^\n]{0,60}",
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

    # ── Paso 2: JSON-LD estructurado ─────────────────────────
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

    # ── Paso 3: og:description como bio de respaldo ──────────
    if intel["bio"] == NOT_AVAILABLE and og.get("og:description"):
        intel["bio"] = og["og:description"][:200]

    return intel


# ─── Mock data ───────────────────────────────────────────────

def _load_mock_data(query: str) -> dict:
    """
    Datos simulados estructurados que emulan una extracción exitosa.
    Activa el badge DEMO DATA en el template y siempre produce un grafo
    funcional para el módulo de Link Analysis.
    """
    q          = query.strip()
    slug       = q.replace(" ", "")
    encoded    = urllib.parse.quote(q)
    query_type = "search" if " " in q else "profile"

    return {
        "username":      query,
        "query_type":    query_type,
        "platform":      "facebook",
        "scraped":       False,
        "is_mock":       True,
        "blocked":       True,
        "status_code":   None,
        "og":            {},
        "profile_image": None,
        "profile_url":   f"https://www.facebook.com/{slug}",
        "search_url":    f"https://www.facebook.com/search/people/?q={encoded}",
        "mobile_url":    f"https://m.facebook.com/{slug}",
        "profile": {
            "name":          f"{q.title()} [DEMO]",
            "location":      "Ciudad de México, México",
            "work":          "Consultoría Digital S.A.",
            "education":     "Universidad Nacional Autónoma de México",
            "friends_count": 487,
        },
        "intel": {
            "ubicacion_actual": "Ciudad de México, México",
            "origen":           "Guadalajara, Jalisco",
            "trabajo":          "Consultoría Digital S.A. — Analista Senior",
            "educacion":        "UNAM — Ingeniería en Sistemas Computacionales",
            "bio":              "Apasionado por la tecnología y la seguridad informática. "
                                "Conferencista en eventos de ciberseguridad en LATAM.",
            "relacion":         NOT_AVAILABLE,
        },
        "recent_posts": [
            {
                "date":     "2024-03-10",
                "text":     "Acabo de llegar a #Guadalajara para la conferencia de seguridad informática.",
                "mentions": ["María López", "Carlos Mendez"],
                "location": "Guadalajara, Jalisco",
                "likes":    47,
            },
            {
                "date":     "2024-03-05",
                "text":     "Trabajando en el nuevo proyecto con el equipo de @ConsultoríaDigital",
                "mentions": ["Consultoría Digital"],
                "location": None,
                "likes":    23,
            },
            {
                "date":     "2024-02-20",
                "text":     f"Revisando reportes. Contacto: {slug}@protonmail.com",
                "mentions": [],
                "location": None,
                "likes":    8,
            },
        ],
        "mutual_connections": ["Ana García", "Roberto Sánchez", "Laura Torres"],
        "email_hints":        [f"{slug}@protonmail.com", f"{slug}@gmail.com"],
    }


# ─── Scraper principal ───────────────────────────────────────

def scrape_facebook_profile(query: str) -> tuple[dict, list[str]]:
    """
    Scraper híbrido de Facebook:

    Paso 1 — Dorking (DuckDuckGo):
        Busca 'site:facebook.com "{query}"' para obtener una URL real de perfil
        público sin tocar directamente el login wall de facebook.com.

    Paso 2 — Playwright (Chromium headless):
        Carga la URL obtenida (o la URL por defecto si dorking falla),
        extrae OG tags, intel profunda y bio.

    Paso 3 — Mock fallback:
        Si Playwright falla, devuelve datos DEMO estructurados.

    Retorna (result_dict, errors_list) compatible con social/routes.py.
    """
    errors: list[str] = []

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        # ── Paso 1: dorking para URL real ────────────────────
        q       = query.strip()
        slug    = q.replace(" ", "")
        encoded = urllib.parse.quote(q)

        dork_url = _dork_facebook_url(query)
        if dork_url:
            url        = dork_url
            query_type = "dork_profile"
            errors.append(
                f"Facebook: URL real encontrada via dorking — "
                f"cargando con Playwright: {dork_url[:80]}"
            )
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
                    page.wait_for_timeout(2000)  # espera hidratación JS
                except PWTimeout:
                    errors.append("Facebook (Playwright): timeout — cargando datos DEMO.")
                    return _load_mock_data(query), errors

                current_url = page.url
                html        = page.content()

                if _is_login_wall(current_url, html):
                    errors.append(
                        f"Facebook ({'búsqueda' if query_type == 'search' else 'perfil'}): "
                        "login wall — mostrando datos DEMO con inteligencia profunda de ejemplo."
                    )
                    return _load_mock_data(query), errors

                # Extracción OG (imagen via content attribute, no <img>)
                og            = _extract_og(html)
                profile_image = og.get("og:image") or None

                # Extracción profunda de inteligencia
                intel = _extract_intel(page, og)

        profile_name = og.get("og:title", q)

        return {
            "username":      query,
            "query_type":    query_type,
            "platform":      "facebook",
            "scraped":       True,
            "is_mock":       False,
            "blocked":       False,
            "status_code":   200,
            "og":            og,
            "profile_image": profile_image,
            "profile_url":   f"https://www.facebook.com/{slug}",
            "search_url":    f"https://www.facebook.com/search/people/?q={encoded}",
            "mobile_url":    f"https://m.facebook.com/{slug}",
            "profile": {
                "name":          profile_name,
                "location":      intel.get("ubicacion_actual", NOT_PUBLIC),
                "work":          intel.get("trabajo",          NOT_AVAILABLE),
                "education":     intel.get("educacion",        NOT_AVAILABLE),
                "friends_count": None,
            },
            "intel":             intel,
            "recent_posts":      [],
            "mutual_connections": [],
            "email_hints":       [],
        }, errors

    except ImportError:
        errors.append(
            "Facebook: Playwright no instalado — datos DEMO. "
            "Ejecuta: playwright install chromium"
        )
        return _load_mock_data(query), errors

    except Exception as exc:
        errors.append(f"Facebook (Playwright): error inesperado ({exc}) — datos DEMO.")
        return _load_mock_data(query), errors
