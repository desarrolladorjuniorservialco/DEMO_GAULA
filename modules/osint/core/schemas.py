from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TargetDetection:
    value: str
    target_type: str
    normalized: str
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NormalizedResult:
    source: str
    entity_type: str
    value: str
    confidence: float
    url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "entity_type": self.entity_type,
            "value": self.value,
            "confidence": round(float(self.confidence), 2),
            "url": self.url,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class SearchOutcome:
    source: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    results: list[NormalizedResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "ok": self.ok,
            "data": self.data,
            "results": [item.as_dict() for item in self.results],
            "errors": self.errors,
        }
