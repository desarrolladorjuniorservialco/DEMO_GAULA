from __future__ import annotations

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataResult


class SuperSociedadesSource(BaseOpenDataSource):
    name = "supersociedades"
    category = "corporate"
    mode = "portal"
    country = "CO"
    description = "Portal de la Superintendencia de Sociedades y consultas mercantiles publicas."
    official_url = "https://www.supersociedades.gov.co/"

    def fetch(self, target: str, **kwargs) -> OpenDataResult:
        return OpenDataResult(
            source=self.name,
            ok=True,
            records=[],
            metadata={
                "target": target,
                "official_url": self.official_url,
                "mode": "manual",
                "nota": "Consulta manual en el portal oficial de la SuperSociedades.",
            },
        )
