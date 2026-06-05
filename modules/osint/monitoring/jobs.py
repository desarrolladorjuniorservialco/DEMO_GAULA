"""monitoring/jobs.py — APScheduler jobs para vigilancia OSINT."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    _APScheduler_AVAILABLE = True
except ImportError:
    _APScheduler_AVAILABLE = False


def _run_watchlist_check() -> None:
    from modules.osint.monitoring.watchlists import WatchlistService
    try:
        results = WatchlistService().check_all()
        log.info("watchlist job: %d targets revisados", len(results))
    except Exception as exc:
        log.error("watchlist job error: %s", exc)


class OsintScheduler:
    """Envuelve APScheduler para los jobs periódicos del módulo OSINT."""

    def __init__(self, watchlist_interval_minutes: int = 60) -> None:
        self._interval = watchlist_interval_minutes
        self._scheduler = None

    def start(self) -> bool:
        if not _APScheduler_AVAILABLE:
            log.warning("APScheduler no instalado — jobs desactivados. pip install apscheduler")
            return False

        self._scheduler = BackgroundScheduler(timezone="UTC", daemon=True)
        self._scheduler.add_job(
            _run_watchlist_check,
            trigger="interval",
            minutes=self._interval,
            id="osint_watchlist_check",
            replace_existing=True,
            misfire_grace_time=300,
        )
        self._scheduler.start()
        log.info("OsintScheduler iniciado — watchlist cada %d min", self._interval)
        return True

    def stop(self) -> None:
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            log.info("OsintScheduler detenido.")

    @property
    def running(self) -> bool:
        return bool(self._scheduler and self._scheduler.running)
