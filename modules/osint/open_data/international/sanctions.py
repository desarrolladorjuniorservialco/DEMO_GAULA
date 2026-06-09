from __future__ import annotations

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataResult


class SanctionsSource(BaseOpenDataSource):
    name = "sanctions"
    supported_target_types = frozenset({"full_name", "organization", "alias", "email"})

    def fetch(self, target: str, **kwargs) -> OpenDataResult:
        return OpenDataResult(source=self.name, ok=False, errors=["sanctions integration pending"], metadata={"target": target})
