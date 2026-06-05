"""history/repository.py — Acceso a datos del historial de consultas OSINT."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


class HistoryRepository:
    """Queries de solo lectura sobre ConsultaOsint y ResultadoOsint."""

    @staticmethod
    def list_recent(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        from models.osint import ConsultaOsint

        rows = (
            ConsultaOsint.query
            .order_by(ConsultaOsint.fecha.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [_consulta_to_dict(r) for r in rows]

    @staticmethod
    def get_by_id(consulta_id: int) -> dict[str, Any] | None:
        from models.osint import ConsultaOsint, ResultadoOsint

        consulta = ConsultaOsint.query.get(consulta_id)
        if not consulta:
            return None

        resultados = (
            ResultadoOsint.query
            .filter_by(consulta_id=consulta_id)
            .order_by(ResultadoOsint.id)
            .all()
        )
        d = _consulta_to_dict(consulta)
        d["resultados"] = [_resultado_to_dict(r) for r in resultados]
        return d

    @staticmethod
    def search(target: str = "", days: int = 30, limit: int = 100) -> list[dict[str, Any]]:
        from models.osint import ConsultaOsint

        q = ConsultaOsint.query
        if target:
            q = q.filter(ConsultaOsint.target.ilike(f"%{target}%"))
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            q = q.filter(ConsultaOsint.fecha >= since)

        rows = q.order_by(ConsultaOsint.fecha.desc()).limit(limit).all()
        return [_consulta_to_dict(r) for r in rows]

    @staticmethod
    def delete(consulta_id: int) -> bool:
        from models import db
        from models.osint import ConsultaOsint, ResultadoOsint

        ResultadoOsint.query.filter_by(consulta_id=consulta_id).delete()
        deleted = ConsultaOsint.query.filter_by(id=consulta_id).delete()
        db.session.commit()
        return bool(deleted)


def _consulta_to_dict(c: Any) -> dict[str, Any]:
    return {
        "id":          c.id,
        "target":      c.target,
        "target_type": getattr(c, "target_type", None),
        "estado":      getattr(c, "estado", None),
        "fecha":       c.fecha.isoformat() if c.fecha else None,
        "usuario_id":  getattr(c, "usuario_id", None),
    }


def _resultado_to_dict(r: Any) -> dict[str, Any]:
    return {
        "id":        r.id,
        "fuente":    getattr(r, "fuente", None),
        "tipo":      getattr(r, "tipo", None),
        "valor":     getattr(r, "valor", None),
        "confianza": getattr(r, "confianza", None),
    }
