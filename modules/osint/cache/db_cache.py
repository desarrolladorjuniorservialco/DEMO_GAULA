"""cache/db_cache.py — L3 database cache sobre CacheConsulta (osint.db)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

log = logging.getLogger(__name__)


class DbCache:
    """L3 cache persistente usando la tabla CacheConsulta en osint.db."""

    def get(self, cache_key: str) -> dict[str, Any] | None:
        try:
            from models import db
            from models.osint import CacheConsulta

            cache = db.session.query(CacheConsulta).filter_by(hash_clave=cache_key).first()
            if not cache or not cache.expira_en:
                return None
            if cache.expira_en < datetime.utcnow():
                return None
            payload = json.loads(cache.respuesta_raw or "{}")
            cache.hits = (cache.hits or 0) + 1
            db.session.commit()
            return payload
        except Exception as exc:
            log.debug("DbCache.get error: %s", exc)
            return None

    def set(self, cache_key: str, consulta_id: int, payload: dict[str, Any], ttl_hours: int = 1) -> None:
        try:
            from models import db
            from models.osint import CacheConsulta

            existing = db.session.query(CacheConsulta).filter_by(hash_clave=cache_key).first()
            if existing:
                existing.respuesta_raw = json.dumps(payload, ensure_ascii=False, default=str)
                existing.expira_en = datetime.utcnow() + timedelta(hours=ttl_hours)
                existing.hits = 0
            else:
                entry = CacheConsulta(
                    consulta_id=consulta_id,
                    hash_clave=cache_key,
                    respuesta_raw=json.dumps(payload, ensure_ascii=False, default=str),
                    codigo_http=200,
                    expira_en=datetime.utcnow() + timedelta(hours=ttl_hours),
                    hits=0,
                )
                db.session.add(entry)
            db.session.commit()
        except Exception as exc:
            log.debug("DbCache.set error: %s", exc)
            try:
                from models import db  # noqa: F811
                db.session.rollback()
            except Exception:
                pass

    def invalidate(self, cache_key: str) -> None:
        try:
            from models import db
            from models.osint import CacheConsulta

            db.session.query(CacheConsulta).filter_by(hash_clave=cache_key).delete()
            db.session.commit()
        except Exception as exc:
            log.debug("DbCache.invalidate error: %s", exc)
