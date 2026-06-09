from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class OpenDataRecord:
    source: str
    entity_type: str
    value: str
    confidence: float = 0.5
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
class OpenDataQuery:
    target: str
    target_type: str
    source_hint: str = "government"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OpenDataResult:
    source: str
    ok: bool
    records: list[OpenDataRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "ok": self.ok,
            "records": [record.as_dict() for record in self.records],
            "errors": self.errors,
            "metadata": self.metadata,
        }
