from __future__ import annotations

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataResult


class RamaJudicialSource(BaseOpenDataSource):
    name = "rama_judicial"
    category = "justice"
    mode = "portal"
    country = "CO"
    description = "Portal oficial de la Rama Judicial para consultas y trazas publicas."
    official_url = "https://www.ramajudicial.gov.co/"

    def fetch(self, target: str, **kwargs) -> OpenDataResult:
        return OpenDataResult(
            source=self.name,
            ok=True,
            records=[],
            metadata={
                "target": target,
                "official_url": self.official_url,
                "mode": "manual",
                "nota": "Consulta manual en el portal oficial; no se ejecuto scraping ni evasion de controles.",
            },
        )
