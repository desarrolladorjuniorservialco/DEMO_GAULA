from __future__ import annotations

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataResult


class BoletinesSource(BaseOpenDataSource):
    name = "boletines"
    category = "boletines"
    mode = "portal"
    country = "CO"
    description = "Boletines y publicaciones oficiales de entidades publicas."
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
                "nota": "Usa el catalogo oficial de datos abiertos para encontrar boletines relacionados.",
            },
        )
