"""Open data layer for OSINT public-sector and institutional sources."""
from __future__ import annotations

from .base import BaseOpenDataSource
from .models import OpenDataQuery, OpenDataRecord, OpenDataResult
from .registry import OpenDataRegistry, open_data_registry
from .service import OpenDataEngine

try:
    open_data_registry.discover()
except Exception:
    pass

__all__ = [
    "BaseOpenDataSource",
    "OpenDataQuery",
    "OpenDataRecord",
    "OpenDataResult",
    "OpenDataRegistry",
    "OpenDataEngine",
    "open_data_registry",
]
