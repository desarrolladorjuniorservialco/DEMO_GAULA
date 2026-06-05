"""
engines/dork_engine.py — Motor de Dorking Universal.

Movido desde modules/osint/services/search_engine.py.
El modulo services mantiene un shim de re-exportacion para compatibilidad.

Usa DuckDuckGo como proxy de busqueda para evitar requests directas a redes
sociales que bloquean bots. Aplica Google Dork: site:{dominio} "{objetivo}".
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from duckduckgo_search import DDGS
    from duckduckgo_search.exceptions import DuckDuckGoSearchException
    try:
        from duckduckgo_search.exceptions import RatelimitException
    except ImportError:
        RatelimitException = DuckDuckGoSearchException
    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False
    DuckDuckGoSearchException = Exception
    RatelimitException = Exception

PLATFORM_DOMAINS: dict[str, str] = {
    "x":         "x.com",
    "twitter":   "twitter.com",
    "tiktok":    "tiktok.com",
    "facebook":  "facebook.com",
    "instagram": "instagram.com",
    "linkedin":  "linkedin.com",
    "reddit":    "reddit.com",
    "github":    "github.com",
}

INTER_SEARCH_DELAY = 1.5


def _build_dork(objetivo: str, domain: str) -> str:
    return f'site:{domain} "{objetivo}"'


def _search_single_platform(objetivo: str, platform: str, max_results: int = 50) -> dict:
    """Ejecuta una busqueda DDG para UNA plataforma."""
    domain  = PLATFORM_DOMAINS.get(platform.lower(), platform)
    query   = _build_dork(objetivo, domain)
    results = []
    errors  = []

    if not DDG_AVAILABLE:
        errors.append(f"{platform}: duckduckgo-search no instalado.")
        return {"platform": platform, "domain": domain, "query": query,
                "results": results, "errors": errors}

    try:
        with DDGS() as ddgs:
            raw = ddgs.text(query, max_results=max_results) or []
            for r in raw:
                results.append({
                    "platform": platform,
                    "domain":   domain,
                    "title":    r.get("title",  ""),
                    "url":      r.get("href",   ""),
                    "snippet":  r.get("body",   ""),
                })
            time.sleep(INTER_SEARCH_DELAY)
    except RatelimitException:
        errors.append(
            f"{platform}: Rate limit 429 en DuckDuckGo — "
            "espera 60 segundos antes de reintentar esta plataforma."
        )
    except DuckDuckGoSearchException as exc:
        errors.append(f"{platform}: Error de busqueda DDG ({exc}).")
    except Exception as exc:
        errors.append(f"{platform}: Error inesperado ({exc}).")

    return {"platform": platform, "domain": domain, "query": query,
            "results": results, "errors": errors}


def ejecutar_dork_universal(
    objetivo: str,
    plataformas_lista: list[str],
    max_results: int = 50,
) -> dict[str, dict]:
    """
    Ejecuta busquedas de dorking CONCURRENTES para multiples plataformas.

    Returns:
        Dict keyed by platform: {platform, domain, query, results[], errors[]}
    """
    plataformas_validas = [p for p in plataformas_lista if p.lower() in PLATFORM_DOMAINS]
    all_results: dict[str, dict] = {}
    workers = min(len(plataformas_validas), 3) if plataformas_validas else 1

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_search_single_platform, objetivo, p, max_results): p
            for p in plataformas_validas
        }
        for future in as_completed(futures, timeout=90):
            platform = futures[future]
            try:
                all_results[platform] = future.result(timeout=45)
            except Exception as exc:
                all_results[platform] = {
                    "platform": platform,
                    "domain":   PLATFORM_DOMAINS.get(platform.lower(), ""),
                    "query":    _build_dork(objetivo, PLATFORM_DOMAINS.get(platform.lower(), "")),
                    "results":  [],
                    "errors":   [f"Future timeout/error: {exc}"],
                }

    for p in plataformas_lista:
        if p.lower() not in PLATFORM_DOMAINS:
            all_results[p] = {
                "platform": p, "domain": "", "query": "",
                "results":  [], "errors": [f"'{p}' no esta en PLATFORM_DOMAINS."],
            }

    return all_results
