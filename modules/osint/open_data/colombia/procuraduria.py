from __future__ import annotations

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataResult


class ProcuraduriaSource(BaseOpenDataSource):
    name = "procuraduria"
    category = "control"
    mode = "portal"
    country = "CO"
    description = "Portal de antecedentes y publicaciones de la Procuraduria."
    official_url = "https://www.procuraduria.gov.co/"

    def fetch(self, target: str, **kwargs) -> OpenDataResult:
        return OpenDataResult(
            source=self.name,
            ok=True,
            records=[],
            metadata={
                "target": target,
                "official_url": self.official_url,
                "mode": "manual",
                "nota": "Consulta manual en el portal oficial; integra acceso autorizado si existe convenio.",
            },
        )
