# Diseño: Tab "Datos Abiertos" — Módulo OSINT

**Fecha:** 2026-06-09
**Estado:** Aprobado
**Rama:** desarrollador1

---

## Resumen

Añadir un cuarto tab llamado **Datos Abiertos** en el módulo OSINT de la consola de casos. El tab ofrece una búsqueda universal: el usuario ingresa cualquier término (cédula, nombre, empresa, placa, teléfono) y el sistema detecta automáticamente qué fuentes consultar, ejecuta las búsquedas en paralelo y devuelve un resumen unificado más detalle expandible por fuente.

**Fuentes iniciales:** SIMIT (infracciones de tránsito vía datos.gov.co) y Truecaller (información telefónica).

---

## Arquitectura

### Archivos nuevos

| Archivo | Propósito |
|---|---|
| `modules/osint/connectors/simit.py` | SimitConnector — consulta datos.gov.co |
| `modules/osint/connectors/truecaller.py` | TruecallerConnector — consulta Truecaller API |
| `modules/osint/opendata/__init__.py` | Registro del blueprint `opendata_bp` |
| `modules/osint/opendata/routes.py` | Endpoint `GET /osint/opendata/lookup` |
| `templates/osint/opendata_fragment.html` | Fragmento HTML del tab |

### Archivos modificados

| Archivo | Cambio |
|---|---|
| `modules/__init__.py` | Registrar `opendata_bp` con prefijo `/osint/opendata` |
| `templates/casos/console.html` | Añadir 4° tab "Datos Abiertos" + panel de contenido |

---

## Flujo de Datos

```
Usuario escribe término
        │
        ▼
GET /osint/opendata/lookup?q=<término>&caso_id=<id>
        │
        ▼
routes.py detecta tipo de dato:
  - Solo dígitos 6-10 chars  → "document" / "plate" → SIMIT
  - Inicia +57 / 3XX 10 dig  → "phone"              → Truecaller
  - Texto mixto              → "unknown"             → ambas fuentes
        │
        ▼
OsintOrchestrator ejecuta conectores aplicables en paralelo
        │
        ▼
Renderiza opendata_fragment.html con:
  - Resumen unificado (N fuentes, M hallazgos)
  - Sección SIMIT expandible (tabla)
  - Sección Truecaller expandible (tarjeta)
```

---

## Conectores

### SimitConnector

- **Extiende:** `BaseConnector`
- **`target_types`:** `["document", "plate", "unknown"]`
- **API:** `https://www.datos.gov.co/resource/72nf-y4v3.json`
- **Estrategia de búsqueda:**
  - Tipo `document`: `$where=numero_documento='<q>'`
  - Tipo `plate`: `$where=placa='<q>'`
  - Tipo `unknown`: `$where=nombre like '%<q>%'`
- **Campos retornados:** nombre, numero_documento, placa, valor_multa, estado, fecha_infraccion, municipio
- **Sin autenticación requerida** (API pública)

### TruecallerConnector

- **Extiende:** `BaseConnector`
- **`target_types`:** `["phone"]`
- **API key:** `TRUECALLER_API_KEY` (variable de entorno)
- **Comportamiento si no está configurada:** retorna `ConnectorResult` con `status="unconfigured"`, no lanza excepción
- **Campos retornados:** nombre_registrado, operador, pais, spam_score, tipo_linea

---

## UI

### Tab en console.html

Se añade un cuarto botón en la barra de tabs OSINT:
```
[ Redes Sociales ]  [ Historial ]  [ Grafo de Relaciones ]  [ Datos Abiertos ]
```

### opendata_fragment.html

```
┌─────────────────────────────────────────┐
│  RESUMEN UNIFICADO                       │
│  ● N fuentes consultadas                 │
│  ● M hallazgos encontrados               │
│  [SIMIT ✓]  [Truecaller ✓/sin config]   │
└─────────────────────────────────────────┘

▼ SIMIT — Infracciones de Tránsito
  Tabla: Nombre | Placa | Valor | Estado | Fecha | Municipio

▼ TRUECALLER — Información Telefónica
  Tarjeta: Nombre registrado, Operador, Spam score, Tipo de línea
```

**Reglas UI:**
- Cada sección es expandible/colapsable
- Si no hay resultados en una fuente: "Sin resultados en [FUENTE]" en lugar de sección vacía
- Si Truecaller no está configurado: banner "Configura `TRUECALLER_API_KEY` en el entorno"
- Spinner mientras carga (mismo patrón que tab Social)
- Estilo consistente con el tema institucional/gubernamental del proyecto

---

## Variables de Entorno Requeridas

| Variable | Requerida | Descripción |
|---|---|---|
| `TRUECALLER_API_KEY` | Opcional | Sin ella, Truecaller muestra aviso en UI |
| `API_IDENTIDAD_AUTORIZADA` | Futuro | Reservada para fase 2 |

---

## Fuera de Alcance (esta versión)

- Conectores adicionales (Procuraduría, SECOP, Contraloría, RUNT, RNMC)
- Persistencia de resultados en base de datos
- Correlación con el grafo de relaciones
- Paginación de resultados SIMIT
