"""monitoring/watchlists.py — Servicio de vigilancia activa de targets OSINT."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)


class WatchlistService:
    """
    Ejecuta re-consultas periódicas de targets activos en WatchlistOsint
    y registra cambios detectados.
    """

    def check_all(self) -> list[dict[str, Any]]:
        """Revisa todos los watchlists activos y retorna lista de resultados."""
        from models import db
        from models.osint import WatchlistOsint

        activos = WatchlistOsint.query.filter_by(activo=True).all()
        resultados = []
        for item in activos:
            try:
                resultado = self._check_one(item)
                resultados.append(resultado)
            except Exception as exc:
                log.error("watchlist id=%s error: %s", item.id, exc)
                resultados.append({"id": item.id, "ok": False, "error": str(exc)})
        return resultados

    def _check_one(self, item: Any) -> dict[str, Any]:
        from modules.osint.engines.orchestration import OsintOrchestrator

        orchestrator = OsintOrchestrator.default()
        results = orchestrator.run(
            target=item.target,
            target_type=getattr(item, "target_type", "username"),
        )
        ok_count = sum(1 for r in results.values() if r.ok)
        return {
            "id": item.id,
            "target": item.target,
            "ok": True,
            "connectors_ok": ok_count,
            "connectors_total": len(results),
            "checked_at": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def add(target: str, target_type: str = "username", nombre: str = "") -> Any:
        from models import db
        from models.osint import WatchlistOsint

        item = WatchlistOsint(
            target=target,
            target_type=target_type,
            nombre=nombre or target,
            activo=True,
            created_at=datetime.utcnow(),
        )
        db.session.add(item)
        db.session.commit()
        return item

    @staticmethod
    def deactivate(watchlist_id: int) -> bool:
        from models import db
        from models.osint import WatchlistOsint

        item = WatchlistOsint.query.get(watchlist_id)
        if item:
            item.activo = False
            db.session.commit()
            return True
        return False
