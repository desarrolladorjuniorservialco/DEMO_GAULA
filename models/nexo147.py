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

    # casos = db.relationship("Caso", back_populates="unidad_gaula")  # defined in future task
