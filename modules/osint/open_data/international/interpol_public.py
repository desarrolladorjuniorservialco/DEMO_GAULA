from __future__ import annotations

from modules.osint.open_data.base import BaseOpenDataSource
from modules.osint.open_data.models import OpenDataResult


class InterpolPublicSource(BaseOpenDataSource):
    name = "interpol_public"
    supported_target_types = frozenset({"full_name", "alias", "organization", "username"})

    def fetch(self, target: str, **kwargs) -> OpenDataResult:
        return OpenDataResult(source=self.name, ok=False, errors=["interpol_public integration pending"], metadata={"target": target})
