from __future__ import annotations

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataResult


class TerritorialSource(BaseOpenDataSource):
    name = "territorial"
    category = "territorial"
    mode = "catalog"
    country = "CO"
    description = "Catastros, registros y portales territoriales abiertos."
    official_url = "https://www.datos.gov.co/"

    def fetch(self, target: str, **kwargs) -> OpenDataResult:
        return OpenDataResult(
            source=self.name,
            ok=True,
            records=[],
            metadata={
                "target": target,
                "official_url": self.official_url,
                "mode": "manual",
                "nota": "Fuente reservada para catalogos territoriales y datos abiertos municipales.",
            },
        )
