from __future__ import annotations

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataResult


class PublicCompanyDataSource(BaseOpenDataSource):
    name = "public_company_data"
    supported_target_types = frozenset({"organization", "domain", "full_name"})

    def fetch(self, target: str, **kwargs) -> OpenDataResult:
        return OpenDataResult(source=self.name, ok=False, errors=["public_company_data integration pending"], metadata={"target": target})
