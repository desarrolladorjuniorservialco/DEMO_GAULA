from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Iterable

from .schemas import NormalizedResult

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - optional dependency
    fuzz = None


class IdentityCorrelationEngine:
    def __init__(self, similarity_threshold: int = 90) -> None:
        self.similarity_threshold = similarity_threshold

    def _signature(self, item: NormalizedResult) -> tuple[str, str, str]:
        return (item.source.lower(), item.entity_type.lower(), item.value.strip().lower())

    def _same_identity(self, left: NormalizedResult, right: NormalizedResult) -> bool:
        if self._signature(left) == self._signature(right):
            return True

        if left.entity_type != right.entity_type:
            return False

        if not fuzz:
            return left.value.strip().lower() == right.value.strip().lower()

        score = fuzz.ratio(left.value.strip().lower(), right.value.strip().lower())
        return score >= self.similarity_threshold

    def correlate(self, results: Iterable[NormalizedResult]) -> list[NormalizedResult]:
        merged: list[NormalizedResult] = []
        buckets: dict[tuple[str, str], list[NormalizedResult]] = defaultdict(list)

        for item in results:
            buckets[(item.entity_type.lower(), item.value.strip().lower())].append(item)

        for bucket in buckets.values():
            if not bucket:
                continue
            base = bucket[0]
            if len(bucket) == 1:
                merged.append(base)
                continue

            sources = sorted({item.source for item in bucket})
            urls = [item.url for item in bucket if item.url]
            metadata: dict = {}
            for item in bucket:
                metadata.update(item.metadata or {})
            metadata["sources"] = sources
            metadata["merged_count"] = len(bucket)

            merged.append(
                replace(
                    base,
                    confidence=min(0.99, max(item.confidence for item in bucket)),
                    url=urls[0] if urls else base.url,
                    metadata=metadata,
                )
            )

        merged.sort(key=lambda item: (item.entity_type, item.value, item.source))
        return merged
