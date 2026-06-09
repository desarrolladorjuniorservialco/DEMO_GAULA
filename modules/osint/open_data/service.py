from __future__ import annotations

import ipaddress
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

from .base import BaseOpenDataSource
from .models import OpenDataRecord, OpenDataResult
from .registry import open_data_registry


_DOMAIN_RE = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[A-Za-z]{2,63}$")
_PLATE_RE = re.compile(r"^[A-Z]{3}\d{3}$")
_DOCUMENT_RE = re.compile(r"^\d{5,12}$")


class OpenDataEngine:
    def __init__(self) -> None:
        self.registry = open_data_registry

    def classify(self, target: str) -> dict[str, Any]:
        raw = (target or "").strip()
        normalized = raw.upper()
        kind = "text"
        plate_candidate = re.sub(r"[^A-Z0-9]", "", normalized)
        document_candidate = re.sub(r"\D", "", raw)

        if not raw:
            kind = "empty"
        else:
            try:
                ipaddress.ip_address(raw)
                kind = "ip"
                normalized = raw
            except ValueError:
                if raw.startswith(("http://", "https://")):
                    kind = "url"
                elif _PLATE_RE.fullmatch(plate_candidate):
                    kind = "plate"
                    normalized = plate_candidate
                elif _DOCUMENT_RE.fullmatch(document_candidate):
                    kind = "document"
                    normalized = document_candidate
                elif _DOMAIN_RE.fullmatch(raw.lower()):
                    kind = "domain"

        return {"raw": raw, "normalized": normalized, "kind": kind}

    def _source_groups(self, target_kind: str, source_hint: str) -> list[str]:
        source_hint = (source_hint or "official").strip().lower()

        if source_hint in {"all", "auto", "official", "government"}:
            if target_kind == "plate":
                return ["simit_historical", "datos_gov"]
            if target_kind in {"document", "identification"}:
                return ["rnmc_open_data", "datos_gov"]
            if target_kind in {"domain", "url"}:
                return ["datos_gov", "secop", "rama_judicial"]
            if target_kind == "ip":
                return ["datos_gov", "territorial"]
            return ["datos_gov", "secop", "rama_judicial", "procuraduria", "contraloria", "supersociedades"]

        explicit_map = {
            "simit": ["simit_historical", "datos_gov"],
            "rnmc": ["rnmc_open_data", "datos_gov"],
            "datos_gov": ["datos_gov"],
            "secop": ["secop", "datos_gov"],
            "rama_judicial": ["rama_judicial", "datos_gov"],
            "procuraduria": ["procuraduria", "datos_gov"],
            "contraloria": ["contraloria", "datos_gov"],
            "supersociedades": ["supersociedades", "datos_gov"],
            "territorial": ["territorial", "datos_gov"],
            "boletines": ["boletines", "datos_gov"],
        }
        if source_hint in explicit_map:
            return explicit_map[source_hint]
        if source_hint in {source.name for source in self.registry.all()}:
            return [source_hint]
        return ["datos_gov"]

    def catalog(self, target_kind: str, source_hint: str) -> list[dict[str, Any]]:
        selected = set(self._source_groups(target_kind, source_hint))
        catalog = []
        for source in self.registry.all():
            if source.country != "CO" and source_hint in {"all", "auto", "official", "government"}:
                continue
            if source.name not in selected and source_hint not in {"all", "auto", "official", "government"}:
                continue
            item = source.describe()
            item["selected"] = source.name in selected
            item["available"] = source.supports(target_kind) or target_kind in {"text", "empty"}
            catalog.append(item)
        catalog.sort(key=lambda item: (not item["selected"], item["label"]))
        return catalog

    def _build_network_records(self, target: str, target_kind: str) -> tuple[list[OpenDataRecord], dict[str, Any]]:
        records: list[OpenDataRecord] = []
        details: dict[str, Any] = {"ip_data": None, "rdap_data": None, "crt_data": []}

        if target_kind == "ip":
            try:
                response = requests.get(
                    f"http://ip-api.com/json/{target}",
                    params={
                        "fields": "status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
                    },
                    timeout=15,
                )
                if response.ok:
                    data = response.json()
                    if data.get("status") == "success":
                        details["ip_data"] = data
                        records.append(
                            OpenDataRecord(
                                source="ip_api",
                                entity_type="ip",
                                value=str(data.get("query") or target),
                                confidence=0.86,
                                url="http://ip-api.com/",
                                metadata=data,
                            )
                        )
                    else:
                        details.setdefault("errors", []).append(f"ip-api: {data.get('message', 'consulta fallida')}")
                else:
                    details.setdefault("errors", []).append(f"ip-api: respuesta HTTP {response.status_code}")
            except Exception as exc:
                details.setdefault("errors", []).append(f"ip-api: {exc}")

        if target_kind in {"domain", "url"}:
            host = target
            if target.startswith(("http://", "https://")):
                from urllib.parse import urlparse

                host = urlparse(target).netloc or target
            if host.startswith("www."):
                host = host[4:]
            try:
                rdap_response = requests.get(
                    f"https://rdap.org/domain/{host}",
                    headers={"User-Agent": "NEXO-147 OpenData/1.0"},
                    timeout=15,
                )
                if rdap_response.ok:
                    details["rdap_data"] = rdap_response.json()
                    records.append(
                        OpenDataRecord(
                            source="rdap",
                            entity_type="domain",
                            value=host.lower(),
                            confidence=0.84,
                            url=f"https://rdap.org/domain/{host}",
                            metadata=details["rdap_data"],
                        )
                    )
                else:
                    details.setdefault("errors", []).append(f"RDAP: respuesta HTTP {rdap_response.status_code}")
            except Exception as exc:
                details.setdefault("errors", []).append(f"RDAP: {exc}")

            try:
                crt_response = requests.get(
                    "https://crt.sh/",
                    params={"q": host, "output": "json"},
                    headers={"User-Agent": "NEXO-147 OpenData/1.0"},
                    timeout=15,
                )
                if crt_response.ok:
                    raw = crt_response.json()
                    certs: list[dict[str, Any]] = []
                    seen = set()
                    for entry in raw[:50] if isinstance(raw, list) else []:
                        name = entry.get("name_value", "")
                        for sub in name.split("\n"):
                            sub = sub.strip()
                            if not sub or sub in seen:
                                continue
                            seen.add(sub)
                            certs.append(
                                {
                                    "name": sub,
                                    "issuer": entry.get("issuer_name", ""),
                                    "not_before": entry.get("not_before", ""),
                                    "not_after": entry.get("not_after", ""),
                                }
                            )
                    details["crt_data"] = certs
                    for cert in certs:
                        records.append(
                            OpenDataRecord(
                                source="crtsh",
                                entity_type="certificate",
                                value=cert["name"],
                                confidence=0.78,
                                url=f"https://crt.sh/?q={host}",
                                metadata=cert,
                            )
                        )
                else:
                    details.setdefault("errors", []).append(f"crt.sh: respuesta HTTP {crt_response.status_code}")
            except Exception as exc:
                details.setdefault("errors", []).append(f"crt.sh: {exc}")

        return records, details

    def search(self, target: str, source_hint: str = "official") -> dict[str, Any]:
        classification = self.classify(target)
        target_kind = classification["kind"]
        selected_sources = self._source_groups(target_kind, source_hint)
        source_objects = [source for source in self.registry.all() if source.name in selected_sources]
        source_results: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        errors: list[str] = []

        workers = max(1, min(6, len(source_objects) or 1))

        def run_source(source: BaseOpenDataSource) -> tuple[str, OpenDataResult]:
            return source.name, source.fetch(classification["normalized"], target_kind=target_kind, source_hint=source_hint)

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="open-data") as executor:
            futures = {executor.submit(run_source, source): source for source in source_objects}
            for future in as_completed(futures):
                source = futures[future]
                try:
                    source_name, result = future.result()
                except Exception as exc:
                    source_name = source.name
                    result = OpenDataResult(
                        source=source.name,
                        ok=False,
                        errors=[str(exc)],
                        metadata={"official_url": source.official_url, "api_url": source.api_url},
                    )
                source_results.append(result.as_dict())
                records.extend(record.as_dict() for record in result.records)
                errors.extend(result.errors)

        source_results.sort(key=lambda item: item.get("source", ""))

        network_records, network_details = self._build_network_records(classification["normalized"], target_kind)
        records.extend(record.as_dict() for record in network_records)
        errors.extend(network_details.get("errors", []))

        summary = {
            "sources_count": len(source_results),
            "records_count": len(records),
            "errors_count": len(errors),
            "network_records_count": len(network_records),
        }

        guidance: list[str] = []
        if target_kind == "plate":
            guidance.append("SIMIT historico solo valida coincidencias historicas; confirma vigencia en el portal oficial.")
        if target_kind in {"document", "identification"}:
            guidance.append("RNMC abierto puede devolver registros correlacionados; si no hay coincidencia, valida manualmente en el portal oficial.")
        if target_kind in {"domain", "url"}:
            guidance.append("Para dominios, RDAP y certificados CT ayudan a ubicar trazas tecnicas publicas.")

        return {
            "query": classification["raw"],
            "query_normalized": classification["normalized"],
            "target_type": target_kind,
            "source_hint": source_hint,
            "source_label": source_hint.replace("_", " ").title(),
            "source_catalog": self.catalog(target_kind, source_hint),
            "source_results": source_results,
            "results": records,
            "errors": errors,
            "network": network_details,
            "ip_data": network_details.get("ip_data"),
            "rdap_data": network_details.get("rdap_data"),
            "crt_data": network_details.get("crt_data", []),
            "summary": summary,
            "guidance": guidance,
        }
