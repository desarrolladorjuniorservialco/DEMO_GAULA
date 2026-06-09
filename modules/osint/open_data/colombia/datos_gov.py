from __future__ import annotations

from typing import Any

import requests

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataRecord, OpenDataResult


CATALOG_URL = "https://www.datos.gov.co/api/search/views.json"


class DatosGovSource(BaseOpenDataSource):
    name = "datos_gov"
    category = "catalog"
    mode = "api"
    country = "CO"
    description = "Busqueda en el catalogo oficial de datos abiertos de Colombia."
    official_url = "https://www.datos.gov.co/"
    api_url = CATALOG_URL

    def fetch(self, target: str, **kwargs: Any) -> OpenDataResult:
        query = (target or "").strip()
        if not query:
            return OpenDataResult(
                source=self.name,
                ok=False,
                errors=["No se proporciono un termino de busqueda."],
                metadata={"official_url": self.official_url, "api_url": self.api_url},
            )

        limit = int(kwargs.get("limit", 8) or 8)
        try:
            response = requests.get(
                self.api_url,
                params={"q": query, "limit": limit},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", []) if isinstance(payload, dict) else []
            records: list[OpenDataRecord] = []

            for item in results:
                view = (item or {}).get("view", {})
                dataset_id = view.get("id", "")
                title = view.get("name") or dataset_id or query
                description = view.get("description", "") or ""
                catalog_url = f"https://www.datos.gov.co/d/{dataset_id}" if dataset_id else self.official_url
                records.append(
                    OpenDataRecord(
                        source=self.name,
                        entity_type="dataset",
                        value=str(title),
                        confidence=0.84,
                        url=catalog_url,
                        metadata={
                            "dataset_id": dataset_id,
                            "description": description[:500],
                            "category": view.get("category", ""),
                            "asset_type": view.get("assetType", ""),
                            "attribution": view.get("attribution", ""),
                            "provenance": view.get("provenance", ""),
                            "download_count": view.get("downloadCount", 0),
                            "view_count": view.get("viewCount", 0),
                            "rows_updated_at": view.get("rowsUpdatedAt", 0),
                        },
                    )
                )

            metadata = {
                "query": query,
                "total_matches": int(payload.get("count", len(records))) if isinstance(payload, dict) else len(records),
                "official_url": self.official_url,
                "api_url": self.api_url,
            }
            return OpenDataResult(source=self.name, ok=True, records=records, metadata=metadata)
        except Exception as exc:
            return OpenDataResult(
                source=self.name,
                ok=False,
                errors=[f"datos.gov.co: {exc}"],
                metadata={"query": query, "official_url": self.official_url, "api_url": self.api_url},
            )
