# Modelos de datos — NEXO-147

Todos los modelos usan **SQLAlchemy 2.0** con la instancia `db` de `modules/extensions.py`.

---

## Convenciones

- Todos los modelos heredan de `db.Model`
- Los que pertenecen a una base secundaria declaran `__bind_key__`
- Columnas de auditoría estándar: `created_at`, `updated_at`, `created_by`, `updated_by`
- Las relaciones inter-base no usan FK explícita (int simple para evitar dependencias circulares)

---

## models/nexo147.py — Dominio core

### `Usuario`

```python
class Usuario(db.Model):
    __tablename__ = "usuarios"

    id: int (PK)
    username: str (UNIQUE, NOT NULL)
    password_hash: str
    nombre: str
    rol: str  # admin | director | analista | operador
    activo: bool (default=True)
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
```

**Métodos:**
- `set_password(password)` — genera hash Werkzeug
- `check_password(password)` → `bool` — verifica hash

---

### `UnidadGaula`

```python
class UnidadGaula(db.Model):
    __tablename__ = "unidades_gaula"

    id: int (PK)
    nombre: str (UNIQUE)        # "GAULA Bogotá D.C."
    ciudad: str
    departamento: str
    activa: bool (default=True)
    # + campos auditoría
```

**Relaciones:**
- `casos` → `relationship("Caso", backref="unidad")`

---

### `Caso`

```python
class Caso(db.Model):
    __tablename__ = "casos"

    id: int (PK)
    id_caso: str (UNIQUE)       # UUID generado en app
    fecha_registro: datetime
    fecha_actualizacion: datetime
    estado: str                  # Recibido | En proceso | Cerrado
    prioridad: str               # Baja | Media | Alta | Crítica
    tipo_caso: str
    canal_recepcion: str
    unidad_gaula_id: int (FK → UnidadGaula)
    descripcion: str
    observaciones: str
    # + campos auditoría
```

**Relaciones:**
- `unidad` ← backref desde `UnidadGaula`
- `reportantes` → `relationship("Reportante", secondary="caso_reportante")`
- `evidencias` → `relationship("Evidencia", backref="caso")`
- `eventos` → `relationship("EventoCaso", backref="caso")`
- `medios_pago` → `relationship("MedioPago", backref="caso")`

---

### `Reportante`

```python
class Reportante(db.Model):
    __tablename__ = "reportantes"

    id: int (PK)
    nombre: str
    documento: str
    telefono: str
    anonimo: bool (default=False)
    # + campos auditoría
```

**Relaciones:**
- `casos` → M:N via `CasoReportante`

---

### `CasoReportante` (tabla de unión)

```python
class CasoReportante(db.Model):
    __tablename__ = "caso_reportante"

    caso_id: int (FK → Caso, PK)
    reportante_id: int (FK → Reportante, PK)
    rol_en_caso: str             # denunciante | victima | testigo
    created_at: datetime
    created_by: str
```

---

### `Evidencia`

```python
class Evidencia(db.Model):
    __tablename__ = "evidencias"

    id: int (PK)
    caso_id: int (FK → Caso, NOT NULL)
    tipo: str                    # audio | video | documento | referencia
    descripcion: str
    ruta_archivo: str
    hash_sha256: str
    # + campos auditoría
```

---

### `EventoCaso`

Registro inmutable de cambios de estado (audit trail).

```python
class EventoCaso(db.Model):
    __tablename__ = "eventos_caso"

    id: int (PK)
    caso_id: int (FK → Caso, NOT NULL)
    tipo_evento: str             # creacion | cambio_estado | escalada
    descripcion: str
    estado_anterior: str
    estado_nuevo: str
    created_at: datetime
    created_by: str
```

---

### `MedioPago`

```python
class MedioPago(db.Model):
    __tablename__ = "medios_pago"

    id: int (PK)
    caso_id: int (FK → Caso, NOT NULL)
    tipo: str                    # nequi | daviplata | transferencia
    valor_exigido: Numeric(15, 2)
    moneda: str (default="COP")
    referencia: str              # número de cuenta o teléfono
    # + campos auditoría
```

---

## models/intel.py — Dominio inteligencia

Todos los modelos declaran `__bind_key__ = "intel"`.

### Entidades principales

| Modelo | Tabla | Campos clave |
|---|---|---|
| `Persona` | `personas` | nombre, documento, fecha_nac, nacionalidad, sexo, nivel_riesgo, es_objetivo |
| `Alias` | `alias` | valor (nombre alternativo), tipo |
| `Telefono` | `telefonos` | numero, operador, pais, tipo |
| `Correo` | `correos` | direccion, dominio, proveedor |
| `Direccion` | `direcciones` | linea1, barrio, ciudad, departamento, codigo_postal |
| `Ubicacion` | `ubicaciones` | latitud, longitud, descripcion, precision |
| `Vehiculo` | `vehiculos` | placa, tipo, marca, modelo, anio, color, vin |
| `CuentaBancaria` | `cuentas_bancarias` | numero, tipo, entidad, titular |
| `RedSocial` | `redes_sociales` | plataforma, handle, url_perfil |
| `Organizacion` | `organizaciones` | nombre, tipo, descripcion |

---

### Modelos de unión M:N (intel.db)

| Modelo | Tabla | Une |
|---|---|---|
| `PersonaAlias` | `persona_alias` | Persona ↔ Alias |
| `PersonaTelefono` | `persona_telefono` | Persona ↔ Telefono |
| `PersonaCorreo` | `persona_correo` | Persona ↔ Correo |
| `PersonaDireccion` | `persona_direccion` | Persona ↔ Direccion |
| `PersonaVehiculo` | `persona_vehiculo` | Persona ↔ Vehiculo |
| `PersonaCuenta` | `persona_cuenta` | Persona ↔ CuentaBancaria |
| `PersonaRedSocial` | `persona_red_social` | Persona ↔ RedSocial |
| `PersonaOrganizacion` | `persona_organizacion` | Persona ↔ Organizacion |
| `OrganizacionTelefono` | `organizacion_telefono` | Organizacion ↔ Telefono |
| `OrganizacionCuenta` | `organizacion_cuenta` | Organizacion ↔ CuentaBancaria |

---

### Modelos de unión inter-base (nexo147 ↔ intel)

Almacenados en `intel.db`. Usan `int` simple (no FK) para el ID del caso.

| Modelo | Tabla | Vincula |
|---|---|---|
| `CasoPersona` | `caso_persona` | `caso_id` (nexo147) ↔ `persona_id` |
| `CasoTelefono` | `caso_telefono` | `caso_id` ↔ `telefono_id` |
| `CasoUbicacion` | `caso_ubicacion` | `caso_id` ↔ `ubicacion_id` |
| `CasoCuenta` | `caso_cuenta` | `caso_id` ↔ `cuenta_id` |

---

### `IntelNode`

```python
class IntelNode(db.Model):
    __bind_key__ = "intel"
    __tablename__ = "intel_nodes"

    id: int (PK)
    entity_type: str         # persona | telefono | correo | vehiculo
    entity_id: int           # ID de la entidad en intel.db
    label: str               # Texto visible en grafo
    nivel_riesgo: str        # bajo | medio | alto | crítico
    metadata_json: str       # JSON con atributos extra
    created_at: datetime
```

---

### `IntelEdge`

```python
class IntelEdge(db.Model):
    __bind_key__ = "intel"
    __tablename__ = "intel_edges"

    id: int (PK)
    source_node_id: int (FK → IntelNode)
    target_node_id: int (FK → IntelNode)
    tipo_relacion: str       # usa_telefono | pertenece_a | contactó_con
    confianza: float         # 0.0–1.0
    fuente: str
    fecha_deteccion: datetime
```

---

### `HallazgoIntel`

```python
class HallazgoIntel(db.Model):
    __bind_key__ = "intel"
    __tablename__ = "hallazgos_intel"

    id: int (PK)
    titulo: str
    descripcion: str
    nivel_clasificacion: str  # público | reservado | secreto
    caso_referencia_id: int   # Sin FK (inter-base)
    analista_id: int          # Sin FK (inter-base)
    estado: str               # borrador | revisión | aprobado
    created_at: datetime
    updated_at: datetime
```

---

## models/osint.py — Dominio OSINT

Todos los modelos declaran `__bind_key__ = "osint"`.

### `FuenteOsint`

```python
class FuenteOsint(db.Model):
    __bind_key__ = "osint"
    __tablename__ = "fuentes_osint"

    id: int (PK)
    nombre: str
    tipo: str            # api | scraper | search | plugin
    url_base: str
    requiere_key: bool
    activa: bool (default=True)
    rate_limit: int      # solicitudes por minuto
```

---

### `ConsultaOsint`

```python
class ConsultaOsint(db.Model):
    __bind_key__ = "osint"
    __tablename__ = "consultas_osint"

    id: int (PK)
    fuente_id: int (FK → FuenteOsint)
    tipo_consulta: str   # username | email | phone | domain | ip
    valor_consultado: str
    caso_referencia_id: int   # Sin FK
    entity_type: str
    entity_id: int
    estado: str          # pendiente | completado | error
    usuario_id: int
    created_at: datetime
    updated_at: datetime
```

---

### `CacheConsulta`

```python
class CacheConsulta(db.Model):
    __bind_key__ = "osint"
    __tablename__ = "cache_consultas"

    id: int (PK)
    consulta_id: int (FK → ConsultaOsint)
    hash_clave: str      # SHA-256 de los parámetros
    respuesta_raw: str   # Respuesta cruda del servicio
    codigo_http: int
    expira_en: datetime
    hits: int            # Número de usos del caché
```

---

### `ResultadoOsint`

```python
class ResultadoOsint(db.Model):
    __bind_key__ = "osint"
    __tablename__ = "resultados_osint"

    id: int (PK)
    consulta_id: int (FK → ConsultaOsint)
    tipo_hallazgo: str   # perfil | actividad | red | imagen
    titulo: str
    descripcion: str
    datos_json: str      # JSON con datos estructurados
    relevancia: float    # 0.0–1.0
    verificado: bool
```

---

### `IndicadorRiesgo`

```python
class IndicadorRiesgo(db.Model):
    __bind_key__ = "osint"
    __tablename__ = "indicadores_riesgo"

    id: int (PK)
    tipo: str            # telefono | email | dominio | ip
    valor: str
    descripcion: str
    nivel_riesgo: str    # bajo | medio | alto | crítico
    fuente_origen: str
    caso_referencia_id: int  # Sin FK
    activo: bool (default=True)
    fecha_deteccion: datetime
    fecha_expiracion: datetime
```

---

## models/osint_graph.py — Grafo OSINT (Cytoscape)

### `Node`

```python
class Node(db.Model):
    __bind_key__ = "osint"
    __tablename__ = "node"

    id: int (PK)
    type: str            # email | phone | domain | person | ip
    value: str (UNIQUE)  # Identificador único del nodo
    label: str           # Texto visible
    group: str           # contact | network | org | target
    metadata_payload: str  # JSON con atributos Cytoscape
    created_at: datetime
    updated_at: datetime
```

**Helper:**
```python
def get_or_create_node(db_session, type, value, label, group) -> Node:
    ...
```

---

### `OsintEdge`

```python
class OsintEdge(db.Model):
    __bind_key__ = "osint"
    __tablename__ = "edge"

    id: int (PK)
    source_id: int (FK → Node)
    target_id: int (FK → Node)
    relation_type: str
    metadata_payload: str  # JSON

def create_edge(db_session, source_id, target_id, relation_type) -> OsintEdge:
    ...
```

---

## Importación de modelos

```python
# Acceso centralizado via models/__init__.py
from models.nexo147 import Usuario, UnidadGaula, Caso, Reportante, Evidencia, EventoCaso, MedioPago
from models.intel import Persona, Telefono, IntelNode, IntelEdge, HallazgoIntel
from models.osint import FuenteOsint, ConsultaOsint, ResultadoOsint, IndicadorRiesgo
from models.osint_graph import Node, OsintEdge, get_or_create_node, create_edge
```
