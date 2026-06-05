"""cache/redis_cache.py — L2 Redis cache (condicional).

Si redis no está instalado o no hay servidor disponible, todas las
operaciones son no-ops silenciosos.
"""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger(__name__)

try:
    import redis as _redis_lib
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False
    _redis_lib = None  # type: ignore[assignment]


class RedisCache:
    """L2 cache con Redis. Degrada a no-op si Redis no está disponible.

    Args:
        url:         URL de conexión. Ej: 'redis://localhost:6379/0'.
        default_ttl: TTL en segundos.
    """

    def __init__(self, url: str = "redis://localhost:6379/0", default_ttl: int = 3600) -> None:
        self._default_ttl = default_ttl
        self._client: Any = None
        if _REDIS_AVAILABLE:
            try:
                self._client = _redis_lib.from_url(url, decode_responses=True, socket_connect_timeout=2)
                self._client.ping()
            except Exception as exc:
                log.debug("RedisCache: no disponible (%s) — modo no-op.", exc)
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def get(self, key: str) -> Any | None:
        if not self._client:
            return None
        try:
            raw = self._client.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if not self._client:
            return
        try:
            self._client.setex(key, ttl or self._default_ttl, json.dumps(value, default=str))
        except Exception:
            pass

    def delete(self, key: str) -> None:
        if not self._client:
            return
        try:
            self._client.delete(key)
        except Exception:
            pass

    def clear_prefix(self, prefix: str) -> int:
        if not self._client:
            return 0
        try:
            keys = self._client.keys(f"{prefix}*")
            return int(self._client.delete(*keys)) if keys else 0
        except Exception:
            return 0
