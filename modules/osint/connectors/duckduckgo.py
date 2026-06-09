"""connectors/duckduckgo.py — DuckDuckGo instant-answer / search connector."""
from __future__ import annotations

import time
from typing import Any

from modules.osint.connectors.base import BaseConnector, ConnectorResult

try:
    from duckduckgo_search import DDGS
    _DDG_AVAILABLE = True
except ImportError:
    _DDG_AVAILABLE = False


class DuckDuckGoConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "duckduckgo"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"username", "alias", "full_name", "email", "domain", "ip", "phone"})

    @property
    def timeout_seconds(self) -> float:
        return 15.0

    def fetch(self, target: str, max_results: int = 10, **kwargs: Any) -> ConnectorResult:
        errors: list[str] = []
        t0 = time.monotonic()

        if not _DDG_AVAILABLE:
            return ConnectorResult(
                connector=self.name,
                ok=False,
                data={},
                errors=["duckduckgo_search no instalado — pip install duckduckgo-search"],
                metadata={"latency_ms": 0},
            )

        results: list[dict] = []
        try:
            with DDGS() as ddgs:
                hits = ddgs.text(target, max_results=max_results)
                results = [
                    {"title": h.get("title"), "url": h.get("href"), "snippet": h.get("body")}
                    for h in (hits or [])
                ]
        except Exception as exc:
            errors.append(f"duckduckgo: error — {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=bool(results),
            data={"results": results},
            errors=errors,
            metadata={
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "results_count": len(results),
                "library_available": _DDG_AVAILABLE,
            },
        )
