from __future__ import annotations

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataResult


class SecopSource(BaseOpenDataSource):
    name = "secop"
    category = "procurement"
    mode = "portal"
    country = "CO"
    description = "Portal SECOP y trazas publicas de contratacion estatal."
    official_url = "https://www.colombiacompra.gov.co/secop"

    def fetch(self, target: str, **kwargs) -> OpenDataResult:
        return OpenDataResult(
            source=self.name,
            ok=True,
            records=[],
            metadata={
                "target": target,
                "official_url": self.official_url,
                "mode": "manual",
                "nota": "Consulta manual o integra el API oficial de contratacion si esta disponible para tu convenio.",
            },
        )
