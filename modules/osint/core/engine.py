from __future__ import annotations

import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any

from flask import session

from models import db
from models.nexo147 import Usuario
from models.osint import CacheConsulta, ConsultaOsint, FuenteOsint, ResultadoOsint
from models.osint_graph import create_edge, get_or_create_node

from modules.osint.analytics.graph_builder import build_graph
from modules.osint.core.correlation import IdentityCorrelationEngine
from modules.osint.core.findings import FindingEngine
from modules.osint.core.result_merger import ResultMerger
from modules.osint.core.schemas import NormalizedResult, SearchOutcome
from modules.osint.core.target_detection import TargetDetection, detect_target_type
from modules.osint.engines.orchestration import OsintOrchestrator
from modules.osint.plugins.registry import get_plugins
from modules.osint.services.search_engine import ejecutar_dork_universal

log = logging.getLogger(__name__)


class UniversalOsintEngine:
    def __init__(self) -> None:
        self.correlation_engine = IdentityCorrelationEngine()
        self.finding_engine = FindingEngine()

    def detect_target_type(self, target: str) -> TargetDetection:
        return detect_target_type(target)

    def discover_sources(self, target_type: str, source_hint: str = "all") -> list[str]:
        catalog = {
            "username": ["github", "reddit", "facebook", "x", "tiktok", "plugins"],
            "alias": ["github", "reddit", "facebook", "x", "tiktok", "plugins"],
            "full_name": ["github", "reddit", "facebook", "x", "tiktok", "plugins"],
            "email": ["github", "reddit", "facebook", "x", "tiktok", "plugins"],
            "phone": ["facebook", "plugins"],
            "domain": ["domain", "plugins"],
            "url": ["domain", "plugins"],
            "ip": ["ip", "plugins"],
            "hash": ["plugins"],
            "unknown": ["github", "reddit", "duckduckgo", "plugins"],
        }
        hint_map = {
            "both": ["github", "reddit"],
            "social": ["github", "reddit", "facebook", "x", "tiktok", "plugins"],
            "deep_all": ["github", "reddit", "facebook", "x", "tiktok", "plugins"],
            "network": ["ip", "domain", "plugins"],
            "osint_all": ["github", "reddit", "duckduckgo", "domain", "ip", "plugins"],
        }
        if source_hint in hint_map:
            return hint_map[source_hint]
        if source_hint and source_hint not in {"all", "auto"}:
            return [source_hint]
        return catalog.get(target_type, ["github", "reddit", "facebook", "x", "tiktok", "plugins"])

    def _collect_github(self, target: str) -> tuple[dict[str, Any] | None, list[dict], list[str]]:
        from modules.osint.social.routes import _fetch_github

        profile, repos, errors = _fetch_github(target)
        return profile, repos or [], errors or []

    def _collect_reddit(self, target: str) -> tuple[dict[str, Any] | None, list[dict], list[str]]:
        from modules.osint.social.routes import _fetch_reddit

        profile, posts, errors = _fetch_reddit(target)
        return profile, posts or [], errors or []

    def _collect_facebook(self, target: str) -> tuple[dict[str, Any] | None, list[str]]:
        from modules.osint.social.scrapers.facebook_playwright import scrape_facebook_profile

        data, errors = scrape_facebook_profile(target)
        return data, errors or []

    def _collect_x(self, target: str) -> tuple[dict[str, Any] | None, list[str]]:
        raw = ejecutar_dork_universal(target, ["x"], max_results=30)
        res = raw.get("x", {})
        data = extract_x_profiles(res.get("results", []), target) if extract_x_profiles else None
        return data, res.get("errors", [])

    def _collect_tiktok(self, target: str) -> tuple[dict[str, Any] | None, list[str]]:
        raw = ejecutar_dork_universal(target, ["tiktok"], max_results=30)
        res = raw.get("tiktok", {})
        data = extract_tiktok_profiles(res.get("results", []), target) if extract_tiktok_profiles else None
        return data, res.get("errors", [])

    def _collect_ip(self, target: str) -> tuple[dict[str, Any] | None, list[str]]:
        from modules.osint.opendata.routes import _fetch_ip_geo

        data, errors = _fetch_ip_geo(target)
        return data, errors or []

    def _collect_domain(self, target: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
        from modules.osint.opendata.routes import _fetch_crt_sh, _fetch_domain_rdap, _parse_rdap

        rdap_raw, rdap_errors = _fetch_domain_rdap(target)
        rdap_data = _parse_rdap(rdap_raw) if rdap_raw else None
        crt_data, crt_errors = _fetch_crt_sh(target)
        return rdap_data, {"certs": crt_data}, (rdap_errors or []) + (crt_errors or [])

    def _collect_plugins(self, target: str) -> tuple[list[dict], list[str]]:
        payloads: list[dict] = []
        errors: list[str] = []
        for plugin in get_plugins():
            try:
                payloads.append(plugin.ejecutar(target))
            except Exception as exc:
                errors.append(f"Plugin {plugin.name}: {exc}")
        return payloads, errors

    def run_collectors(self, target: str, sources: list[str]) -> dict[str, dict[str, Any]]:
        collected: dict[str, dict[str, Any]] = {}
        workers = max(1, min(len(sources), 6))

        def task(source: str) -> tuple[str, dict[str, Any]]:
            if source == "github":
                profile, repos, errors = self._collect_github(target)
                return source, {"profile": profile, "repos": repos, "errors": errors}
            if source == "reddit":
                profile, posts, errors = self._collect_reddit(target)
                return source, {"profile": profile, "posts": posts, "errors": errors}
            if source == "facebook":
                data, errors = self._collect_facebook(target)
                return source, {"data": data, "errors": errors}
            if source == "x":
                data, errors = self._collect_x(target)
                return source, {"data": data, "errors": errors}
            if source == "tiktok":
                data, errors = self._collect_tiktok(target)
                return source, {"data": data, "errors": errors}
            if source == "ip":
                data, errors = self._collect_ip(target)
                return source, {"data": data, "errors": errors}
            if source == "domain":
                rdap_data, crt_data, errors = self._collect_domain(target)
                return source, {"rdap_data": rdap_data, "crt_data": crt_data, "errors": errors}
            if source == "plugins":
                payloads, errors = self._collect_plugins(target)
                return source, {"plugins": payloads, "errors": errors}
            return source, {"errors": [f"Fuente no soportada: {source}"]}

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="osint-universal") as executor:
            futures = {executor.submit(task, source): source for source in sources}
            for future in as_completed(futures):
                source = futures[future]
                try:
                    key, payload = future.result()
                    collected[key] = payload
                except Exception as exc:
                    collected[source] = {"errors": [str(exc)]}

        return collected

    def _normalize_collected(self, collected: dict[str, dict[str, Any]], target: str) -> list[NormalizedResult]:
        normalized: list[NormalizedResult] = []

        github = collected.get("github", {})
        if github.get("profile"):
            profile = github["profile"]
            normalized.append(
                NormalizedResult(
                    source="github",
                    entity_type="social_profile",
                    value=str(profile.get("html_url") or f"https://github.com/{target}"),
                    confidence=0.95,
                    url=str(profile.get("html_url") or ""),
                    metadata={
                        "username": profile.get("login", target),
                        "name": profile.get("name", ""),
                        "company": profile.get("company", ""),
                        "bio": profile.get("bio", ""),
                        "location": profile.get("location", ""),
                    },
                )
            )
            if profile.get("email"):
                normalized.append(
                    NormalizedResult(
                        source="github",
                        entity_type="email",
                        value=str(profile["email"]).lower(),
                        confidence=0.95,
                        url=str(profile.get("html_url") or ""),
                    )
                )
            if profile.get("company"):
                normalized.append(
                    NormalizedResult(
                        source="github",
                        entity_type="organization",
                        value=str(profile["company"]).strip().lstrip("@"),
                        confidence=0.8,
                        url=str(profile.get("html_url") or ""),
                    )
                )
            if profile.get("blog"):
                normalized.append(
                    NormalizedResult(
                        source="github",
                        entity_type="domain",
                        value=str(profile["blog"]).strip(),
                        confidence=0.75,
                    )
                )
            if profile.get("twitter_username"):
                normalized.append(
                    NormalizedResult(
                        source="github",
                        entity_type="social_profile",
                        value=f"@{profile['twitter_username']}",
                        confidence=0.8,
                    )
                )

        for repo in github.get("repos", []) or []:
            normalized.append(
                NormalizedResult(
                    source="github",
                    entity_type="repository",
                    value=str(repo.get("html_url") or repo.get("name") or ""),
                    confidence=0.8,
                    url=str(repo.get("html_url") or ""),
                    metadata={
                        "name": repo.get("name", ""),
                        "language": repo.get("language", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "updated_at": repo.get("updated_at", ""),
                    },
                )
            )

        reddit = collected.get("reddit", {})
        if reddit.get("profile"):
            profile = reddit["profile"]
            normalized.append(
                NormalizedResult(
                    source="reddit",
                    entity_type="social_profile",
                    value=f"https://reddit.com/u/{profile.get('name', target)}",
                    confidence=0.9,
                    url=f"https://reddit.com/u/{profile.get('name', target)}",
                    metadata={"name": profile.get("name", target), "karma": profile.get("total_karma", 0)},
                )
            )

        facebook = collected.get("facebook", {})
        if facebook.get("data"):
            data = facebook["data"]
            normalized.append(
                NormalizedResult(
                    source="facebook",
                    entity_type="social_profile",
                    value=str(data.get("profile_url") or f"https://facebook.com/{target}"),
                    confidence=0.7,
                    url=str(data.get("profile_url") or ""),
                    metadata={"is_mock": data.get("is_mock", False)},
                )
            )
            for hint in data.get("email_hints", []) or []:
                normalized.append(
                    NormalizedResult(
                        source="facebook",
                        entity_type="email",
                        value=str(hint).lower(),
                        confidence=0.55,
                        metadata={"source": "facebook_hints"},
                    )
                )

        x_data = collected.get("x", {}).get("data")
        if x_data:
            for profile in x_data.get("profiles", []) or []:
                normalized.append(
                    NormalizedResult(
                        source="x",
                        entity_type="social_profile",
                        value=str(profile.get("url") or ""),
                        confidence=0.6,
                        url=str(profile.get("url") or ""),
                        metadata=profile,
                    )
                )

        tiktok_data = collected.get("tiktok", {}).get("data")
        if tiktok_data:
            for profile in tiktok_data.get("profiles", []) or []:
                normalized.append(
                    NormalizedResult(
                        source="tiktok",
                        entity_type="social_profile",
                        value=str(profile.get("url") or ""),
                        confidence=0.6,
                        url=str(profile.get("url") or ""),
                        metadata=profile,
                    )
                )

        ip_data = collected.get("ip", {}).get("data")
        if ip_data:
            normalized.append(
                NormalizedResult(
                    source="ip-api",
                    entity_type="ip",
                    value=str(ip_data.get("query") or target),
                    confidence=0.8,
                    metadata=ip_data,
                )
            )

        rdap_data = collected.get("domain", {}).get("rdap_data")
        if rdap_data and rdap_data.get("ldhName"):
            normalized.append(
                NormalizedResult(
                    source="rdap",
                    entity_type="domain",
                    value=str(rdap_data.get("ldhName")),
                    confidence=0.85,
                    metadata=rdap_data,
                )
            )

        for plugin_result in collected.get("plugins", {}).get("plugins", []) or []:
            normalized.append(
                NormalizedResult(
                    source=str(plugin_result.get("plugin", "plugin")),
                    entity_type=str(plugin_result.get("entity_type", "plugin")),
                    value=str(plugin_result.get("value", target)),
                    confidence=float(plugin_result.get("confidence", 0.5) or 0.5),
                    url=str(plugin_result.get("url", "")),
                    metadata=plugin_result,
                )
            )

        return normalized

    def calculate_risk(self, normalized_results: list[NormalizedResult]) -> dict[str, Any]:
        findings, risk = self.finding_engine.build(normalized_results)
        return {"findings": findings, "risk": risk}

    def build_graph(self, target: str, collected: dict[str, dict[str, Any]]) -> dict[str, Any]:
        return build_graph(
            username=target,
            github_profile=collected.get("github", {}).get("profile"),
            github_repos=collected.get("github", {}).get("repos"),
            reddit_profile=collected.get("reddit", {}).get("profile"),
            facebook_data=collected.get("facebook", {}).get("data"),
            ip_data=collected.get("ip", {}).get("data"),
            rdap_data=collected.get("domain", {}).get("rdap_data"),
        )

    def _cache_key(self, target: str, source_hint: str, target_type: str) -> str:
        payload = f"{target_type}:{source_hint}:{target.strip().lower()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _resolve_user_id(self, username: str | None) -> int | None:
        if not username:
            return None
        user = db.session.query(Usuario).filter_by(username=username).first()
        return user.id if user else None

    def _load_cache(self, cache_key: str) -> dict[str, Any] | None:
        cache = (
            db.session.query(CacheConsulta)
            .filter_by(hash_clave=cache_key)
            .first()
        )
        if not cache or not cache.expira_en:
            return None
        if cache.expira_en < datetime.utcnow():
            return None
        try:
            payload = json.loads(cache.respuesta_raw or "{}")
            cache.hits = (cache.hits or 0) + 1
            db.session.commit()
            return payload
        except Exception:
            return None

    def _ensure_source(self) -> FuenteOsint:
        fuente = db.session.query(FuenteOsint).filter_by(nombre="universal_engine").first()
        if fuente:
            return fuente
        fuente = FuenteOsint(
            nombre="universal_engine",
            tipo="engine",
            url_base="",
            requiere_key=False,
            activa=True,
            rate_limit_por_min=60,
            descripcion="Motor universal OSINT",
            created_by="system",
            updated_by="system",
        )
        db.session.add(fuente)
        db.session.commit()
        return fuente

    def persist_results(
        self,
        target: str,
        detection: TargetDetection,
        source_hint: str,
        collected: dict[str, dict[str, Any]],
        normalized_results: list[NormalizedResult],
        response: dict[str, Any],
        user_id: int | None = None,
        created_by: str | None = None,
    ) -> None:
        source = self._ensure_source()
        consulta = ConsultaOsint(
            fuente_id=source.id,
            tipo_consulta="universal_search",
            valor_consultado=target,
            entity_type=detection.target_type,
            estado="completada",
            usuario_id=user_id,
            created_by=created_by or "system",
        )
        db.session.add(consulta)
        db.session.flush()

        cache = CacheConsulta(
            consulta_id=consulta.id,
            hash_clave=self._cache_key(target, source_hint, detection.target_type),
            respuesta_raw=json.dumps(response, ensure_ascii=False, default=str),
            codigo_http=200,
            expira_en=datetime.utcnow() + timedelta(hours=1),
            hits=0,
        )
        db.session.add(cache)

        for item in normalized_results:
            resultado = ResultadoOsint(
                consulta_id=consulta.id,
                tipo_hallazgo=item.entity_type,
                titulo=item.value[:200],
                descripcion=json.dumps(item.metadata, ensure_ascii=False, default=str),
                datos_json=json.dumps(item.as_dict(), ensure_ascii=False, default=str),
                relevancia=min(1.0, max(0.0, float(item.confidence))),
                verificado=False,
                created_by=created_by or "system",
            )
            db.session.add(resultado)

        graph_data = response.get("graph") or {}
        if graph_data.get("nodes") and graph_data.get("links"):
            node_objs: dict[str, Any] = {}
            for node in graph_data["nodes"]:
                obj, _ = get_or_create_node(
                    db.session,
                    type=node.get("type", "person"),
                    value=node.get("id", ""),
                    label=node.get("label", node.get("id", "")),
                    group=node.get("type", "contact"),
                    metadata_dict=node.get("metadata", {}),
                )
                node_objs[node.get("id", "")] = obj
            for edge in graph_data["links"]:
                src = node_objs.get(edge.get("source"))
                tgt = node_objs.get(edge.get("target"))
                if src and tgt:
                    create_edge(
                        db.session,
                        src,
                        tgt,
                        edge.get("relation_type", "relacion"),
                        {
                            "confidence": edge.get("confidence", 0.75),
                            "weight": edge.get("weight", 1.0),
                            "source_evidence": edge.get("source_evidence", "universal_engine"),
                        },
                    )

        db.session.commit()

    def search(
        self,
        target: str,
        source_hint: str = "all",
        persist: bool = True,
        user_name: str | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        started_at = datetime.utcnow()
        detection = self.detect_target_type(target)
        cache_key = self._cache_key(target, source_hint, detection.target_type)
        cached = self._load_cache(cache_key)
        if cached:
            cached["cached"] = True
            return cached

        sources           = self.discover_sources(detection.target_type, source_hint)
        collected         = self.run_collectors(target, sources)
        legacy_normalized = self._normalize_collected(collected, target)
        connector_results = OsintOrchestrator.default().run(target, detection.target_type)
        extra_normalized  = ResultMerger.merge(collected, connector_results, detection.target_type)
        normalized        = self.correlation_engine.correlate(legacy_normalized + extra_normalized)
        risk_bundle = self.calculate_risk(normalized)
        graph_data = self.build_graph(target, collected)

        response = {
            "target": target,
            "target_type": detection.target_type,
            "sources_used": sources,
            "results": [item.as_dict() for item in normalized],
            "findings": risk_bundle["findings"],
            "risk": risk_bundle["risk"],
            "graph": graph_data,
            "stats": {
                "duration_ms": int((datetime.utcnow() - started_at).total_seconds() * 1000),
                "results_count": len(normalized),
                "sources_count": len(sources),
            },
            "detected": {
                "value": detection.value,
                "normalized": detection.normalized,
                "confidence": detection.confidence,
                "metadata": detection.metadata,
            },
            "collectors": collected,
            "connector_results": {
                name: {"ok": r.ok, "errors": r.errors}
                for name, r in connector_results.items()
            },
        }

        if persist:
            try:
                self.persist_results(
                    target,
                    detection,
                    source_hint,
                    collected,
                    normalized,
                    response,
                    user_id=self._resolve_user_id(user_name),
                    created_by=created_by,
                )
            except Exception:
                log.exception("search: persist_results falló para target=%r", target)
                db.session.rollback()

        return response
