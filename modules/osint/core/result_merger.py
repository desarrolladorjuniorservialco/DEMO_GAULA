"""core/result_merger.py — Fusiona resultados del OsintOrchestrator con los legacy."""
from __future__ import annotations

import logging
from typing import Any

from modules.osint.connectors.base import ConnectorResult
from modules.osint.core.schemas import NormalizedResult

log = logging.getLogger(__name__)

# Confianza base por conector (hardcoded)
CONFIDENCE: dict[str, float] = {
    "github":     0.95,
    "reddit":     0.90,
    "rdap":       0.85,
    "abuseipdb":  0.90,
    "alienvault": 0.85,
    "crtsh":      0.80,
    "hibp":       0.90,
    "whois":      0.80,
    "duckduckgo": 0.55,
    "playwright": 0.70,
}

# Conectores cubiertos por _normalize_collected() en engine.py — se tratan como
# "legacy" y solo se usan como fallback si legacy no produjo datos.
_LEGACY_CONNECTORS = frozenset({"github", "reddit", "facebook", "x", "tiktok", "ip", "domain", "plugins"})


class ResultMerger:
    """Normaliza ConnectorResult del OsintOrchestrator a NormalizedResult."""

    @classmethod
    def merge(
        cls,
        legacy_collected: dict[str, dict[str, Any]],
        connector_results: dict[str, ConnectorResult],
        target_type: str,
    ) -> list[NormalizedResult]:
        """
        Produce NormalizedResult a partir de los conectores del orquestador.

        - Los conectores que ya cubre _normalize_collected() (github, reddit, etc.)
          solo se usan como fallback si legacy_collected no tiene datos válidos.
        - Los conectores con ok=False se omiten silenciosamente.
        - Los conectores desconocidos / stubs se omiten.
        """
        out: list[NormalizedResult] = []

        ok_count = sum(1 for r in connector_results.values() if r.ok)
        log.info(
            "result_merger: orquestador retornó %d conectores (%d ok)",
            len(connector_results),
            ok_count,
        )

        for name, result in connector_results.items():
            if not result.ok:
                continue

            try:
                items = cls._normalize_one(name, result, legacy_collected, target_type)
            except Exception as exc:
                log.warning("result_merger: error normalizando conector %r — %s", name, exc)
                continue

            if items:
                log.info("result_merger: %s aportó %d resultado(s)", name, len(items))
            out.extend(items)

        return out

    # ------------------------------------------------------------------
    # Normalización individual por conector
    # ------------------------------------------------------------------

    @classmethod
    def _normalize_one(
        cls,
        name: str,
        result: ConnectorResult,
        legacy_collected: dict[str, dict[str, Any]],
        target_type: str,
    ) -> list[NormalizedResult]:
        conf = CONFIDENCE.get(name, 0.50)
        data = result.data

        # --- Conectores de "nueva" cobertura (no cubiertos por legacy) ---

        if name == "abuseipdb":
            return cls._norm_abuseipdb(data, conf)

        if name == "alienvault":
            return cls._norm_alienvault(data, conf, target_type)

        if name == "hibp":
            return cls._norm_hibp(data, conf)

        if name == "whois":
            return cls._norm_whois(data, conf)

        if name == "crtsh":
            return cls._norm_crtsh(data, conf)

        if name == "duckduckgo":
            return cls._norm_duckduckgo(data, conf)

        if name == "rdap":
            return cls._norm_rdap(data, conf)

        # --- Conectores legacy con fallback ---

        if name == "github":
            # Solo usar si legacy no tiene datos
            legacy_profile = legacy_collected.get("github", {}).get("profile")
            if legacy_profile:
                return []
            return cls._norm_github_fallback(data, conf)

        if name == "reddit":
            legacy_profile = legacy_collected.get("reddit", {}).get("profile")
            if legacy_profile:
                return []
            return cls._norm_reddit_fallback(data, conf)

        # Stubs y conectores desconocidos — ignorar
        return []

    # ------------------------------------------------------------------
    # Normalizadores por conector
    # ------------------------------------------------------------------

    @staticmethod
    def _norm_abuseipdb(data: dict[str, Any], conf: float) -> list[NormalizedResult]:
        target = data.get("ipAddress") or data.get("ip", "")
        if not target:
            return []
        metadata = {
            "is_public":             data.get("is_public"),
            "abuse_confidence_score": data.get("abuse_confidence_score"),
            "country_code":          data.get("country_code"),
            "reports":               data.get("reports"),
        }
        return [
            NormalizedResult(
                source="abuseipdb",
                entity_type="ip",
                value=str(target),
                confidence=conf,
                url=f"https://www.abuseipdb.com/check/{target}",
                metadata=metadata,
            )
        ]

    @staticmethod
    def _norm_alienvault(data: dict[str, Any], conf: float, target_type: str) -> list[NormalizedResult]:
        target = data.get("indicator") or data.get("target", "")
        if not target:
            # Intentar extraer desde pulse_info / general
            target = data.get("general", {}).get("indicator", "")
        entity = "ip" if target_type == "ip" else "domain"
        metadata = {
            "pulse_count": data.get("pulse_count") or data.get("pulse_info", {}).get("count"),
            "reputation":  data.get("reputation"),
        }
        if not target:
            return []
        return [
            NormalizedResult(
                source="alienvault",
                entity_type=entity,
                value=str(target),
                confidence=conf,
                url=f"https://otx.alienvault.com/indicator/{entity}/{target}",
                metadata=metadata,
            )
        ]

    @staticmethod
    def _norm_hibp(data: dict[str, Any], conf: float) -> list[NormalizedResult]:
        breaches = data.get("breaches")
        if not isinstance(breaches, list) or not breaches:
            return []
        out = []
        for breach in breaches:
            name = breach.get("Name", "desconocido") if isinstance(breach, dict) else str(breach)
            out.append(
                NormalizedResult(
                    source="hibp",
                    entity_type="breach",
                    value=name,
                    confidence=conf,
                    url=f"https://haveibeenpwned.com/PwnedWebsites#{name}",
                    metadata=breach if isinstance(breach, dict) else {"name": name},
                )
            )
        return out

    @staticmethod
    def _norm_whois(data: dict[str, Any], conf: float) -> list[NormalizedResult]:
        out = []
        email = data.get("registrant_email") or data.get("emails")
        if email:
            # Puede ser lista o string
            emails = [email] if isinstance(email, str) else list(email)
            for e in emails:
                out.append(
                    NormalizedResult(
                        source="whois",
                        entity_type="email",
                        value=str(e).lower().strip(),
                        confidence=conf,
                        metadata={"origin": "whois_registrant"},
                    )
                )
        registrar = data.get("registrar")
        if registrar:
            out.append(
                NormalizedResult(
                    source="whois",
                    entity_type="organization",
                    value=str(registrar).strip(),
                    confidence=conf,
                    metadata={"origin": "whois_registrar"},
                )
            )
        return out

    @staticmethod
    def _norm_crtsh(data: dict[str, Any], conf: float) -> list[NormalizedResult]:
        domains = data.get("domains", [])
        if not isinstance(domains, list):
            return []
        out = []
        for domain in domains:
            if not domain:
                continue
            out.append(
                NormalizedResult(
                    source="crtsh",
                    entity_type="domain",
                    value=str(domain).strip(),
                    confidence=conf,
                    url=f"https://crt.sh/?q={domain}",
                )
            )
        return out

    @staticmethod
    def _norm_duckduckgo(data: dict[str, Any], conf: float) -> list[NormalizedResult]:
        results = data.get("results", [])
        if not isinstance(results, list):
            return []
        out = []
        for item in results:
            if not isinstance(item, dict):
                continue
            url = item.get("url", "")
            out.append(
                NormalizedResult(
                    source="duckduckgo",
                    entity_type="url",
                    value=str(url),
                    confidence=conf,
                    url=str(url),
                    metadata=item,
                )
            )
        return out

    @staticmethod
    def _norm_rdap(data: dict[str, Any], conf: float) -> list[NormalizedResult]:
        out = []
        ldh_name = data.get("ldhName")
        if ldh_name:
            out.append(
                NormalizedResult(
                    source="rdap",
                    entity_type="domain",
                    value=str(ldh_name).lower(),
                    confidence=conf,
                    url=f"https://rdap.org/domain/{ldh_name}",
                )
            )
        for entity in data.get("entities", []):
            if not isinstance(entity, dict):
                continue
            roles = entity.get("roles", [])
            if "registrant" in roles:
                vcard = entity.get("vcardArray", [])
                org_name = ""
                if isinstance(vcard, list) and len(vcard) > 1:
                    for field_entry in vcard[1]:
                        if isinstance(field_entry, list) and len(field_entry) >= 4 and field_entry[0] == "fn":
                            org_name = str(field_entry[3])
                            break
                if org_name:
                    out.append(
                        NormalizedResult(
                            source="rdap",
                            entity_type="organization",
                            value=org_name,
                            confidence=conf,
                            metadata={"role": "registrant"},
                        )
                    )
        return out

    @staticmethod
    def _norm_github_fallback(data: dict[str, Any], conf: float) -> list[NormalizedResult]:
        profile = data.get("profile", {})
        if not profile:
            return []
        out = [
            NormalizedResult(
                source="github",
                entity_type="social_profile",
                value=str(profile.get("html_url") or f"https://github.com/{profile.get('login','')}"),
                confidence=conf,
                url=str(profile.get("html_url") or ""),
                metadata={
                    "username": profile.get("login", ""),
                    "name":     profile.get("name", ""),
                    "bio":      profile.get("bio", ""),
                    "location": profile.get("location", ""),
                },
            )
        ]
        if profile.get("email"):
            out.append(
                NormalizedResult(
                    source="github",
                    entity_type="email",
                    value=str(profile["email"]).lower(),
                    confidence=conf,
                    url=str(profile.get("html_url") or ""),
                )
            )
        return out

    @staticmethod
    def _norm_reddit_fallback(data: dict[str, Any], conf: float) -> list[NormalizedResult]:
        profile = data.get("profile", {})
        if not profile:
            return []
        name = profile.get("name", "")
        return [
            NormalizedResult(
                source="reddit",
                entity_type="social_profile",
                value=f"https://reddit.com/u/{name}",
                confidence=conf,
                url=f"https://reddit.com/u/{name}",
                metadata={"name": name, "karma": profile.get("total_karma", 0)},
            )
        ]
