from datetime import datetime
from . import db


class FuenteOsint(db.Model):
    __tablename__ = "fuentes_osint"
    __bind_key__ = "osint"

    id                 = db.Column(db.Integer, primary_key=True)
    nombre             = db.Column(db.String(100), unique=True, nullable=False)
    tipo               = db.Column(db.String(50))
    url_base           = db.Column(db.String(500))
    requiere_key       = db.Column(db.Boolean, default=True)
    activa             = db.Column(db.Boolean, default=True)
    rate_limit_por_min = db.Column(db.Integer)
    descripcion        = db.Column(db.Text)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by         = db.Column(db.String(50))
    updated_by         = db.Column(db.String(50))

    consultas = db.relationship("ConsultaOsint", back_populates="fuente")


class ConsultaOsint(db.Model):
    __tablename__ = "consultas_osint"
    __bind_key__ = "osint"
    __table_args__ = (
        db.Index("ix_consultas_valor",  "valor_consultado"),
        db.Index("ix_consultas_tipo",   "tipo_consulta"),
        db.Index("ix_consultas_fuente", "fuente_id"),
        {},
    )

    id                 = db.Column(db.Integer, primary_key=True)
    fuente_id          = db.Column(db.Integer, db.ForeignKey("fuentes_osint.id"), nullable=False)
    tipo_consulta      = db.Column(db.String(50))
    valor_consultado   = db.Column(db.String(500))
    caso_referencia_id = db.Column(db.Integer)   # nexo147.casos.id — plain int, no FK
    entity_type        = db.Column(db.String(50))
    entity_id          = db.Column(db.Integer)   # intel.db entity — plain int, no FK
    estado             = db.Column(db.String(20))
    usuario_id         = db.Column(db.Integer)   # nexo147.usuarios.id — plain int, no FK
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    created_by         = db.Column(db.String(50))

    fuente     = db.relationship("FuenteOsint",  back_populates="consultas")
    cache      = db.relationship("CacheConsulta",  back_populates="consulta", uselist=False)
    resultados = db.relationship("ResultadoOsint", back_populates="consulta")


class CacheConsulta(db.Model):
    __tablename__ = "cache_consultas"
    __bind_key__ = "osint"

    id             = db.Column(db.Integer, primary_key=True)
    consulta_id    = db.Column(db.Integer, db.ForeignKey("consultas_osint.id"), nullable=False)
    hash_clave     = db.Column(db.String(64), unique=True, nullable=False)
    respuesta_raw  = db.Column(db.Text)
    codigo_http    = db.Column(db.Integer)
    fecha_consulta = db.Column(db.DateTime, default=datetime.utcnow)
    expira_en      = db.Column(db.DateTime)
    hits           = db.Column(db.Integer, default=0)

    consulta = db.relationship("ConsultaOsint", back_populates="cache")


class ResultadoOsint(db.Model):
    __tablename__ = "resultados_osint"
    __bind_key__ = "osint"

    id            = db.Column(db.Integer, primary_key=True)
    consulta_id   = db.Column(db.Integer, db.ForeignKey("consultas_osint.id"), nullable=False)
    tipo_hallazgo = db.Column(db.String(50))
    titulo        = db.Column(db.String(200))
    descripcion   = db.Column(db.Text)
    datos_json    = db.Column(db.Text)
    relevancia    = db.Column(db.Float, default=0.5)
    verificado    = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by    = db.Column(db.String(50))
    updated_by    = db.Column(db.String(50))

    consulta = db.relationship("ConsultaOsint", back_populates="resultados")


class IndicadorRiesgo(db.Model):
    __tablename__ = "indicadores_riesgo"
    __bind_key__ = "osint"
    __table_args__ = (
        db.Index("ix_indicadores_tipo",   "tipo"),
        db.Index("ix_indicadores_valor",  "valor"),
        db.Index("ix_indicadores_riesgo", "nivel_riesgo"),
        db.Index("ix_indicadores_activo", "activo"),
        {},
    )

    id                 = db.Column(db.Integer, primary_key=True)
    tipo               = db.Column(db.String(50))
    valor              = db.Column(db.String(500), nullable=False)
    descripcion        = db.Column(db.String(200))
    nivel_riesgo       = db.Column(db.String(20))
    fuente_origen      = db.Column(db.String(100))
    caso_referencia_id = db.Column(db.Integer)   # nexo147.casos.id — plain int, no FK
    activo             = db.Column(db.Boolean, default=True)
    fecha_deteccion    = db.Column(db.DateTime)
    fecha_expiracion   = db.Column(db.DateTime)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by         = db.Column(db.String(50))
    updated_by         = db.Column(db.String(50))


class WatchlistOsint(db.Model):
    __tablename__ = "watchlists_osint"
    __bind_key__ = "osint"
    __table_args__ = (
        db.Index("ix_watchlists_target", "target"),
        db.Index("ix_watchlists_active", "activo"),
        db.Index("ix_watchlists_target_type", "target_type"),
        {},
    )

    id                 = db.Column(db.Integer, primary_key=True)
    nombre             = db.Column(db.String(120), nullable=False)
    target             = db.Column(db.String(500), nullable=False)
    target_type        = db.Column(db.String(50), nullable=False, default="unknown")
    source_hint        = db.Column(db.String(50), default="all")
    frecuencia_minutos = db.Column(db.Integer, default=1440)
    activo             = db.Column(db.Boolean, default=True)
    last_run_at        = db.Column(db.DateTime)
    last_risk_level    = db.Column(db.String(20))
    last_risk_score    = db.Column(db.Integer, default=0)
    last_result_json   = db.Column(db.Text)
    notas              = db.Column(db.Text)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by         = db.Column(db.String(50))
    updated_by         = db.Column(db.String(50))
