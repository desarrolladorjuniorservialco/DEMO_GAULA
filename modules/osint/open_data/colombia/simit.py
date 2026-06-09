from __future__ import annotations

from typing import Any
import re

import requests

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataRecord, OpenDataResult


SIMIT_DATASET_ID = "72nf-y4v3"
SIMIT_API_URL = f"https://www.datos.gov.co/resource/{SIMIT_DATASET_ID}.json"
SIMIT_PORTAL_URL = "https://fcm.org.co/simit/#/home-public"
SIMIT_DATASET_URL = f"https://www.datos.gov.co/d/{SIMIT_DATASET_ID}"


class SimitHistoricalSource(BaseOpenDataSource):
    name = "simit_historical"
    category = "vehicular"
    mode = "dataset"
    country = "CO"
    description = "Historial publico de multas SIMIT publicado en datos.gov.co."
    official_url = SIMIT_PORTAL_URL
    api_url = SIMIT_API_URL
    supported_target_types = frozenset({"plate", "organization", "full_name", "document"})

    def _normalize_plate(self, target: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", (target or "").upper())

    def fetch(self, target: str, **kwargs: Any) -> OpenDataResult:
        plate = self._normalize_plate(target)
        if not plate:
            return OpenDataResult(
                source=self.name,
                ok=False,
                errors=["No se ingreso una placa."],
                metadata={"official_url": self.official_url, "api_url": self.api_url},
            )

        try:
            response = requests.get(
                self.api_url,
                params={"$limit": int(kwargs.get("limit", 10) or 10), "placa": plate},
                timeout=15,
            )
            response.raise_for_status()
            rows = response.json()
            records: list[OpenDataRecord] = []

            if isinstance(rows, list):
                for row in rows:
                    records.append(
                        OpenDataRecord(
                            source=self.name,
                            entity_type="vehicle_fine",
                            value=f"{row.get('placa', plate)} · {row.get('fecha_multa', 'sin fecha')}",
                            confidence=0.95,
                            url=SIMIT_DATASET_URL,
                            metadata={
                                "placa": row.get("placa", plate),
                                "vigencia": row.get("vigencia", ""),
                                "fecha_multa": row.get("fecha_multa", ""),
                                "valor_multa": row.get("valor_multa", ""),
                                "departamento": row.get("departamento", ""),
                                "ciudad": row.get("ciudad", ""),
                                "pagado_si_no": row.get("pagado_si_no", ""),
                            },
                        )
                    )

            metadata = {
                "placa": plate,
                "total_coincidencias": len(records),
                "official_url": self.official_url,
                "dataset_url": SIMIT_DATASET_URL,
                "api_url": self.api_url,
                "nota": "Fuente historica publica; validar vigencia en el portal oficial SIMIT.",
            }
            return OpenDataResult(source=self.name, ok=True, records=records, metadata=metadata)
        except Exception as exc:
            return OpenDataResult(
                source=self.name,
                ok=False,
                errors=[f"SIMIT historico: {exc}"],
                metadata={
                    "placa": plate,
                    "official_url": self.official_url,
                    "dataset_url": SIMIT_DATASET_URL,
                    "api_url": self.api_url,
                },
            )
