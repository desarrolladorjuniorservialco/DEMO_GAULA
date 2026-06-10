"""connectors/web_dork.py — Helper reutilizable de dorking DuckDuckGo."""
from __future__ import annotations

import time
from typing import Any

try:
    from duckduckgo_search import DDGS
    from duckduckgo_search.exceptions import DuckDuckGoSearchException
    try:
        from duckduckgo_search.exceptions import RatelimitException
    except ImportError:
        RatelimitException = DuckDuckGoSearchException
    _AVAILABLE = True
except ImportError:
    DDGS = None  # type: ignore
    DuckDuckGoSearchException = Exception  # type: ignore
    RatelimitException = Exception  # type: ignore
    _AVAILABLE = False


def run_dork(
    queries: list[str],
    *,
    max_results: int = 10,
    sleep_between: float = 1.5,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Ejecuta dorks DuckDuckGo. Devuelve (resultados, errores). Nunca lanza."""
    if not _AVAILABLE:
        return [], ["duckduckgo-search no disponible."]

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_urls: set[str] = set()

    try:
        with DDGS() as ddgs:
            for query in queries:
                try:
                    for r in (ddgs.text(query, max_results=max_results) or []):
                        url = r.get("href", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            results.append({
                                "title":   r.get("title", "")[:120],
                                "url":     url,
                                "snippet": r.get("body", "")[:250],
                            })
                    if sleep_between:
                        time.sleep(sleep_between)
                except RatelimitException:
                    errors.append("DDG: rate limit — intenta en 60s.")
                    break
                except DuckDuckGoSearchException as exc:
                    errors.append(f"DDG: {exc}")
    except Exception as exc:  # noqa: BLE001 — el helper nunca debe propagar
        errors.append(f"DDG: {exc}")

    return results, errors
