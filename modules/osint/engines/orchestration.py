"""engines/orchestration.py — Coordinador concurrente de conectores OSINT."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from modules.osint.connectors.base import BaseConnector, ConnectorResult

log = logging.getLogger(__name__)

_DEFAULT_WORKERS = 6
_DEFAULT_TIMEOUT = 30.0


class OsintOrchestrator:
    """Ejecuta múltiples conectores en paralelo y agrega sus resultados."""

    def __init__(
        self,
        connectors: list[BaseConnector],
        *,
        max_workers: int = _DEFAULT_WORKERS,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._connectors = connectors
        self._max_workers = max_workers
        self._timeout = timeout

    def applicable(self, target_type: str) -> list[BaseConnector]:
        return [c for c in self._connectors if c.supports(target_type)]

    def run(
        self,
        target: str,
        target_type: str,
        *,
        connector_names: list[str] | None = None,
        extra_kwargs: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, ConnectorResult]:
        """
        Ejecuta los conectores aplicables en paralelo.

        Args:
            target: El objetivo de la consulta (usuario, dominio, IP, etc.).
            target_type: Tipo del objetivo (username, domain, ip, email).
            connector_names: Si se indica, solo ejecuta estos conectores.
            extra_kwargs: kwargs adicionales por conector {"github": {"max_repos": 20}}.

        Returns:
            Diccionario connector_name -> ConnectorResult.
        """
        candidates = self.applicable(target_type)
        if connector_names:
            names_set = set(connector_names)
            candidates = [c for c in candidates if c.name in names_set]

        if not candidates:
            log.warning("orchestration: sin conectores para target_type=%r", target_type)
            return {}

        extra_kwargs = extra_kwargs or {}
        results: dict[str, ConnectorResult] = {}

        with ThreadPoolExecutor(max_workers=min(self._max_workers, len(candidates))) as pool:
            future_to_name = {
                pool.submit(
                    self._safe_fetch,
                    connector,
                    target,
                    **(extra_kwargs.get(connector.name, {})),
                ): connector.name
                for connector in candidates
            }
            for future in as_completed(future_to_name, timeout=self._timeout):
                name = future_to_name[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    log.error("orchestration: %s raised %s", name, exc)
                    results[name] = ConnectorResult(
                        connector=name,
                        ok=False,
                        errors=[f"{name}: error interno — {exc}"],
                    )

        return results

    @staticmethod
    def _safe_fetch(connector: BaseConnector, target: str, **kwargs: Any) -> ConnectorResult:
        try:
            return connector.fetch(target, **kwargs)
        except Exception as exc:
            log.error("connector %s fetch error: %s", connector.name, exc)
            return ConnectorResult(
                connector=connector.name,
                ok=False,
                errors=[f"{connector.name}: excepción no capturada — {exc}"],
            )

    @classmethod
    def default(cls) -> "OsintOrchestrator":
        """Devuelve un orquestador con todos los conectores disponibles."""
        from modules.osint.connectors.github import GitHubConnector
        from modules.osint.connectors.reddit import RedditConnector
        from modules.osint.connectors.duckduckgo import DuckDuckGoConnector
        from modules.osint.connectors.crtsh import CrtShConnector
        from modules.osint.connectors.rdap import RdapConnector
        from modules.osint.connectors.abuseipdb import AbuseIpDbConnector
        from modules.osint.connectors.alienvault import AlienVaultConnector
        from modules.osint.connectors.hibp import HibpConnector
        from modules.osint.connectors.whois import WhoisConnector
        from modules.osint.connectors.phone import PhoneConnector
        from modules.osint.connectors.shodan import ShodanApiConnector
        from modules.osint.connectors.virustotal import VirusTotalApiConnector
        from modules.osint.connectors.social_stubs import ALL_SOCIAL_STUBS

        working = [
            GitHubConnector(),
            RedditConnector(),
            DuckDuckGoConnector(),
            CrtShConnector(),
            RdapConnector(),
            AbuseIpDbConnector(),
            AlienVaultConnector(),
            HibpConnector(),
            WhoisConnector(),
            PhoneConnector(),
            ShodanApiConnector(),
            VirusTotalApiConnector(),
        ]
        stubs = [klass() for klass in ALL_SOCIAL_STUBS]
        return cls(working + stubs)
