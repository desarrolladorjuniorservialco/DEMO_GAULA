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


# ── Task 7: M:M Junction Tables ──────────────────────────────────────────────

class PersonaAlias(db.Model):
    __tablename__ = "persona_alias"
    __bind_key__ = "intel"

    persona_id   = db.Column(db.Integer, db.ForeignKey("personas.id"), primary_key=True)
    alias_id     = db.Column(db.Integer, db.ForeignKey("alias.id"),    primary_key=True)
    fecha_inicio = db.Column(db.DateTime)
    fecha_fin    = db.Column(db.DateTime)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    created_by   = db.Column(db.String(50))

    persona = db.relationship("Persona", backref="alias_rel")
    alias   = db.relationship("Alias",   backref="personas_rel")


class PersonaTelefono(db.Model):
    __tablename__ = "persona_telefono"
    __bind_key__ = "intel"

    persona_id  = db.Column(db.Integer, db.ForeignKey("personas.id"),  primary_key=True)
    telefono_id = db.Column(db.Integer, db.ForeignKey("telefonos.id"), primary_key=True)
    relacion    = db.Column(db.String(50))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.String(50))

    persona  = db.relationship("Persona",  backref="telefonos_rel")
    telefono = db.relationship("Telefono", backref="personas_rel")


class PersonaCorreo(db.Model):
    __tablename__ = "persona_correo"
    __bind_key__ = "intel"

    persona_id = db.Column(db.Integer, db.ForeignKey("personas.id"), primary_key=True)
    correo_id  = db.Column(db.Integer, db.ForeignKey("correos.id"),  primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))

    persona = db.relationship("Persona", backref="correos_rel")
    correo  = db.relationship("Correo",  backref="personas_rel")


class PersonaDireccion(db.Model):
    __tablename__ = "persona_direccion"
    __bind_key__ = "intel"

    persona_id   = db.Column(db.Integer, db.ForeignKey("personas.id"),    primary_key=True)
    direccion_id = db.Column(db.Integer, db.ForeignKey("direcciones.id"), primary_key=True)
    tipo         = db.Column(db.String(50))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    created_by   = db.Column(db.String(50))

    persona   = db.relationship("Persona",   backref="direcciones_rel")
    direccion = db.relationship("Direccion", backref="personas_rel")


class PersonaVehiculo(db.Model):
    __tablename__ = "persona_vehiculo"
    __bind_key__ = "intel"

    persona_id  = db.Column(db.Integer, db.ForeignKey("personas.id"),  primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey("vehiculos.id"), primary_key=True)
    rol         = db.Column(db.String(50))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.String(50))

    persona  = db.relationship("Persona",  backref="vehiculos_rel")
    vehiculo = db.relationship("Vehiculo", backref="personas_rel")


class PersonaCuenta(db.Model):
    __tablename__ = "persona_cuenta"
    __bind_key__ = "intel"

    persona_id = db.Column(db.Integer, db.ForeignKey("personas.id"),          primary_key=True)
    cuenta_id  = db.Column(db.Integer, db.ForeignKey("cuentas_bancarias.id"), primary_key=True)
    rol        = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))

    persona = db.relationship("Persona",        backref="cuentas_rel")
    cuenta  = db.relationship("CuentaBancaria", backref="personas_rel")


class PersonaRedSocial(db.Model):
    __tablename__ = "persona_red_social"
    __bind_key__ = "intel"

    persona_id    = db.Column(db.Integer, db.ForeignKey("personas.id"),        primary_key=True)
    red_social_id = db.Column(db.Integer, db.ForeignKey("redes_sociales.id"),  primary_key=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    created_by    = db.Column(db.String(50))

    persona    = db.relationship("Persona",   backref="redes_rel")
    red_social = db.relationship("RedSocial", backref="personas_rel")


class PersonaOrganizacion(db.Model):
    __tablename__ = "persona_organizacion"
    __bind_key__ = "intel"

    persona_id      = db.Column(db.Integer, db.ForeignKey("personas.id"),        primary_key=True)
    organizacion_id = db.Column(db.Integer, db.ForeignKey("organizaciones.id"),  primary_key=True)
    rol_org         = db.Column(db.String(50))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    created_by      = db.Column(db.String(50))

    persona      = db.relationship("Persona",      backref="organizaciones_rel")
    organizacion = db.relationship("Organizacion", backref="personas_rel")


class OrganizacionTelefono(db.Model):
    __tablename__ = "organizacion_telefono"
    __bind_key__ = "intel"

    organizacion_id = db.Column(db.Integer, db.ForeignKey("organizaciones.id"), primary_key=True)
    telefono_id     = db.Column(db.Integer, db.ForeignKey("telefonos.id"),       primary_key=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    created_by      = db.Column(db.String(50))

    organizacion = db.relationship("Organizacion", backref="telefonos_rel")
    telefono     = db.relationship("Telefono",     backref="organizaciones_rel")


class OrganizacionCuenta(db.Model):
    __tablename__ = "organizacion_cuenta"
    __bind_key__ = "intel"

    organizacion_id = db.Column(db.Integer, db.ForeignKey("organizaciones.id"),   primary_key=True)
    cuenta_id       = db.Column(db.Integer, db.ForeignKey("cuentas_bancarias.id"), primary_key=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    created_by      = db.Column(db.String(50))

    organizacion = db.relationship("Organizacion",   backref="cuentas_rel")
    cuenta       = db.relationship("CuentaBancaria", backref="organizaciones_rel")


# Cross-DB junction tables (caso_id is a plain integer — no FK to nexo147.db)

class CasoPersona(db.Model):
    __tablename__ = "caso_persona"
    __bind_key__ = "intel"

    caso_id     = db.Column(db.Integer, primary_key=True)  # nexo147.casos.id, no FK
    persona_id  = db.Column(db.Integer, db.ForeignKey("personas.id"), primary_key=True)
    rol_en_caso = db.Column(db.String(50))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.String(50))

    persona = db.relationship("Persona", backref="casos_rel")


class CasoTelefono(db.Model):
    __tablename__ = "caso_telefono"
    __bind_key__ = "intel"

    caso_id     = db.Column(db.Integer, primary_key=True)
    telefono_id = db.Column(db.Integer, db.ForeignKey("telefonos.id"), primary_key=True)
    contexto    = db.Column(db.String(100))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.String(50))

    telefono = db.relationship("Telefono", backref="casos_rel")


class CasoUbicacion(db.Model):
    __tablename__ = "caso_ubicacion"
    __bind_key__ = "intel"

    caso_id        = db.Column(db.Integer, primary_key=True)
    ubicacion_id   = db.Column(db.Integer, db.ForeignKey("ubicaciones.id"), primary_key=True)
    tipo_ubicacion = db.Column(db.String(50))
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    created_by     = db.Column(db.String(50))

    ubicacion = db.relationship("Ubicacion", backref="casos_rel")


class CasoCuenta(db.Model):
    __tablename__ = "caso_cuenta"
    __bind_key__ = "intel"

    caso_id   = db.Column(db.Integer, primary_key=True)
    cuenta_id = db.Column(db.Integer, db.ForeignKey("cuentas_bancarias.id"), primary_key=True)
    uso       = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))

    cuenta = db.relationship("CuentaBancaria", backref="casos_rel")


# ── Task 8: Graph Module + HallazgoIntel ──────────────────────────────────────

class IntelNode(db.Model):
    __tablename__ = "intel_nodes"
    __bind_key__ = "intel"
    __table_args__ = (
        db.UniqueConstraint("entity_type", "entity_id", name="uq_node_entity"),
        {},
    )

    id            = db.Column(db.Integer, primary_key=True)
    entity_type   = db.Column(db.String(50), nullable=False)
    entity_id     = db.Column(db.Integer,    nullable=False)
    label         = db.Column(db.String(200))
    nivel_riesgo  = db.Column(db.String(20))
    metadata_json = db.Column(db.Text)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by    = db.Column(db.String(50))
    updated_by    = db.Column(db.String(50))

    edges_out = db.relationship("IntelEdge", foreign_keys="IntelEdge.source_node_id",
                                backref="source_node")
    edges_in  = db.relationship("IntelEdge", foreign_keys="IntelEdge.target_node_id",
                                backref="target_node")


class IntelEdge(db.Model):
    __tablename__ = "intel_edges"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_edges_source", "source_node_id"),
        db.Index("ix_edges_target", "target_node_id"),
        db.Index("ix_edges_tipo",   "tipo_relacion"),
        {},
    )

    id              = db.Column(db.Integer, primary_key=True)
    source_node_id  = db.Column(db.Integer, db.ForeignKey("intel_nodes.id"), nullable=False)
    target_node_id  = db.Column(db.Integer, db.ForeignKey("intel_nodes.id"), nullable=False)
    tipo_relacion   = db.Column(db.String(50))
    descripcion     = db.Column(db.String(200))
    confianza       = db.Column(db.Float, default=1.0)
    fuente          = db.Column(db.String(100))
    fecha_deteccion = db.Column(db.DateTime)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by      = db.Column(db.String(50))
    updated_by      = db.Column(db.String(50))


class HallazgoIntel(db.Model):
    __tablename__ = "hallazgos_intel"
    __bind_key__ = "intel"

    id                  = db.Column(db.Integer, primary_key=True)
    titulo              = db.Column(db.String(200))
    descripcion         = db.Column(db.Text)
    nivel_clasificacion = db.Column(db.String(20))
    caso_referencia_id  = db.Column(db.Integer)   # nexo147.casos.id — plain int, no FK
    analista_id         = db.Column(db.Integer)   # nexo147.usuarios.id — plain int, no FK
    estado              = db.Column(db.String(20))
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at          = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by          = db.Column(db.String(50))
    updated_by          = db.Column(db.String(50))
