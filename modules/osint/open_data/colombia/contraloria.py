from __future__ import annotations

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataResult


class ContraloriaSource(BaseOpenDataSource):
    name = "contraloria"
    category = "control"
    mode = "portal"
    country = "CO"
    description = "Portal y consultas publicas de la Contraloria General."
    official_url = "https://www.contraloria.gov.co/"

    def fetch(self, target: str, **kwargs) -> OpenDataResult:
        return OpenDataResult(
            source=self.name,
            ok=True,
            records=[],
            metadata={
                "target": target,
                "official_url": self.official_url,
                "mode": "manual",
                "nota": "Consulta manual en el portal oficial de la Contraloria.",
            },
        )
