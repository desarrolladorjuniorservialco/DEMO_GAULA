from __future__ import annotations

from typing import Any

import requests

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataRecord, OpenDataResult


RNMC_PORTAL_URL = "https://srvcnpc.policia.gov.co/PSC/frm_cnp_consulta.aspx"
RNMC_DATASET_ID = "e7nt-rbi7"
RNMC_DATASET_URL = f"https://www.datos.gov.co/d/{RNMC_DATASET_ID}"
RNMC_API_URL = f"https://www.datos.gov.co/resource/{RNMC_DATASET_ID}.json"
RNMC_CATALOG_URL = "https://www.datos.gov.co/api/search/views.json"


class RnmcOpenDataSource(BaseOpenDataSource):
    name = "rnmc_open_data"
    category = "convivencia"
    mode = "dataset"
    country = "CO"
    description = "Consulta abierta relacionada con RNMC y medidas correctivas publicada en datos.gov.co."
    official_url = RNMC_PORTAL_URL
    api_url = RNMC_API_URL
    supported_target_types = frozenset({"identification", "document", "full_name", "organization", "plate"})

    def _catalog_search(self, query: str, limit: int = 6) -> list[OpenDataRecord]:
        response = requests.get(
            RNMC_CATALOG_URL,
            params={"q": f"RNMC {query}".strip(), "limit": limit},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        records: list[OpenDataRecord] = []
        for item in payload.get("results", []) if isinstance(payload, dict) else []:
            view = (item or {}).get("view", {})
            dataset_id = view.get("id", "")
            title = view.get("name") or dataset_id or "RNMC"
            records.append(
                OpenDataRecord(
                    source=self.name,
                    entity_type="dataset",
                    value=str(title),
                    confidence=0.74,
                    url=f"https://www.datos.gov.co/d/{dataset_id}" if dataset_id else RNMC_PORTAL_URL,
                    metadata={
                        "dataset_id": dataset_id,
                        "description": (view.get("description", "") or "")[:500],
                        "category": view.get("category", ""),
                        "provenance": view.get("provenance", ""),
                    },
                )
            )
        return records

    def fetch(self, target: str, **kwargs: Any) -> OpenDataResult:
        query = (target or "").strip()
        if not query:
            return OpenDataResult(
                source=self.name,
                ok=False,
                errors=["No se ingreso un valor para consultar RNMC."],
                metadata={"official_url": self.official_url, "api_url": self.api_url},
            )

        limit = int(kwargs.get("limit", 10) or 10)
        records: list[OpenDataRecord] = []
        errors: list[str] = []

        try:
            # Primer intento: dataset abierto de medidas correctivas.
            response = requests.get(
                self.api_url,
                params={"$limit": limit, "$q": query},
                timeout=15,
            )
            response.raise_for_status()
            rows = response.json()
            if isinstance(rows, list):
                for row in rows:
                    expediente = row.get("expediente", "")
                    descripcion = row.get("comportamiento", "") or row.get("medida", "")
                    records.append(
                        OpenDataRecord(
                            source=self.name,
                            entity_type="rnmc_record",
                            value=str(expediente or query),
                            confidence=0.82,
                            url=RNMC_DATASET_URL,
                            metadata={
                                "expediente": expediente,
                                "fecha_hechos": row.get("fecha_hechos", ""),
                                "hora_hechos": row.get("hora_hechos", ""),
                                "localidad": row.get("localidad", ""),
                                "barrio_hechos": row.get("barrio_hechos", ""),
                                "articulo": row.get("articulo", ""),
                                "comportamiento": descripcion,
                                "estado_medida": row.get("estado_medida", ""),
                                "estado_comparendo": row.get("estado_comparendo", ""),
                                "nota": "Registro abierto municipal asociado al ecosistema RNMC.",
                            },
                        )
                    )
        except Exception as exc:
            errors.append(f"RNMC dataset: {exc}")

        try:
            catalog_records = self._catalog_search(query, limit=min(6, max(2, limit // 2)))
            records.extend(catalog_records)
        except Exception as exc:
            errors.append(f"RNMC catalogo: {exc}")

        metadata = {
            "query": query,
            "official_url": self.official_url,
            "portal_url": RNMC_PORTAL_URL,
            "dataset_url": RNMC_DATASET_URL,
            "api_url": self.api_url,
            "total_records": len(records),
            "note": "Si no aparece una coincidencia exacta, valida manualmente en el portal oficial RNMC.",
        }

        return OpenDataResult(
            source=self.name,
            ok=len(errors) == 0,
            records=records,
            errors=errors,
            metadata=metadata,
        )
