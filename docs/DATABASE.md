# Base de datos — NEXO-147

Motor: **SQLite** via **Flask-SQLAlchemy**  
Archivo: `data/nexo147.db`  
Creación: automática al arrancar la app por primera vez

---

## Tablas

### `usuarios`

Almacena las cuentas de acceso al sistema. Los usuarios iniciales se insertan automáticamente (seed) si la tabla está vacía.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | INTEGER | PK, autoincremento | Identificador interno |
| `username` | VARCHAR(50) | UNIQUE, NOT NULL | Nombre de usuario para login |
| `password_hash` | VARCHAR(256) | NOT NULL | Contraseña hasheada (werkzeug) |
| `nombre` | VARCHAR(100) | NOT NULL | Nombre visible en la interfaz |
| `rol` | VARCHAR(20) | NOT NULL | Rol asignado (ver tabla de roles) |
| `activo` | BOOLEAN | DEFAULT TRUE | Permite desactivar sin eliminar |

### `reportes`

Almacena cada denuncia o reporte recibido a través del sistema. Reemplaza el archivo `data/reportes_147.jsonl`.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador interno autoincremental |
| `id_reporte` | VARCHAR(36) | UUID visible al usuario (ej. `a3f2...`) |
| `fecha_registro` | DATETIME | Fecha y hora de registro (automática) |
| `estado` | VARCHAR(20) | Estado del caso: `Recibido`, `En proceso`, `Cerrado` |
| `usuario_registro` | VARCHAR(50) | Username de quien registró |
| `rol_usuario` | VARCHAR(20) | Rol del usuario al momento del registro |
| **Clasificación** | | |
| `tipo_reporte` | VARCHAR(50) | Ej: Extorsión, Secuestro, Amenaza |
| `prioridad` | VARCHAR(20) | Baja, Media, Alta, Crítica |
| `unidad_gaula` | VARCHAR(100) | Unidad GAULA receptora |
| `canal_recepcion` | VARCHAR(50) | Ej: Línea 147, Web, Presencial |
| **Reportante** | | |
| `nombre_reportante` | VARCHAR(100) | Nombre de quien reporta |
| `documento_reportante` | VARCHAR(30) | Documento de identidad |
| `telefono_reportante` | VARCHAR(20) | Teléfono de contacto |
| `ubicacion` | VARCHAR(200) | Ubicación del hecho o del reportante |
| **Caso** | | |
| `descripcion` | TEXT | Descripción detallada del caso |
| `numero_extorsivo` | VARCHAR(30) | Número desde donde se realiza la extorsión |
| `alias_sospechoso` | VARCHAR(100) | Alias o apodo del sospechoso |
| `medio_pago` | VARCHAR(50) | Medio de pago exigido |
| `valor_exigido` | VARCHAR(50) | Valor monetario exigido |
| `evidencia` | VARCHAR(200) | Referencia a evidencia adjunta |
| `observaciones` | TEXT | Notas adicionales del operador |

---

## Roles y permisos

| Rol | Login | Registrar reporte | Ver reportes | Dashboard | Gestión usuarios |
|---|:---:|:---:|:---:|:---:|:---:|
| `admin` | SI | SI | SI | SI | SI |
| `director` | SI | NO | SI (lectura) | SI | NO |
| `analista` | SI | NO | SI + actualizar estado | NO | NO |
| `operador` | SI | SI | NO | NO | NO |

---

## Usuarios de demo (seed)

Insertados automáticamente la primera vez que arranca la app.

| Username | Rol | Contraseña inicial |
|---|---|---|
| `admin` | admin | `Admin147*` |
| `director` | director | `Director147*` |
| `analista` | analista | `Analista147*` |
| `operador` | operador | `Operador147*` |

> Las contraseñas se almacenan como hash — nunca en texto plano.

---

## Diagrama de relaciones

```
usuarios
  id (PK)
  username
  password_hash
  nombre
  rol
  activo

reportes
  id (PK)
  id_reporte
  usuario_registro  ──► usuarios.username (referencia lógica, sin FK)
  ...campos del caso
```

No se usa Foreign Key explícita entre `reportes.usuario_registro` y `usuarios.username` para mantener el historial si un usuario es eliminado.

---

## Dependencias

```
flask-sqlalchemy
```

`werkzeug.security` (para hashing de contraseñas) ya viene incluido con Flask — no requiere instalación adicional.

---

## Ubicación del archivo

```
DEMO_GAULA/
├── data/
│   └── nexo147.db       ← base de datos SQLite
├── app.py
└── docs/
    └── DATABASE.md      ← este archivo
```

El archivo `nexo147.db` no se versiona en git (agregar a `.gitignore`).
