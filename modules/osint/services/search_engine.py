"""
search_engine.py — Motor de Dorking Universal
==============================================
Usa DuckDuckGo como proxy de búsqueda para evitar requests directas a redes
sociales que bloquean bots. Aplica Google Dork: site:{dominio} "{objetivo}".

Ventajas:
- Sin autenticación requerida en plataformas objetivo.
- Resultados cacheados por DDG → menor exposición del servidor.
- Rate limiting nativo con manejo explícito de HTTP 429.

Limitaciones:
- Max ~50 resultados por búsqueda (límite de DDG).
- DDG puede aplicar rate limit; implementar back-off si se detecta.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from duckduckgo_search import DDGS
    from duckduckgo_search.exceptions import DuckDuckGoSearchException
    # RatelimitException existe en versiones >=6 — import con fallback
    try:
        from duckduckgo_search.exceptions import RatelimitException
    except ImportError:
        RatelimitException = DuckDuckGoSearchException
    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False
    DuckDuckGoSearchException = Exception
    RatelimitException = Exception

# Mapa de plataformas soportadas → dominio canónico para el dork
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

# Tiempo de espera entre búsquedas para no saturar DDG (segundos)
INTER_SEARCH_DELAY = 1.5


def _build_dork(objetivo: str, domain: str) -> str:
    """Construye la query de dorking para DuckDuckGo."""
    return f'site:{domain} "{objetivo}"'


def _search_single_platform(
    objetivo: str,
    platform: str,
    max_results: int = 50,
) -> dict:
    """
    Ejecuta una búsqueda DDG para UNA plataforma.
    Maneja rate limit (429) y errores de red de forma granular.
    Retorna dict con platform, query, results[], errors[].
    """
    domain   = PLATFORM_DOMAINS.get(platform.lower(), platform)
    query    = _build_dork(objetivo, domain)
    results  = []
    errors   = []

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
        errors.append(f"{platform}: Error de búsqueda DDG ({exc}).")
    except Exception as exc:
        errors.append(f"{platform}: Error inesperado ({exc}).")

    return {
        "platform": platform,
        "domain":   domain,
        "query":    query,
        "results":  results,
        "errors":   errors,
    }


def ejecutar_dork_universal(
    objetivo: str,
    plataformas_lista: list[str],
    max_results: int = 50,
) -> dict[str, dict]:
    """
    Ejecuta búsquedas de dorking CONCURRENTES para múltiples plataformas.

    Args:
        objetivo:          Nombre de usuario, nombre completo o alias a investigar.
        plataformas_lista: Lista de claves de PLATFORM_DOMAINS (ej. ['x', 'tiktok']).
        max_results:       Máximo de resultados por plataforma (límite DDG ~50).

    Returns:
        Dict keyed by platform: {platform: {platform, domain, query, results[], errors[]}}

    Notas de rate limiting:
        - DDG bloquea si se lanzan demasiadas búsquedas en ráfaga.
        - max_workers=3 reduce la probabilidad de 429.
        - INTER_SEARCH_DELAY=1.5s dentro de cada búsqueda.
        - Si se recibe 429, el resultado incluye el error en errors[] pero no colapsa.
    """
    plataformas_validas = [
        p for p in plataformas_lista
        if p.lower() in PLATFORM_DOMAINS
    ]

    all_results: dict[str, dict] = {}

    # Limitamos workers para respetar el rate limit de DDG
    workers = min(len(plataformas_validas), 3)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures: dict = {
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

    # Plataformas no soportadas
    for p in plataformas_lista:
        if p.lower() not in PLATFORM_DOMAINS:
            all_results[p] = {
                "platform": p,
                "domain":   "",
                "query":    "",
                "results":  [],
                "errors":   [f"'{p}' no está en PLATFORM_DOMAINS."],
            }

    return all_results
