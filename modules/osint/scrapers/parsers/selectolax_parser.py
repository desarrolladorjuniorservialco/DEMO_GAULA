"""scrapers/parsers/selectolax_parser.py — Selectolax HTML parser wrapper (alta velocidad)."""
from __future__ import annotations

try:
    from selectolax.parser import HTMLParser as _HTMLParser
    _SELECTOLAX_AVAILABLE = True
except ImportError:
    _SELECTOLAX_AVAILABLE = False


class SelectolaxParser:
    """Wrapper sobre selectolax — el parser más rápido para HTML plano."""

    def __init__(self, html_str: str) -> None:
        if not _SELECTOLAX_AVAILABLE:
            raise ImportError("selectolax no instalado — pip install selectolax")
        self._tree = _HTMLParser(html_str)

    def text(self, selector: str) -> list[str]:
        return [node.text(strip=True) for node in self._tree.css(selector)]

    def attr(self, selector: str, attr_name: str) -> list[str]:
        return [
            node.attrs.get(attr_name, "")
            for node in self._tree.css(selector)
            if node.attrs.get(attr_name)
        ]

    def first_text(self, selector: str) -> str | None:
        node = self._tree.css_first(selector)
        return node.text(strip=True) if node else None

    def first_attr(self, selector: str, attr_name: str) -> str | None:
        node = self._tree.css_first(selector)
        if node:
            return node.attrs.get(attr_name)
        return None

    def extract_og(self) -> dict[str, str]:
        og: dict[str, str] = {}
        for node in self._tree.css("meta"):
            prop = node.attrs.get("property") or node.attrs.get("name") or ""
            if prop.lower().startswith("og:"):
                og[prop.lower()] = node.attrs.get("content", "")
        return og

    def body_text(self) -> str:
        body = self._tree.css_first("body")
        return body.text(separator=" ", strip=True) if body else ""
