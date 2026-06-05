"""cache/memory.py — L1 in-memory cache con TTL."""
from __future__ import annotations

import threading
import time
from typing import Any

try:
    from cachetools import TTLCache
    _CACHETOOLS = True
except ImportError:
    _CACHETOOLS = False


class MemoryCache:
    """L1 cache en memoria con TTL por clave.

    Args:
        maxsize:     Máximo de entradas (solo con cachetools).
        default_ttl: Tiempo de vida en segundos.
    """

    def __init__(self, maxsize: int = 512, default_ttl: float = 3600.0) -> None:
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        if _CACHETOOLS:
            self._cache: Any = TTLCache(maxsize=maxsize, ttl=default_ttl)
        else:
            self._cache: dict = {}  # key -> (value, expire_at)

    def get(self, key: str) -> Any | None:
        with self._lock:
            if _CACHETOOLS:
                return self._cache.get(key)
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, expire_at = entry
            if time.monotonic() > expire_at:
                del self._cache[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            if _CACHETOOLS:
                self._cache[key] = value
            else:
                self._cache[key] = (value, time.monotonic() + effective_ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __len__(self) -> int:
        with self._lock:
            if _CACHETOOLS:
                return len(self._cache)
            now = time.monotonic()
            return sum(1 for _, (_, exp) in self._cache.items() if exp > now)
