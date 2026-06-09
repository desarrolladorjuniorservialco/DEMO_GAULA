"""scrapers/parsers/bs4_parser.py — BeautifulSoup4 HTML parser wrapper."""
from __future__ import annotations

from typing import Any

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False


class Bs4Parser:
    """Wrapper ligero sobre BeautifulSoup4 para extracción de datos HTML."""

    def __init__(self, html: str, parser: str = "html.parser") -> None:
        if not _BS4_AVAILABLE:
            raise ImportError("bs4 no instalado — pip install beautifulsoup4")
        self._soup = BeautifulSoup(html, parser)

    def extract_text(self, selector: str) -> list[str]:
        return [el.get_text(strip=True) for el in self._soup.select(selector)]

    def extract_attr(self, selector: str, attr: str) -> list[str]:
        return [
            el.get(attr, "")
            for el in self._soup.select(selector)
            if el.get(attr)
        ]

    def extract_meta(self, prop: str) -> str | None:
        tag = self._soup.find("meta", attrs={"property": prop}) or \
              self._soup.find("meta", attrs={"name": prop})
        if tag:
            return tag.get("content")
        return None

    def extract_og(self) -> dict[str, str]:
        og: dict[str, str] = {}
        for tag in self._soup.find_all("meta"):
            prop = tag.get("property") or tag.get("name") or ""
            if prop.lower().startswith("og:"):
                og[prop.lower()] = tag.get("content", "")
        return og

    def extract_links(self, base_url: str = "") -> list[dict[str, str]]:
        links = []
        for a in self._soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/") and base_url:
                href = base_url.rstrip("/") + href
            links.append({"text": a.get_text(strip=True), "href": href})
        return links

    def extract_json_ld(self) -> list[dict[str, Any]]:
        import json
        results = []
        for script in self._soup.find_all("script", type="application/ld+json"):
            try:
                results.append(json.loads(script.string or ""))
            except Exception:
                pass
        return results
