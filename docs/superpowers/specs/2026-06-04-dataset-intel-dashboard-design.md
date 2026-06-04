# Dataset Demo + Dashboard Intel — Spec de Diseño
**Fecha:** 2026-06-04  
**Rama:** feat/osint-graph-sigma  
**Enfoque aprobado:** A — Backend Flask renderiza el dashboard

---

## Resumen

Integrar el dataset CSV de demostración (500 casos + alertas OSINT) en dos módulos de `console.html`:

1. **Bandeja de Casos** (`panel-casos`): reemplazar la fuente de datos SQLite por los datos del CSV demo.
2. **Hallazgos Intel** (`panel-hallazgos`): reemplazar el contenido actual por el dashboard Plotly/Pandas del script proporcionado.
3. **Eliminar** el módulo "Grafo de Relaciones" (`panel-grafo`) del HTML y del sidebar.

---

## Archivos de Dataset

Ruta base: `data/Data_Set/nexo147_dataset_relacional_csv/`

| Archivo | Uso |
|---|---|
| `nexo147_casos_demo_500.csv` | Tabla Bandeja de Casos + KPIs del dashboard |
| `nexo147_alertas_osint_demo.csv` | KPI alertas OSINT + gráfico G6 del dashboard |

Columnas clave de `nexo147_casos_demo_500.csv`:
`id_reporte`, `fecha_registro`, `tipo_reporte`, `prioridad`, `canal`, `unidad_gaula_receptora`, `estado_caso`, `departamento`, `municipio`, `monto_exigido_perdida_estimada`, `score_riesgo`, `modalidad`, `posible_grupo`, `descripcion_hechos`, `numero_telefonico_asociado`, `alias_sospechoso`

---

## Backend — Nuevas rutas Flask

### Nuevo Blueprint: `dataset_bp`

Archivo: `modules/dataset/__init__.py` + `modules/dataset/routes.py`  
Prefijo URL: `/api/dataset`  
Registro en: `app.py`

#### `GET /api/dataset/casos`

- Lee `nexo147_casos_demo_500.csv` con pandas en cada request (datos de demo, volumen manejable).
- Retorna JSON array con los campos mapeados a la tabla actual:

```json
[
  {
    "id_reporte": "NEXO-147-00001",
    "fecha_registro": "2026-04-08 10:26",
    "tipo_reporte": "Extorsión",
    "prioridad": "Media",
    "unidad_gaula": "GAULA Cundinamarca",
    "estado": "En verificación",
    "departamento": "Antioquia",
    "municipio": "Bello",
    "monto_exigido": 1795833,
    "score_riesgo": 57,
    "modalidad": "Extorsión digital",
    "posible_grupo": "Actor desconocido",
    "descripcion_hechos": "...",
    "numero_telefonico": "3508589530",
    "alias_sospechoso": "Alias-344"
  }
]
```

#### `GET /api/intel/dashboard`

- Lee ambos CSVs con pandas.
- Ejecuta el procesamiento del script proporcionado (tendencias, KPIs, agrupaciones).
- Retorna JSON:

```json
{
  "kpis": {
    "total_casos": 500,
    "total_monto": 10407000000,
    "avg_riesgo": 65.3,
    "total_alertas": 120
  },
  "charts": {
    "line_casos": "<div>...</div>",
    "bar_monto": "<div>...</div>",
    "bar_dept": "<div>...</div>",
    "donut_tipo": "<div>...</div>",
    "bar_canal_prioridad": "<div>...</div>",
    "osint_indicador": "<div>...</div>"
  }
}
```

Los `<div>` se generan con `plotly.offline.plot(fig, include_plotlyjs=False, output_type='div')`.

---

## Frontend — `console.html`

### 1. `<head>` — Cambios de scripts

**Eliminar:**
```html
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<script src="{{ url_for('static', filename='js/osint-graph.bundle.js') }}" defer></script>
```

**Agregar:**
```html
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
```

### 2. Sidebar — Eliminar ítem "Grafo de Relaciones"

Eliminar las líneas (aprox. 85–88):
```html
<a href="#grafo" class="nav-item" data-panel="panel-grafo">
  ...
  <span>Grafo de Relaciones</span>
</a>
```

### 3. `panel-casos` — Cambiar fuente de datos

- El JS que actualmente llama `fetch('/api/casos')` pasa a llamar `fetch('/api/dataset/casos')`.
- Las columnas de la tabla se mantienen iguales en estructura.
- El panel de detalle lateral muestra los campos adicionales: departamento, municipio, modalidad, score_riesgo, alias_sospechoso, numero_telefonico.
- Los filtros de prioridad y estado siguen funcionando (filtrado client-side sobre los datos CSV).

### 4. `panel-hallazgos` — Reemplazar contenido por dashboard

El contenido actual (tabla HallazgoIntel + indicadores OSINT) se elimina completamente.

Nuevo contenido:

```html
<section class="panel-section" id="panel-hallazgos">
  <div class="section-header-tactical">
    <h2>Hallazgos Intel — Dashboard de Tendencias NEXO-147</h2>
    <p>Análisis de tendencias operativas y correlación OSINT sobre el dataset de demostración.</p>
  </div>

  <!-- KPIs -->
  <div class="kpi-grid" id="intel-kpis">
    <div class="kpi-card">...</div>  <!-- 4 KPIs dinámicos -->
  </div>

  <!-- Insights estratégicos -->
  <div class="insight-box" id="intel-insights">...</div>

  <!-- 6 gráficos Plotly en layout 2 columnas -->
  <div id="intel-charts-container">
    <!-- Se inyecta via JS desde /api/intel/dashboard -->
  </div>

  <div id="intel-dashboard-loading" class="helper-text-mono text-center">
    Cargando dashboard de inteligencia...
  </div>
</section>
```

La carga ocurre cuando el usuario navega al panel (`data-panel="panel-hallazgos"`), usando el mismo sistema de navegación de paneles existente.

### 5. `panel-grafo` — Eliminar sección completa

Eliminar las líneas 873–921 del HTML (toda la sección `<section class="panel-section" id="panel-grafo">`).

---

## Dependencias Python

Agregar a `requirements.txt`:
```
pandas
plotly
```

Verificar que estén instaladas en el venv del proyecto.

---

## Mapeo de columnas CSV → tabla Bandeja de Casos

| Columna HTML actual | Campo CSV |
|---|---|
| Código / Fecha | `id_reporte` / `fecha_registro` |
| Delito | `tipo_reporte` |
| Prioridad | `prioridad` |
| GAULA | `unidad_gaula_receptora` |
| Estado | `estado_caso` |
| Acción | botón detalle (sin cambio) |

**Detalle lateral adicional (campos nuevos):**
- Departamento / Municipio
- Monto exigido
- Score de riesgo
- Modalidad / Grupo presunto
- Alias sospechoso / Teléfono asociado

---

## Flujo de datos

```
[CSV en disco]
    │
    ▼
[Flask /api/dataset/casos]  →  JSON array  →  JS fetch()  →  tabla panel-casos
[Flask /api/intel/dashboard] →  JSON {kpis, charts} →  JS fetch()  →  panel-hallazgos
```

---

## Restricciones y aclaraciones

- El endpoint `/api/casos` (base de datos SQLite) no se elimina; solo deja de usarse desde el panel-casos del frontend.
- El dataset CSV es de solo lectura; no hay escritura sobre él desde la app.
- El dashboard no tiene estado persistente entre sesiones; se regenera en cada carga del panel.
- La autenticación (`@login_required`) aplica a ambas rutas nuevas.
