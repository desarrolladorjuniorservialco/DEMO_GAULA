"""scrapers/parsers/lxml_parser.py — lxml HTML parser wrapper."""
from __future__ import annotations

try:
    from lxml import etree, html as lxml_html
    _LXML_AVAILABLE = True
except ImportError:
    _LXML_AVAILABLE = False


class LxmlParser:
    """Wrapper sobre lxml para XPath y extracción rápida."""

    def __init__(self, html_str: str) -> None:
        if not _LXML_AVAILABLE:
            raise ImportError("lxml no instalado — pip install lxml")
        self._tree = lxml_html.fromstring(html_str)

    def xpath(self, expr: str) -> list[str]:
        try:
            results = self._tree.xpath(expr)
            return [r.strip() if isinstance(r, str) else str(r) for r in results]
        except Exception:
            return []

    def css(self, selector: str) -> list[str]:
        try:
            return [el.text_content().strip() for el in self._tree.cssselect(selector)]
        except Exception:
            return []

    def attr(self, selector: str, attr_name: str) -> list[str]:
        try:
            return [
                el.get(attr_name, "")
                for el in self._tree.cssselect(selector)
                if el.get(attr_name)
            ]
        except Exception:
            return []

    def text_content(self) -> str:
        try:
            return self._tree.text_content()
        except Exception:
            return ""
