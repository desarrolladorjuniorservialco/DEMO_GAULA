# Base de datos — NEXO-147

Motor: **SQLite** via **Flask-SQLAlchemy 3.1.1 / SQLAlchemy 2.0.50**  
Archivos: `data/nexo147.db`, `data/intel.db`, `data/osint.db`  
Creación: automática al arrancar la app (`db.create_all()` dentro de `create_app()`)

---

## Bases de datos

| Archivo | Bind key | Propósito |
|---|---|---|
| `data/nexo147.db` | `(default)` | Core: casos, usuarios, reportantes, evidencias |
| `data/intel.db` | `"intel"` | Inteligencia: personas, entidades, grafo de relaciones |
| `data/osint.db` | `"osint"` | OSINT: fuentes, consultas, resultados, grafo |

---

## 1. nexo147.db — Base de datos principal

### `usuarios`

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | INTEGER | PK, autoincremento | Identificador interno |
| `username` | VARCHAR(50) | UNIQUE, NOT NULL | Nombre de usuario para login |
| `password_hash` | VARCHAR(256) | NOT NULL | Hash werkzeug (pbkdf2:sha256) |
| `nombre` | VARCHAR(100) | NOT NULL | Nombre visible en la interfaz |
| `rol` | VARCHAR(20) | NOT NULL | `admin`, `director`, `analista`, `operador` |
| `activo` | BOOLEAN | DEFAULT TRUE | Desactivar sin eliminar |
| `created_at` | DATETIME | DEFAULT now | Fecha de creación |
| `updated_at` | DATETIME | on update | Fecha de última modificación |
| `created_by` | VARCHAR(50) | | Username que creó el registro |
| `updated_by` | VARCHAR(50) | | Username que modificó el registro |

### `unidades_gaula`

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador |
| `nombre` | VARCHAR(100) | UNIQUE, NOT NULL | Ej: "GAULA Bogotá D.C." |
| `ciudad` | VARCHAR(100) | | Ciudad de operación |
| `departamento` | VARCHAR(100) | | Departamento |
| `activa` | BOOLEAN | DEFAULT TRUE | Estado de la unidad |
| `created_at`, `updated_at`, `created_by`, `updated_by` | | | Auditoría |

### `casos`

Entidad principal del sistema.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador interno |
| `id_caso` | VARCHAR(36) | UNIQUE, NOT NULL | UUID visible al usuario |
| `fecha_registro` | DATETIME | DEFAULT now | Fecha de creación |
| `fecha_actualizacion` | DATETIME | on update | Última modificación |
| `estado` | VARCHAR(20) | DEFAULT "Recibido" | `Recibido`, `En proceso`, `Cerrado` |
| `prioridad` | VARCHAR(20) | | `Baja`, `Media`, `Alta`, `Crítica` |
| `tipo_caso` | VARCHAR(50) | | `Extorsión`, `Secuestro`, `Amenaza`, etc. |
| `canal_recepcion` | VARCHAR(50) | | `Línea 147`, `Web`, `Presencial` |
| `unidad_gaula_id` | INTEGER | FK → `unidades_gaula.id` | Unidad receptora |
| `descripcion` | TEXT | | Descripción detallada |
| `observaciones` | TEXT | | Notas del operador |
| `created_at`, `updated_at`, `created_by`, `updated_by` | | | Auditoría |

**Índices:** `ix_casos_estado`, `ix_casos_prioridad`, `ix_casos_tipo`, `ix_casos_fecha`

### `reportantes`

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador interno |
| `nombre` | VARCHAR(100) | | Nombre completo |
| `documento` | VARCHAR(30) | | Número de documento de identidad |
| `telefono` | VARCHAR(20) | | Teléfono de contacto |
| `anonimo` | BOOLEAN | DEFAULT FALSE | Denuncia anónima |
| `created_at`, `updated_at`, `created_by`, `updated_by` | | | Auditoría |

**Índices:** `ix_reportantes_documento`, `ix_reportantes_telefono`

### `caso_reportante` (tabla de unión M:N)

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `caso_id` | INTEGER | FK → `casos.id`, PK | Referencia al caso |
| `reportante_id` | INTEGER | FK → `reportantes.id`, PK | Referencia al reportante |
| `rol_en_caso` | VARCHAR(50) | | `denunciante`, `victima`, `testigo`, etc. |
| `created_at` | DATETIME | DEFAULT now | Fecha de asociación |
| `created_by` | VARCHAR(50) | | Usuario que asoció |

### `evidencias`

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador |
| `caso_id` | INTEGER | FK → `casos.id`, NOT NULL | Caso al que pertenece |
| `tipo` | VARCHAR(50) | | `audio`, `video`, `documento`, `referencia` |
| `descripcion` | VARCHAR(200) | | Descripción de la evidencia |
| `ruta_archivo` | VARCHAR(500) | | Ruta al archivo almacenado |
| `hash_sha256` | VARCHAR(64) | | Hash de integridad |
| `created_at`, `updated_at`, `created_by`, `updated_by` | | | Auditoría |

### `eventos_caso` (auditoría de cambios de estado)

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador |
| `caso_id` | INTEGER | FK → `casos.id`, NOT NULL | Caso afectado |
| `tipo_evento` | VARCHAR(50) | | `creacion`, `cambio_estado`, `escalada`, etc. |
| `descripcion` | TEXT | | Detalle del evento |
| `estado_anterior` | VARCHAR(20) | | Estado previo |
| `estado_nuevo` | VARCHAR(20) | | Estado resultante |
| `created_at` | DATETIME | DEFAULT now | Timestamp del evento |
| `created_by` | VARCHAR(50) | | Usuario responsable |

### `medios_pago`

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador |
| `caso_id` | INTEGER | FK → `casos.id`, NOT NULL | Caso asociado |
| `tipo` | VARCHAR(50) | | `nequi`, `daviplata`, `transferencia`, etc. |
| `valor_exigido` | NUMERIC(15,2) | | Monto exigido |
| `moneda` | VARCHAR(10) | DEFAULT "COP" | Moneda |
| `referencia` | VARCHAR(100) | | Número de cuenta, teléfono, etc. |
| `created_at`, `updated_at`, `created_by`, `updated_by` | | | Auditoría |

---

## 2. intel.db — Base de datos de inteligencia

### Tablas de entidades

| Tabla | Descripción |
|---|---|
| `personas` | Personas de interés (nombre, documento, fechanac, nacionalidad, sexo, nivel_riesgo, objetivo) |
| `alias` | Apodos o nombres alternativos |
| `telefonos` | Números de teléfono (operador, país, tipo) |
| `correos` | Correos electrónicos (dominio, proveedor) |
| `direcciones` | Direcciones físicas (línea1, barrio, ciudad, departamento, código postal) |
| `ubicaciones` | Coordenadas GPS (latitud, longitud, descripción, precisión) |
| `vehiculos` | Vehículos (placa, tipo, marca, modelo, año, color, VIN) |
| `cuentas_bancarias` | Cuentas bancarias (número, tipo, entidad, titular) |
| `redes_sociales` | Perfiles en redes (plataforma, handle, url_perfil) |
| `organizaciones` | Grupos u organizaciones (nombre, tipo, descripción) |

### Tablas de unión M:N (entidades ↔ entidades)

| Tabla | Relación |
|---|---|
| `persona_alias` | Persona ↔ Alias |
| `persona_telefono` | Persona ↔ Teléfono |
| `persona_correo` | Persona ↔ Correo |
| `persona_direccion` | Persona ↔ Dirección |
| `persona_vehiculo` | Persona ↔ Vehículo |
| `persona_cuenta` | Persona ↔ Cuenta bancaria |
| `persona_red_social` | Persona ↔ Red social |
| `persona_organizacion` | Persona ↔ Organización |
| `organizacion_telefono` | Organización ↔ Teléfono |
| `organizacion_cuenta` | Organización ↔ Cuenta bancaria |

### Tablas de unión inter-base (nexo147 ↔ intel)

Estas tablas vinculan casos del nexo147.db con entidades del intel.db. Usan `int` en lugar de FK explícita para evitar dependencias circulares entre bases de datos.

| Tabla | Vincula |
|---|---|
| `caso_persona` | `casos.id` (nexo147) → `personas.id` (intel) |
| `caso_telefono` | `casos.id` → `telefonos.id` |
| `caso_ubicacion` | `casos.id` → `ubicaciones.id` |
| `caso_cuenta` | `casos.id` → `cuentas_bancarias.id` |

### `intel_nodes` — Nodos del grafo

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `entity_type` | VARCHAR(50) | `persona`, `telefono`, `correo`, `vehiculo`, etc. |
| `entity_id` | INTEGER | ID de la entidad referenciada |
| `label` | VARCHAR(200) | Etiqueta visible en el grafo |
| `nivel_riesgo` | VARCHAR(20) | `bajo`, `medio`, `alto`, `crítico` |
| `metadata_json` | TEXT | Atributos adicionales (JSON) |
| `created_at` | DATETIME | Fecha de creación |

### `intel_edges` — Aristas del grafo

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `source_node_id` | INTEGER FK → `intel_nodes.id` | Nodo origen |
| `target_node_id` | INTEGER FK → `intel_nodes.id` | Nodo destino |
| `tipo_relacion` | VARCHAR(100) | `usa_telefono`, `pertenece_a`, `contactó_con`, etc. |
| `confianza` | FLOAT | Nivel de confianza (0.0–1.0) |
| `fuente` | VARCHAR(100) | Fuente de la relación |
| `fecha_deteccion` | DATETIME | Cuándo se detectó |

### `hallazgos_intel`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `titulo` | VARCHAR(200) | Título del hallazgo |
| `descripcion` | TEXT | Descripción detallada |
| `nivel_clasificacion` | VARCHAR(20) | `público`, `reservado`, `secreto` |
| `caso_referencia_id` | INTEGER | ID del caso relacionado (sin FK) |
| `analista_id` | INTEGER | ID del analista (sin FK) |
| `estado` | VARCHAR(20) | `borrador`, `revisión`, `aprobado` |
| `created_at`, `updated_at` | DATETIME | Auditoría |

---

## 3. osint.db — Base de datos OSINT

### `fuentes_osint`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `nombre` | VARCHAR(100) | Nombre de la fuente |
| `tipo` | VARCHAR(50) | `api`, `scraper`, `search`, `plugin` |
| `url_base` | VARCHAR(500) | URL base del servicio |
| `requiere_key` | BOOLEAN | Si necesita API key |
| `activa` | BOOLEAN | Estado de la fuente |
| `rate_limit` | INTEGER | Solicitudes máximas por minuto |

### `consultas_osint`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `fuente_id` | INTEGER FK → `fuentes_osint.id` | Fuente usada |
| `tipo_consulta` | VARCHAR(50) | `username`, `email`, `phone`, `domain`, `ip` |
| `valor_consultado` | VARCHAR(500) | Valor buscado |
| `caso_referencia_id` | INTEGER | Caso asociado (sin FK) |
| `entity_type` | VARCHAR(50) | Tipo de entidad intel relacionada |
| `entity_id` | INTEGER | ID de la entidad intel |
| `estado` | VARCHAR(20) | `pendiente`, `completado`, `error` |
| `usuario_id` | INTEGER | ID del usuario que consultó |
| `created_at`, `updated_at` | DATETIME | Auditoría |

### `cache_consultas`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `consulta_id` | INTEGER FK → `consultas_osint.id` | Consulta cacheada |
| `hash_clave` | VARCHAR(64) | SHA-256 de los parámetros de búsqueda |
| `respuesta_raw` | TEXT | Respuesta cruda del servicio |
| `codigo_http` | INTEGER | Código de respuesta HTTP |
| `expira_en` | DATETIME | Expiración del caché |
| `hits` | INTEGER | Número de veces que se usó el caché |

### `resultados_osint`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `consulta_id` | INTEGER FK → `consultas_osint.id` | Consulta origen |
| `tipo_hallazgo` | VARCHAR(50) | `perfil`, `actividad`, `red`, `imagen`, etc. |
| `titulo` | VARCHAR(200) | Título del hallazgo |
| `descripcion` | TEXT | Descripción detallada |
| `datos_json` | TEXT | Datos estructurados (JSON) |
| `relevancia` | FLOAT | Score de relevancia (0.0–1.0) |
| `verificado` | BOOLEAN | Si el hallazgo fue verificado manualmente |

### `indicadores_riesgo`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `tipo` | VARCHAR(50) | `telefono`, `email`, `dominio`, `ip`, etc. |
| `valor` | VARCHAR(500) | Valor del indicador |
| `descripcion` | VARCHAR(500) | Contexto del indicador |
| `nivel_riesgo` | VARCHAR(20) | `bajo`, `medio`, `alto`, `crítico` |
| `fuente_origen` | VARCHAR(100) | Fuente que lo detectó |
| `caso_referencia_id` | INTEGER | Caso relacionado (sin FK) |
| `activo` | BOOLEAN | DEFAULT TRUE |
| `fecha_deteccion` | DATETIME | Cuándo se detectó |
| `fecha_expiracion` | DATETIME | Cuándo expira (opcional) |

### `node` — Nodos del grafo OSINT (compatible Cytoscape)

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `type` | VARCHAR(50) | `email`, `phone`, `domain`, `person`, `ip`, etc. |
| `value` | VARCHAR(500) | UNIQUE — valor único del nodo |
| `label` | VARCHAR(200) | Etiqueta mostrada en el grafo |
| `group` | VARCHAR(50) | Clase de color (`contact`, `network`, `org`, `target`) |
| `metadata_payload` | TEXT | Atributos adicionales (JSON) |
| `created_at`, `updated_at` | DATETIME | Auditoría |

### `edge` — Aristas del grafo OSINT

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador |
| `source_id` | INTEGER FK → `node.id` | Nodo origen |
| `target_id` | INTEGER FK → `node.id` | Nodo destino |
| `relation_type` | VARCHAR(100) | Tipo de relación entre nodos |
| `metadata_payload` | TEXT | Atributos adicionales (JSON) |

---

## Diagrama de relaciones simplificado

```
nexo147.db
──────────────────────────────────────────────────
usuarios ──created_by──► casos (referencia lógica)
unidades_gaula (1) ──► casos (N)
casos (1) ──► caso_reportante ──► reportantes
casos (1) ──► evidencias (N)
casos (1) ──► eventos_caso (N)
casos (1) ──► medios_pago (N)

         inter-base (nexo147 ↔ intel)
casos.id (int) ──► caso_persona.caso_id
casos.id (int) ──► caso_telefono.caso_id
casos.id (int) ──► caso_ubicacion.caso_id
casos.id (int) ──► caso_cuenta.caso_id

intel.db
──────────────────────────────────────────────────
personas ──► alias, telefonos, correos, direcciones
         ──► vehiculos, cuentas, redes, organizaciones
intel_nodes ──► intel_edges (source / target)

osint.db
──────────────────────────────────────────────────
fuentes_osint (1) ──► consultas_osint (N)
consultas_osint (1) ──► cache_consultas (1)
consultas_osint (1) ──► resultados_osint (N)
node ──► edge (source / target)
```

---

## Usuarios demo (seed automático)

| Username | Contraseña | Rol |
|---|---|---|
| `admin` | `Admin147*` | admin |
| `director` | `Director147*` | director |
| `analista` | `Analista147*` | analista |
| `operador` | `Operador147*` | operador |

Las contraseñas se almacenan como hash Werkzeug (pbkdf2:sha256) — nunca en texto plano.

---

## Configuración de conexión

```python
# modules/config.py
SQLALCHEMY_DATABASE_URI = "sqlite:///data/nexo147.db"
SQLALCHEMY_BINDS = {
    "intel": "sqlite:///data/intel.db",
    "osint": "sqlite:///data/osint.db",
}
SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {"check_same_thread": False},
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}
```

**Pragmas SQLite activados** (via evento `connect`):
- `PRAGMA journal_mode=WAL` — lecturas no bloquean escrituras
- `PRAGMA synchronous=NORMAL`
- `PRAGMA cache_size=10000`
- `PRAGMA foreign_keys=ON`

Los archivos `.db` están en `.gitignore` y no se versionan.
