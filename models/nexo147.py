from datetime import datetime
from . import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre        = db.Column(db.String(100), nullable=False)
    rol           = db.Column(db.String(20), nullable=False)
    activo        = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by    = db.Column(db.String(50))
    updated_by    = db.Column(db.String(50))


class UnidadGaula(db.Model):
    __tablename__ = "unidades_gaula"

    id           = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(100), unique=True, nullable=False)
    ciudad       = db.Column(db.String(100))
    departamento = db.Column(db.String(100))
    activa       = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by   = db.Column(db.String(50))
    updated_by   = db.Column(db.String(50))

    casos = db.relationship("Caso", back_populates="unidad_gaula")


class Caso(db.Model):
    __tablename__ = "casos"
    __table_args__ = (
        db.Index("ix_casos_estado",    "estado"),
        db.Index("ix_casos_prioridad", "prioridad"),
        db.Index("ix_casos_tipo",      "tipo_caso"),
        db.Index("ix_casos_fecha",     "fecha_registro"),
        {},
    )

    id                  = db.Column(db.Integer, primary_key=True)
    id_caso             = db.Column(db.String(36), unique=True, nullable=False)
    fecha_registro      = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, onupdate=datetime.utcnow)
    estado              = db.Column(db.String(20), default="Recibido")
    prioridad           = db.Column(db.String(20))
    tipo_caso           = db.Column(db.String(50))
    canal_recepcion     = db.Column(db.String(50))
    unidad_gaula_id     = db.Column(db.Integer, db.ForeignKey("unidades_gaula.id"))
    descripcion         = db.Column(db.Text)
    observaciones       = db.Column(db.Text)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at          = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by          = db.Column(db.String(50))
    updated_by          = db.Column(db.String(50))

    unidad_gaula = db.relationship("UnidadGaula", back_populates="casos")
    # reportantes  = db.relationship("CasoReportante", back_populates="caso")  # defined in future task
    # evidencias   = db.relationship("Evidencia",       back_populates="caso")  # defined in future task
    # eventos      = db.relationship("EventoCaso",      back_populates="caso")  # defined in future task
    # medios_pago  = db.relationship("MedioPago",       back_populates="caso")  # defined in future task
