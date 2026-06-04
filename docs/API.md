# Referencia de API — NEXO-147

Todas las respuestas JSON usan UTF-8. Las rutas protegidas requieren sesión activa (cookie de sesión Flask).

---

## Auth (`auth_bp`)

### `GET /login`

Renderiza el formulario de login.

**Respuesta:** HTML (`auth/login.html`)

---

### `POST /login`

Autentica al usuario.

**Body (form-data):**

| Campo | Tipo | Descripción |
|---|---|---|
| `username` | string | Nombre de usuario |
| `password` | string | Contraseña en texto plano |

**Respuestas:**

| Código | Descripción |
|---|---|
| `302` | Login exitoso → redirige a `/` |
| `200` | Credenciales incorrectas → renderiza login con error |

---

### `GET /logout`

Destruye la sesión activa.

**Protección:** `@login_required`  
**Respuesta:** `302` → `/login`

---

### `GET /`

Redirige al área correcta según el rol del usuario autenticado.

**Protección:** `@login_required`

| Rol | Redirección |
|---|---|
| `operador` | `/casos/console` |
| `admin`, `director`, `analista` | `/dashboard` |

---

## Casos (`casos_bp`)

### `POST /registrar-reporte`

Registra un nuevo caso en el sistema.

**Protección:** `@operador_required` (admin + operador)  
**Body (JSON o form-data):**

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `tipo_caso` | string | sí | `Extorsión`, `Secuestro`, `Amenaza`, etc. |
| `prioridad` | string | sí | `Baja`, `Media`, `Alta`, `Crítica` |
| `canal_recepcion` | string | sí | `Línea 147`, `Web`, `Presencial` |
| `unidad_gaula_id` | integer | no | ID de la unidad receptora |
| `descripcion` | string | no | Descripción del caso |
| `nombre_reportante` | string | no | Nombre del reportante |
| `documento_reportante` | string | no | Documento de identidad |
| `telefono_reportante` | string | no | Teléfono de contacto |
| `anonimo` | boolean | no | `true` si es denuncia anónima |
| `observaciones` | string | no | Notas adicionales |

**Respuesta exitosa (`201`):**
```json
{
    "ok": true,
    "id_caso": "a3f2b1c4-...",
    "message": "Caso registrado correctamente"
}
```

**Error (`400`):**
```json
{
    "ok": false,
    "error": "tipo_caso es requerido"
}
```

---

### `GET /api/casos`

Lista casos. Los resultados se filtran según el rol del usuario.

**Protección:** `@director_required` (admin + director)

**Query params:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `estado` | string | Filtrar por estado (`Recibido`, `En proceso`, `Cerrado`) |
| `prioridad` | string | Filtrar por prioridad |
| `tipo` | string | Filtrar por tipo de caso |
| `limit` | integer | Máximo de resultados (default: 50) |
| `offset` | integer | Paginación |

**Respuesta (`200`):**
```json
{
    "ok": true,
    "total": 42,
    "casos": [
        {
            "id": 1,
            "id_caso": "a3f2b1c4-...",
            "estado": "Recibido",
            "prioridad": "Alta",
            "tipo_caso": "Extorsión",
            "canal_recepcion": "Línea 147",
            "fecha_registro": "2026-06-03T10:30:00",
            "unidad_gaula": "GAULA Bogotá D.C."
        }
    ]
}
```

---

### `POST /api/casos/<id_caso>/estado`

Actualiza el estado de un caso.

**Protección:** `@analista_required` (admin + analista)

**Body (JSON):**
```json
{
    "estado": "En proceso",
    "observaciones": "Caso derivado a unidad especializada"
}
```

**Respuesta exitosa (`200`):**
```json
{
    "ok": true,
    "id_caso": "a3f2b1c4-...",
    "estado_anterior": "Recibido",
    "estado_nuevo": "En proceso"
}
```

**Error (`404`):**
```json
{
    "ok": false,
    "error": "Caso no encontrado"
}
```

---

## Dashboard (`dashboard_bp`)

### `GET /dashboard`

Renderiza el dashboard operacional.

**Protección:** `@director_required`  
**Respuesta:** HTML (`dashboard/dashboard.html`)

---

### `GET /health`

Verificación de estado del servicio.

**Protección:** ninguna (público)

**Respuesta (`200`):**
```json
{
    "status": "ok",
    "timestamp": "2026-06-03T10:30:00",
    "version": "1.0.0"
}
```

---

### `GET /api/brechas`

Alias de `/api/osint/brechas`. Consulta brechas de seguridad en HaveIBeenPwned.

**Protección:** `@login_required`

**Query params:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `email` | string | Email a consultar |

**Respuesta (`200`):**
```json
{
    "ok": true,
    "email": "ejemplo@dominio.com",
    "brechas": [
        {
            "nombre": "Adobe",
            "fecha": "2013-10-04",
            "datos_comprometidos": ["Email", "Password", "Username"]
        }
    ],
    "total_brechas": 1
}
```

---

### `GET /api/osint/indicadores`

Lista indicadores de riesgo activos.

**Protección:** `@login_required`

**Respuesta (`200`):**
```json
{
    "ok": true,
    "indicadores": [
        {
            "id": 1,
            "tipo": "telefono",
            "valor": "+573001234567",
            "nivel_riesgo": "alto",
            "fuente_origen": "HaveIBeenPwned",
            "fecha_deteccion": "2026-06-03T09:00:00"
        }
    ]
}
```

---

### `GET /api_externa`

Demo de integración con APIs externas.

**Protección:** ninguna  
**Respuesta:** JSON con datos de prueba

---

## Inteligencia (`intel_bp`)

### `GET /api/entidades`

Lista mock de entidades de inteligencia (personas, teléfonos, alias, ubicaciones).

**Protección:** `@login_required`

**Respuesta (`200`):**
```json
{
    "ok": true,
    "entidades": {
        "personas": [...],
        "telefonos": [...],
        "alias": [...],
        "ubicaciones": [...]
    }
}
```

---

### `GET /api/inteligencia/relaciones`

Grafo mock de relaciones entre entidades.

**Protección:** `@login_required`

**Respuesta (`200`):**
```json
{
    "ok": true,
    "nodes": [
        {"id": "1", "label": "Juan Pérez", "type": "persona"}
    ],
    "edges": [
        {"source": "1", "target": "2", "relation": "usa_telefono"}
    ]
}
```

---

### `GET /api/intel/entidades`

Entidades reales desde `intel.db`.

**Protección:** `@login_required`

**Query params:** `tipo` (persona, telefono, correo, vehiculo...), `limit`, `offset`

---

### `GET /api/intel/hallazgos`

Hallazgos de inteligencia registrados.

**Protección:** `@login_required`

**Respuesta (`200`):**
```json
{
    "ok": true,
    "hallazgos": [
        {
            "id": 1,
            "titulo": "Red de extorsión identificada",
            "nivel_clasificacion": "reservado",
            "estado": "aprobado",
            "created_at": "2026-06-03T08:00:00"
        }
    ]
}
```

---

### `GET /api/intel/grafo`

Grafo de inteligencia en formato Cytoscape.js.

**Protección:** `@login_required`

**Respuesta (`200`):**
```json
{
    "ok": true,
    "elements": {
        "nodes": [
            {
                "data": {
                    "id": "n1",
                    "label": "Juan Pérez",
                    "entity_type": "persona",
                    "nivel_riesgo": "alto"
                }
            }
        ],
        "edges": [
            {
                "data": {
                    "source": "n1",
                    "target": "n2",
                    "tipo_relacion": "usa_telefono"
                }
            }
        ]
    }
}
```

---

### `GET /api/etl/status`

Estado del pipeline ETL de inteligencia.

**Protección:** `@login_required`

**Respuesta (`200`):**
```json
{
    "ok": true,
    "etl": {
        "estado": "activo",
        "ultima_ejecucion": "2026-06-03T06:00:00",
        "registros_procesados": 1423,
        "errores": 0
    }
}
```

---

## OSINT — Redes Sociales (`/osint/social`)

### `GET /osint/social/github/<username>`

Perfil público de GitHub y repositorios.

**Protección:** `@login_required`

**Respuesta (`200`):**
```json
{
    "ok": true,
    "username": "ejemplo",
    "perfil": {
        "nombre": "Ejemplo User",
        "bio": "...",
        "seguidores": 42,
        "repositorios": [...]
    }
}
```

---

### `GET /osint/social/reddit/<username>`

Perfil y actividad de Reddit.

### `GET /osint/social/x/<username>`

Descubrimiento de cuenta X/Twitter.

### `GET /osint/social/tiktok/<username>`

Perfil de TikTok.

### `POST /osint/social/facebook`

Scraping de perfil Facebook (requiere Playwright instalado).

**Body (JSON):**
```json
{
    "url": "https://www.facebook.com/ejemplo",
    "username": "ejemplo"
}
```

---

## OSINT — Open Data (`/osint/opendata`)

### `GET /osint/opendata/ip/<ip_address>`

Geolocalización de IP.

**Respuesta (`200`):**
```json
{
    "ok": true,
    "ip": "8.8.8.8",
    "pais": "United States",
    "ciudad": "Mountain View",
    "lat": 37.386,
    "lon": -122.0838,
    "org": "AS15169 Google LLC"
}
```

---

### `GET /osint/opendata/domain/<domain>`

Lookup RDAP del dominio.

**Respuesta (`200`):**
```json
{
    "ok": true,
    "dominio": "ejemplo.com",
    "registrador": "NameCheap",
    "fecha_registro": "2020-01-15",
    "fecha_expiracion": "2027-01-15",
    "nameservers": ["ns1.ejemplo.com"]
}
```

---

### `GET /osint/opendata/certs/<domain>`

Certificados SSL en Certificate Transparency (crt.sh).

---

## OSINT — Analytics (`/osint/analytics`)

### `POST /osint/analytics/grafo`

Construye un grafo desde resultados OSINT.

**Body (JSON):**
```json
{
    "consulta_ids": [1, 2, 3],
    "incluir_relaciones": true
}
```

**Respuesta:** Grafo en formato Cytoscape.js.

---

## Códigos de error comunes

| Código | Significado |
|---|---|
| `400` | Parámetros inválidos o faltantes |
| `401` | No autenticado (sin sesión) |
| `403` | Sin permisos para esta acción (rol insuficiente) |
| `404` | Recurso no encontrado |
| `500` | Error interno del servidor |

Formato de error estándar:
```json
{
    "ok": false,
    "error": "Descripción del error"
}
```
