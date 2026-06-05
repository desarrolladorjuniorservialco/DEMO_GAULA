"""connectors/github.py — GitHub public API (sin autenticacion)."""
from __future__ import annotations

import time
from typing import Any

import requests

from modules.osint.connectors.base import BaseConnector, ConnectorResult

_HEADERS = {
    "User-Agent": "NEXO-147-OSINT/1.0",
    "Accept": "application/vnd.github+json",
}
_BASE = "https://api.github.com"


class GitHubConnector(BaseConnector):

    @property
    def name(self) -> str:
        return "github"

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset({"username", "alias", "full_name", "email"})

    @property
    def rate_limit_per_minute(self) -> int:
        return 1

    @property
    def timeout_seconds(self) -> float:
        return 10.0

    def fetch(self, target: str, max_repos: int = 10, **kwargs: Any) -> ConnectorResult:
        errors: list[str] = []
        t0 = time.monotonic()
        profile: dict[str, Any] | None = None
        repos: list[dict] = []

        try:
            resp = requests.get(
                f"{_BASE}/users/{target}", headers=_HEADERS, timeout=self.timeout_seconds
            )
            if resp.status_code == 404:
                errors.append(f"github: usuario '{target}' no encontrado.")
            elif resp.status_code == 403:
                errors.append("github: rate limit alcanzado (403).")
            else:
                resp.raise_for_status()
                profile = resp.json()
        except requests.RequestException as exc:
            errors.append(f"github: error de red — {exc}")

        if profile:
            try:
                r2 = requests.get(
                    f"{_BASE}/users/{target}/repos",
                    headers=_HEADERS,
                    params={"per_page": max_repos, "sort": "updated"},
                    timeout=self.timeout_seconds,
                )
                r2.raise_for_status()
                repos = r2.json() or []
            except requests.RequestException as exc:
                errors.append(f"github: repos — {exc}")

        return ConnectorResult(
            connector=self.name,
            ok=profile is not None,
            data={"profile": profile, "repos": repos},
            errors=errors,
            metadata={
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "repos_count": len(repos),
            },
        )
