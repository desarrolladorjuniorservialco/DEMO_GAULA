from datetime import datetime
from . import db


class Persona(db.Model):
    __tablename__ = "personas"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_personas_documento",    "documento"),
        db.Index("ix_personas_nivel_riesgo", "nivel_riesgo"),
        db.Index("ix_personas_objetivo",     "es_objetivo"),
        {},
    )

    id               = db.Column(db.Integer, primary_key=True)
    nombres          = db.Column(db.String(100))
    apellidos        = db.Column(db.String(100))
    documento        = db.Column(db.String(30))
    tipo_documento   = db.Column(db.String(20))
    fecha_nacimiento = db.Column(db.Date)
    nacionalidad     = db.Column(db.String(50))
    sexo             = db.Column(db.String(10))
    nivel_riesgo     = db.Column(db.String(20))
    es_objetivo      = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by       = db.Column(db.String(50))
    updated_by       = db.Column(db.String(50))


class Alias(db.Model):
    __tablename__ = "alias"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_alias_valor", "valor"),
        {},
    )

    id         = db.Column(db.Integer, primary_key=True)
    valor      = db.Column(db.String(100), nullable=False)
    contexto   = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))


class Telefono(db.Model):
    __tablename__ = "telefonos"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_telefonos_numero", "numero"),
        {},
    )

    id         = db.Column(db.Integer, primary_key=True)
    numero     = db.Column(db.String(30), unique=True, nullable=False)
    operador   = db.Column(db.String(50))
    pais       = db.Column(db.String(5), default="CO")
    tipo       = db.Column(db.String(20))
    activo     = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))


class Correo(db.Model):
    __tablename__ = "correos"
    __bind_key__ = "intel"

    id         = db.Column(db.Integer, primary_key=True)
    direccion  = db.Column(db.String(200), unique=True, nullable=False)
    dominio    = db.Column(db.String(100))
    proveedor  = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))


class Direccion(db.Model):
    __tablename__ = "direcciones"
    __bind_key__ = "intel"

    id            = db.Column(db.Integer, primary_key=True)
    linea1        = db.Column(db.String(200))
    barrio        = db.Column(db.String(100))
    ciudad        = db.Column(db.String(100))
    departamento  = db.Column(db.String(100))
    pais          = db.Column(db.String(50), default="Colombia")
    codigo_postal = db.Column(db.String(10))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by    = db.Column(db.String(50))
    updated_by    = db.Column(db.String(50))


class Ubicacion(db.Model):
    __tablename__ = "ubicaciones"
    __bind_key__ = "intel"

    id               = db.Column(db.Integer, primary_key=True)
    latitud          = db.Column(db.Float)
    longitud         = db.Column(db.Float)
    descripcion      = db.Column(db.String(200))
    precision_metros = db.Column(db.Integer)
    fuente           = db.Column(db.String(100))
    fecha_captura    = db.Column(db.DateTime)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by       = db.Column(db.String(50))
    updated_by       = db.Column(db.String(50))


class Vehiculo(db.Model):
    __tablename__ = "vehiculos"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_vehiculos_placa", "placa"),
        {},
    )

    id         = db.Column(db.Integer, primary_key=True)
    placa      = db.Column(db.String(20))
    tipo       = db.Column(db.String(50))
    marca      = db.Column(db.String(50))
    modelo     = db.Column(db.String(50))
    anio       = db.Column(db.Integer)
    color      = db.Column(db.String(30))
    vin        = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))


class CuentaBancaria(db.Model):
    __tablename__ = "cuentas_bancarias"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_cuentas_numero",  "numero"),
        db.Index("ix_cuentas_entidad", "entidad"),
        {},
    )

    id                = db.Column(db.Integer, primary_key=True)
    numero            = db.Column(db.String(50))
    tipo              = db.Column(db.String(30))
    entidad           = db.Column(db.String(100))
    titular_declarado = db.Column(db.String(100))
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at        = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by        = db.Column(db.String(50))
    updated_by        = db.Column(db.String(50))


class RedSocial(db.Model):
    __tablename__ = "redes_sociales"
    __bind_key__ = "intel"

    id         = db.Column(db.Integer, primary_key=True)
    plataforma = db.Column(db.String(50))
    handle     = db.Column(db.String(100))
    url_perfil = db.Column(db.String(500))
    activo     = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))


class Organizacion(db.Model):
    __tablename__ = "organizaciones"
    __bind_key__ = "intel"

    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(200))
    tipo        = db.Column(db.String(50))
    descripcion = db.Column(db.Text)
    activa      = db.Column(db.Boolean)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by  = db.Column(db.String(50))
    updated_by  = db.Column(db.String(50))
