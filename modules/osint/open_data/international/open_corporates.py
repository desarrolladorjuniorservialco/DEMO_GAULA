from __future__ import annotations

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataResult


class OpenCorporatesSource(BaseOpenDataSource):
    name = "open_corporates"
    supported_target_types = frozenset({"organization", "domain", "email", "full_name"})

    def fetch(self, target: str, **kwargs) -> OpenDataResult:
        return OpenDataResult(source=self.name, ok=False, errors=["open_corporates integration pending"], metadata={"target": target})
