"""connectors/reddit.py — Reddit public API (sin autenticacion)."""
from __future__ import annotations

import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_HEADERS = {"User-Agent": "NEXO-147-OSINT/1.0"}
_BASE = "https://www.reddit.com"


class RedditConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "reddit"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"username", "alias", "full_name"})

    @property
    def timeout_seconds(self) -> float:
        return 10.0

    def fetch(self, target: str, **kwargs: Any) -> ConnectorResult:
        errors: list[str] = []
        t0 = time.monotonic()
        profile: dict[str, Any] | None = None
        posts: list[dict] = []

        try:
            resp = requests.get(
                f"{_BASE}/user/{target}/about.json",
                headers=_HEADERS,
                timeout=self.timeout_seconds,
            )
            if resp.status_code == 404:
                errors.append(f"reddit: usuario '{target}' no encontrado.")
            elif resp.status_code == 429:
                errors.append("reddit: rate limit (429).")
            else:
                resp.raise_for_status()
                profile = resp.json().get("data", {})
        except requests.RequestException as exc:
            errors.append(f"reddit: error de red — {exc}")

        if profile:
            try:
                r2 = requests.get(
                    f"{_BASE}/user/{target}/submitted.json",
                    headers=_HEADERS,
                    params={"limit": 10},
                    timeout=self.timeout_seconds,
                )
                r2.raise_for_status()
                children = r2.json().get("data", {}).get("children", [])
                posts = [c.get("data", {}) for c in children[:10]]
            except requests.RequestException as exc:
                errors.append(f"reddit: posts — {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=profile is not None,
            data={"profile": profile, "posts": posts},
            errors=errors,
            metadata={
                "latency_ms":  int((time.monotonic() - t0) * 1000),
                "posts_count": len(posts),
            },
        )
