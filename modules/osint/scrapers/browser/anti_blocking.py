"""scrapers/browser/anti_blocking.py — UA rotation + backoff helpers."""
from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

_T = TypeVar("_T")

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]


class AntiBlocking:
    """Herramientas para reducir la detección de bots en scrapers."""

    @staticmethod
    def random_ua() -> str:
        return random.choice(_USER_AGENTS)

    @staticmethod
    def jitter(base_ms: int = 1000, spread_ms: int = 800) -> None:
        """Espera un tiempo aleatorio alrededor de base_ms milisegundos."""
        delay = (base_ms + random.randint(-spread_ms // 2, spread_ms // 2)) / 1000.0
        time.sleep(max(0.1, delay))

    @staticmethod
    def exponential_backoff(
        fn: Callable[[], _T],
        *,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> _T:
        """
        Reintenta fn() con backoff exponencial.
        Lanza la última excepción si se agotan los reintentos.
        """
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                return fn()
            except Exception as exc:
                last_exc = exc
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    @staticmethod
    def random_viewport() -> dict[str, int]:
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 800},
            {"width": 1536, "height": 864},
        ]
        return random.choice(viewports)
