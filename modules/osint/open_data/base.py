from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import OpenDataResult


class BaseOpenDataSource(ABC):
    """Common contract for public-data sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()

    @property
    def description(self) -> str:
        return ""

    @property
    def category(self) -> str:
        return "general"

    @property
    def mode(self) -> str:
        return "manual"

    @property
    def official_url(self) -> str:
        return ""

    @property
    def api_url(self) -> str:
        return ""

    @property
    def supported_target_types(self) -> frozenset[str]:
        return frozenset(
            {
                "username",
                "alias",
                "full_name",
                "email",
                "domain",
                "ip",
                "phone",
                "organization",
                "plate",
                "identification",
                "document",
            }
        )

    @property
    def country(self) -> str | None:
        return None

    def supports(self, target_type: str) -> bool:
        return target_type in self.supported_target_types

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "mode": self.mode,
            "country": self.country,
            "official_url": self.official_url,
            "api_url": self.api_url,
            "supported_target_types": sorted(self.supported_target_types),
        }

    @abstractmethod
    def fetch(self, target: str, **kwargs: Any) -> OpenDataResult:
        ...
