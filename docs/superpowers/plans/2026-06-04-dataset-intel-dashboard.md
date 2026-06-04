# Dataset Demo + Dashboard Intel — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrar el dataset CSV demo en la Bandeja de Casos, reemplazar el panel Hallazgos Intel con un dashboard Plotly/Pandas, y eliminar el módulo Grafo de Relaciones.

**Architecture:** Nuevo blueprint Flask `dataset_bp` expone dos endpoints (`/api/dataset/casos` y `/api/intel/dashboard`) que leen los CSV con pandas y retornan JSON. El frontend consume estos endpoints: `console.js` dirige `fetchCasos` al nuevo endpoint, y una nueva función `fetchIntelDashboard` inyecta los charts Plotly en `panel-hallazgos`.

**Tech Stack:** Python 3, Flask, pandas, plotly, Jinja2, JavaScript (vanilla), Plotly.js CDN

---

## Mapa de archivos

| Acción | Archivo | Responsabilidad |
|---|---|---|
| Modificar | `requirements.txt` | Agregar pandas y plotly |
| Crear | `modules/dataset/__init__.py` | Definir `dataset_bp` |
| Crear | `modules/dataset/routes.py` | Endpoints `/api/dataset/casos` y `/api/intel/dashboard` |
| Modificar | `modules/__init__.py` | Registrar `dataset_bp` |
| Modificar | `templates/casos/console.html` | Quitar grafo, scripts, actualizar hallazgos |
| Modificar | `static/console.js` | Redirigir fetchCasos, agregar fetchIntelDashboard |

---

## Task 1: Agregar dependencias pandas y plotly

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Agregar pandas y plotly a requirements.txt**

Abrir `requirements.txt` y agregar al final:

```
pandas>=2.0.0
plotly>=5.18.0
```

- [ ] **Step 2: Instalar dependencias en el venv**

```bash
# En Windows PowerShell, desde la raíz del proyecto
.venv\Scripts\python.exe -m pip install pandas plotly
```

Salida esperada: líneas `Successfully installed pandas-X.X plotly-X.X` (o `Requirement already satisfied` si ya están).

- [ ] **Step 3: Verificar importación**

```bash
.venv\Scripts\python.exe -c "import pandas; import plotly; print('OK')"
```

Salida esperada: `OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add pandas and plotly dependencies"
```

---

## Task 2: Crear blueprint `dataset_bp` con endpoint `/api/dataset/casos`

**Files:**
- Create: `modules/dataset/__init__.py`
- Create: `modules/dataset/routes.py`

- [ ] **Step 1: Crear `modules/dataset/__init__.py`**

```python
from flask import Blueprint

dataset_bp = Blueprint("dataset", __name__)

from modules.dataset import routes  # noqa: F401, E402
```

- [ ] **Step 2: Crear `modules/dataset/routes.py` con el endpoint de casos**

```python
import os
import pandas as pd
from flask import jsonify
from modules.dataset import dataset_bp
from modules.auth.decorators import login_required

_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "Data_Set", "nexo147_dataset_relacional_csv")
)
_CSV_CASOS   = os.path.join(_DATA_DIR, "nexo147_casos_demo_500.csv")
_CSV_ALERTAS = os.path.join(_DATA_DIR, "nexo147_alertas_osint_demo.csv")


@dataset_bp.route("/api/dataset/casos")
@login_required
def api_dataset_casos():
    df = pd.read_csv(_CSV_CASOS, dtype=str).fillna("")
    resultados = []
    for _, row in df.iterrows():
        resultados.append({
            "id_reporte":        row["id_reporte"],
            "fecha_registro":    row["fecha_registro"],
            "tipo_reporte":      row["tipo_reporte"],
            "prioridad":         row["prioridad"],
            "unidad_gaula":      row["unidad_gaula_receptora"],
            "estado":            row["estado_caso"],
            "nombre_reportante": row["nombre_reportante"],
            "alias_sospechoso":  row["alias_sospechoso"],
            "numero_extorsivo":  row["numero_telefonico_asociado"],
            "valor_exigido":     row["monto_exigido_perdida_estimada"],
            "medio_pago":        row["medio_cuenta_pago"],
            "descripcion":       row["descripcion_hechos"],
            "departamento":      row["departamento"],
            "municipio":         row["municipio"],
            "score_riesgo":      row["score_riesgo"],
            "modalidad":         row["modalidad"],
            "posible_grupo":     row["posible_grupo"],
        })
    return jsonify(resultados)
```

- [ ] **Step 3: Verificar que la ruta devuelve JSON**

Levantar la app y hacer un GET manual:

```bash
.venv\Scripts\python.exe -c "
import os, sys
sys.path.insert(0, '.')
os.environ['FLASK_ENV'] = 'development'
from app import app
with app.test_client() as c:
    with app.test_request_context():
        from flask import session
        with c.session_transaction() as s:
            s['user'] = 'admin'
            s['role'] = 'admin'
    r = c.get('/api/dataset/casos')
    import json
    data = json.loads(r.data)
    print('Status:', r.status_code)
    print('Total registros:', len(data))
    print('Primer registro keys:', list(data[0].keys()))
"
```

Salida esperada:
```
Status: 200
Total registros: 500
Primer registro keys: ['id_reporte', 'fecha_registro', 'tipo_reporte', 'prioridad', 'unidad_gaula', 'estado', ...]
```

- [ ] **Step 4: Commit**

```bash
git add modules/dataset/__init__.py modules/dataset/routes.py
git commit -m "feat(dataset): add blueprint with /api/dataset/casos endpoint"
```

---

## Task 3: Agregar endpoint `/api/intel/dashboard` al blueprint

**Files:**
- Modify: `modules/dataset/routes.py`

- [ ] **Step 1: Agregar el endpoint al final de `modules/dataset/routes.py`**

Agregar estas importaciones al bloque de imports existente al inicio del archivo (reemplazar el bloque completo de imports):

```python
import os
import pandas as pd
import plotly.express as px
import plotly.offline as po
from flask import jsonify
from modules.dataset import dataset_bp
from modules.auth.decorators import login_required
```

Luego agregar esta función al final del archivo (después de `api_dataset_casos`):

```python
@dataset_bp.route("/api/intel/dashboard")
@login_required
def api_intel_dashboard():
    dark = "plotly_dark"

    casos_df  = pd.read_csv(_CSV_CASOS,   dtype=str).fillna("")
    alertas_df = pd.read_csv(_CSV_ALERTAS, dtype=str).fillna("")

    # Conversiones numéricas necesarias para los cálculos
    casos_df["monto_exigido_perdida_estimada"] = pd.to_numeric(
        casos_df["monto_exigido_perdida_estimada"], errors="coerce"
    ).fillna(0)
    casos_df["score_riesgo"] = pd.to_numeric(
        casos_df["score_riesgo"], errors="coerce"
    ).fillna(0)

    casos_df["fecha_registro"] = pd.to_datetime(casos_df["fecha_registro"], errors="coerce")
    casos_df["mes_anio"] = casos_df["fecha_registro"].dt.strftime("%Y-%m")
    casos_df = casos_df.sort_values("mes_anio")

    # KPIs
    total_casos   = int(len(casos_df))
    total_monto   = int(casos_df["monto_exigido_perdida_estimada"].sum())
    avg_riesgo    = float(casos_df["score_riesgo"].mean())
    total_alertas = int(len(alertas_df))

    # G1: Tendencia mensual
    monthly_types = casos_df.groupby(["mes_anio", "tipo_reporte"], as_index=False).size()
    monthly_types.columns = ["mes_anio", "tipo_reporte", "cantidad"]
    fig_line = px.line(monthly_types, x="mes_anio", y="cantidad", color="tipo_reporte",
                       title="Tendencia Mensual de Casos por Tipo de Reporte",
                       labels={"mes_anio": "Mes/Año", "cantidad": "Número de Casos", "tipo_reporte": "Tipo"},
                       markers=True, template=dark)

    # G2: Impacto económico mensual
    monthly_monto = casos_df.groupby("mes_anio", as_index=False)["monto_exigido_perdida_estimada"].sum()
    fig_bar_monto = px.bar(monthly_monto, x="mes_anio", y="monto_exigido_perdida_estimada",
                           title="Impacto Económico Mensual Consolidado ($ COP)",
                           labels={"mes_anio": "Mes/Año", "monto_exigido_perdida_estimada": "Monto ($)"},
                           template=dark, color_discrete_sequence=["#38bdf8"])

    # G3: Casos por departamento
    dept_counts = casos_df["departamento"].value_counts().reset_index()
    dept_counts.columns = ["departamento", "cantidad"]
    fig_bar_dept = px.bar(dept_counts, x="cantidad", y="departamento", orientation="h",
                          title="Volumen de Casos Totales por Departamento",
                          labels={"cantidad": "Número de Casos", "departamento": "Departamento"},
                          template=dark, color="cantidad", color_continuous_scale="Blues")

    # G4: Participación por tipo (donut)
    fig_donut = px.pie(casos_df, names="tipo_reporte", hole=0.4,
                       title="Participación Absoluta por Delito",
                       template=dark, color_discrete_sequence=px.colors.qualitative.Pastel)

    # G5: Canal vs Prioridad
    fig_canal = px.bar(casos_df, x="canal", color="prioridad",
                       title="Casos por Canal de Recepción y Nivel de Prioridad",
                       labels={"canal": "Canal de Recepción", "count": "Casos", "prioridad": "Prioridad"},
                       template=dark, barmode="stack",
                       color_discrete_map={"Crítica": "#ef4444", "Alta": "#f97316",
                                           "Media": "#eab308", "Baja": "#22c55e"})

    # G6: Indicadores OSINT
    ind_counts = alertas_df["indicador"].value_counts().reset_index()
    ind_counts.columns = ["indicador", "cantidad"]
    fig_osint = px.bar(ind_counts, x="indicador", y="cantidad",
                       title="Principales Indicadores de Riesgo OSINT Detectados",
                       labels={"indicador": "Indicador Técnico", "cantidad": "Número de Alertas"},
                       template=dark, color="cantidad", color_continuous_scale="Reds")

    return jsonify({
        "kpis": {
            "total_casos":   total_casos,
            "total_monto":   total_monto,
            "avg_riesgo":    round(avg_riesgo, 1),
            "total_alertas": total_alertas,
        },
        "charts": {
            "line_casos":          po.plot(fig_line,      include_plotlyjs=False, output_type="div"),
            "bar_monto":           po.plot(fig_bar_monto, include_plotlyjs=False, output_type="div"),
            "bar_dept":            po.plot(fig_bar_dept,  include_plotlyjs=False, output_type="div"),
            "donut_tipo":          po.plot(fig_donut,     include_plotlyjs=False, output_type="div"),
            "bar_canal_prioridad": po.plot(fig_canal,     include_plotlyjs=False, output_type="div"),
            "osint_indicador":     po.plot(fig_osint,     include_plotlyjs=False, output_type="div"),
        }
    })
```

- [ ] **Step 2: Verificar que el endpoint responde**

```bash
.venv\Scripts\python.exe -c "
import os, sys, json
sys.path.insert(0, '.')
from app import app
with app.test_client() as c:
    with c.session_transaction() as s:
        s['user'] = 'admin'
        s['role'] = 'admin'
    r = c.get('/api/intel/dashboard')
    data = json.loads(r.data)
    print('Status:', r.status_code)
    print('KPIs:', data['kpis'])
    print('Charts keys:', list(data['charts'].keys()))
"
```

Salida esperada:
```
Status: 200
KPIs: {'total_casos': 500, 'total_monto': ..., 'avg_riesgo': ..., 'total_alertas': ...}
Charts keys: ['line_casos', 'bar_monto', 'bar_dept', 'donut_tipo', 'bar_canal_prioridad', 'osint_indicador']
```

- [ ] **Step 3: Commit**

```bash
git add modules/dataset/routes.py
git commit -m "feat(dataset): add /api/intel/dashboard endpoint with plotly charts"
```

---

## Task 4: Registrar `dataset_bp` en la app Flask

**Files:**
- Modify: `modules/__init__.py:34-49`

- [ ] **Step 1: Agregar importación y registro del blueprint**

En `modules/__init__.py`, dentro de `_register_blueprints`, agregar al final de los imports y registros existentes:

```python
def _register_blueprints(app):
    from modules.auth        import auth_bp
    from modules.casos       import casos_bp
    from modules.inteligencia import intel_bp
    from modules.dashboard   import dashboard_bp
    from modules.dataset     import dataset_bp          # <-- nueva línea
    from modules.osint.social    import social_osint_bp
    from modules.osint.opendata  import opendata_osint_bp
    from modules.osint.analytics import analytics_osint_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(casos_bp)
    app.register_blueprint(intel_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(dataset_bp)                  # <-- nueva línea
    app.register_blueprint(social_osint_bp,    url_prefix="/osint/social")
    app.register_blueprint(opendata_osint_bp,  url_prefix="/osint/opendata")
    app.register_blueprint(analytics_osint_bp, url_prefix="/osint/analytics")
```

- [ ] **Step 2: Verificar que la app arranca sin errores**

```bash
.venv\Scripts\python.exe -c "from app import app; print('App OK, blueprints:', [bp for bp in app.blueprints])"
```

Salida esperada: lista de blueprints que incluye `'dataset'`.

- [ ] **Step 3: Commit**

```bash
git add modules/__init__.py
git commit -m "feat(dataset): register dataset_bp in Flask app"
```

---

## Task 5: Actualizar `console.html` — quitar grafo, scripts, actualizar panel hallazgos

**Files:**
- Modify: `templates/casos/console.html`

### Paso 5a: Scripts en `<head>`

- [ ] **Step 1: Eliminar scripts de vis-network y osint-graph, agregar Plotly.js**

Localizar en el `<head>` (líneas 21-22):
```html
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <script src="{{ url_for('static', filename='js/osint-graph.bundle.js') }}" defer></script>
```

Reemplazar con:
```html
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
```

### Paso 5b: Nav item "Grafo de Relaciones"

- [ ] **Step 2: Eliminar ítem de navegación del sidebar**

Localizar (líneas 85-88):
```html
        <a href="#grafo" class="nav-item" data-panel="panel-grafo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><line x1="6.48" y1="10.74" x2="17.52" y2="6.26"/><line x1="6.48" y1="13.26" x2="17.52" y2="17.74"/></svg>
          <span>Grafo de Relaciones</span>
        </a>
```

Eliminar esas 4 líneas completas.

### Paso 5c: Panel `panel-hallazgos`

- [ ] **Step 3: Reemplazar contenido del panel hallazgos**

Localizar (líneas 835-870):
```html
        <section class="panel-section" id="panel-hallazgos">
          <div class="section-header-tactical">
            <h2>Hallazgos de Inteligencia y Riesgo OSINT</h2>
            <p>Findings catalogados del análisis cruzado entre intel.db, osint.db y nexo147. Datos clasificados según nivel de acceso del operador.</p>
          </div>
          <div class="dashboard-grid">
            <div class="dashboard-card double-bezel col-span-8">
              <div class="inner-core">
                <h2>Hallazgos Registrados: HallazgoIntel</h2>
                <div class="table-wrap">
                  <table id="table-hallazgos">
                    <thead>
                      <tr>
                        <th>Título / Descripción</th>
                        <th>Clasificación</th>
                        <th>Estado</th>
                        <th>Fecha</th>
                      </tr>
                    </thead>
                    <tbody id="hallazgos-body">
                      <tr><td colspan="4" class="text-center helper-text-mono">Cargando hallazgos...</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            <div class="dashboard-card double-bezel col-span-4">
              <div class="inner-core">
                <h3>Indicadores OSINT Activos</h3>
                <div id="indicadores-osint-list" class="indicadores-list">
                  <div class="helper-text-mono text-center">Cargando indicadores...</div>
                </div>
              </div>
            </div>
          </div>
        </section>
```

Reemplazar con:
```html
        <section class="panel-section" id="panel-hallazgos">
          <div class="section-header-tactical">
            <h2>Dashboard de Tendencias NEXO-147</h2>
            <p>Análisis de tendencias operativas y correlación OSINT sobre el dataset de demostración (500 casos + alertas).</p>
          </div>

          <!-- KPIs dinámicos -->
          <div class="kpi-grid" id="intel-kpis" style="display:grid; grid-template-columns: repeat(4,1fr); gap:16px; margin-bottom:24px;">
            <!-- Inyectado por fetchIntelDashboard() -->
          </div>

          <!-- Insights estratégicos -->
          <div class="dashboard-card double-bezel" style="margin-bottom:24px;">
            <div class="inner-core">
              <div style="border-left: 4px solid #38bdf8; padding-left:16px;">
                <p style="margin-bottom:8px;"><strong>1. Anomalía y Pico Temporal (Q1-2026):</strong> Los datos muestran una estabilidad en 2025 que rompe abruptamente en marzo y abril de 2026, donde el volumen de casos se dispara superando los 80 incidentes por mes, concentrado bajo la modalidad de <strong>Extorsión</strong>.</p>
                <p style="margin-bottom:8px;"><strong>2. Foco Demográfico y Económico:</strong> Bogotá D.C., Antioquia y Valle del Cauca centralizan el grueso operativo, representando pérdidas y exigencias acumuladas por más de <strong>$10,407 millones de pesos</strong>.</p>
                <p style="margin-bottom:0;"><strong>3. Hallazgo Técnico OSINT:</strong> Las alertas tempranas correlacionadas revelan que los incidentes nocturnos y la reincidencia en números telefónicos específicos estructuran la principal firma de los ataques.</p>
              </div>
            </div>
          </div>

          <!-- Contenedor de gráficos Plotly (inyectado por JS) -->
          <div id="intel-charts-container"></div>

          <div id="intel-dashboard-loading" class="helper-text-mono text-center" style="padding:40px 0;">
            Cargando dashboard de inteligencia...
          </div>
        </section>
```

### Paso 5d: Eliminar `panel-grafo`

- [ ] **Step 4: Eliminar la sección completa panel-grafo**

Localizar y eliminar desde la línea:
```html


        <!-- PANEL GRAFO DE RELACIONES (DATA WAREHOUSE INTEL) -->
        <section class="panel-section" id="panel-grafo">
```
hasta el cierre `</section>` correspondiente (aproximadamente líneas 872-921, incluyendo el comentario y la sección completa).

El bloque completo a eliminar es:
```html


        <!-- PANEL GRAFO DE RELACIONES (DATA WAREHOUSE INTEL) -->
        <section class="panel-section" id="panel-grafo">
          <div class="section-header-tactical">
            <h2>Grafo de Relaciones: Data Warehouse Intel</h2>
            <p>Nodos (IntelNode) y aristas (IntelEdge) del motor de correlación cruzada. Vínculos detectados por el Motor ETL entre entidades de intel.db.</p>
          </div>
          <div class="dashboard-grid">
            <div class="dashboard-card double-bezel col-span-12">
              <div class="inner-core">
                <div class="graph-toolbar" style="margin-bottom: 15px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                  <span class="helper-text-mono" style="margin: 0;">Filtro de Riesgo:</span>
                  <select id="graph-filter-risk" class="select-tactical" style="padding: 6px 12px; border-radius: 6px; font-size: 12px;">
                    <option value="todos">Todos los Nodos</option>
                    <option value="critico-alto">Crítico & Alto</option>
                    <option value="critico">Solo Crítico</option>
                  </select>
                  
                  <span class="helper-text-mono" style="margin: 0; margin-left: 10px;">Agrupar:</span>
                  <button id="btn-cluster-type" class="btn btn-secondary-tactical" style="padding: 6px 12px; font-size: 12px; border-radius: 6px;">Agrupar por Tipo</button>
                  <button id="btn-uncluster" class="btn btn-secondary-tactical" style="padding: 6px 12px; font-size: 12px; border-radius: 6px; display: none;">Desagrupar</button>
                </div>
                
                <div class="graph-layout-container" style="display: flex; gap: 20px; height: 500px;">
                  <!-- Contenedor del Grafo -->
                  <div id="grafo-canvas" style="flex: 1; height: 100%; background-color: rgba(4, 13, 25, 0.4); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08); position: relative; padding: 12px;">
                    <div id="grafo-loading" style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: rgba(7, 8, 12, 0.8); z-index: 10; font-family: var(--font-mono); color: var(--accent-cyan);">Cargando Grafo Interactivo...</div>
                  </div>
                  
                  <!-- Panel Lateral de Detalles -->
                  <div id="grafo-detail-sidebar" class="double-bezel" style="width: 320px; height: 100%; display: flex; flex-direction: column;">
                    <div class="inner-core" style="padding: 16px; display: flex; flex-direction: column; height: 100%; overflow-y: auto;">
                       <h2 style="font-size: 18px; margin-bottom: 12px; border-left: 2px solid var(--accent-cyan); padding-left: 8px;">Detalle de Selección</h2>
                      <div id="grafo-detail-content" style="flex: 1; display: flex; flex-direction: column; justify-content: center; text-align: center; color: var(--text-muted); font-size: 12px;">
                        Seleccione un nodo o un grupo (cluster) para ver su ficha técnica detallada.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="dashboard-card double-bezel col-span-12">
              <div class="inner-core">
                <h2>Estadísticas del Grafo de Relaciones</h2>
                <div id="grafo-stats-container" class="kpi-grid" style="margin-top: 0;"></div>
              </div>
            </div>
          </div>
        </section>
```

- [ ] **Step 5: Commit**

```bash
git add templates/casos/console.html
git commit -m "feat(console): remove grafo panel, add plotly dashboard container in hallazgos"
```

---

## Task 6: Actualizar `console.js` — redirigir fetchCasos y agregar fetchIntelDashboard

**Files:**
- Modify: `static/console.js`

### Paso 6a: Redirigir `fetchCasos` al nuevo endpoint

- [ ] **Step 1: Cambiar la URL en `fetchCasos` (línea ~321)**

Localizar:
```javascript
      const response = await fetch("/api/casos");
```

Reemplazar con:
```javascript
      const response = await fetch("/api/dataset/casos");
```

### Paso 6b: Redirigir `fetchDashboardData` al nuevo endpoint

- [ ] **Step 2: Cambiar la URL en `fetchDashboardData` (línea ~643)**

Localizar:
```javascript
        const response = await fetch("/api/casos");
```
(la segunda ocurrencia, dentro de `fetchDashboardData`)

Reemplazar con:
```javascript
        const response = await fetch("/api/dataset/casos");
```

### Paso 6c: Deshabilitar "Actualizar Estado" en datos demo

- [ ] **Step 3: Deshabilitar el botón de cambio de estado**

En `window.verDetalleCaso` (línea ~370), al final de la función, antes del cierre `};`, agregar:

```javascript
    // Dataset de demostración — cambio de estado no disponible
    if (btnSaveCaseStatus) {
      btnSaveCaseStatus.disabled = true;
      btnSaveCaseStatus.textContent = "Solo lectura (dataset demo)";
    }
```

### Paso 6d: Agregar `fetchIntelDashboard`

- [ ] **Step 4: Agregar la función `fetchIntelDashboard` después de `fetchDashboardData`**

Después del cierre de `fetchDashboardData` (aprox. línea 652), insertar:

```javascript
  let intelDashboardLoaded = false;

  async function fetchIntelDashboard() {
    if (intelDashboardLoaded) return;

    const loading  = document.getElementById("intel-dashboard-loading");
    const kpisEl   = document.getElementById("intel-kpis");
    const chartsEl = document.getElementById("intel-charts-container");
    if (!chartsEl) return;

    try {
      const response = await fetch("/api/intel/dashboard");
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();

      const { kpis, charts } = data;

      // Renderizar KPIs
      kpisEl.innerHTML = `
        <div class="dashboard-card double-bezel">
          <div class="inner-core" style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;color:#94a3b8;">Total Casos</div>
              <div style="font-size:1.6rem;font-weight:700;color:#38bdf8;">${kpis.total_casos.toLocaleString()}</div>
            </div>
            <span style="font-size:2rem;color:#475569;">📁</span>
          </div>
        </div>
        <div class="dashboard-card double-bezel">
          <div class="inner-core" style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;color:#94a3b8;">Impacto Económico</div>
              <div style="font-size:1.6rem;font-weight:700;color:#38bdf8;">$${kpis.total_monto.toLocaleString()} COP</div>
            </div>
            <span style="font-size:2rem;color:#475569;">💰</span>
          </div>
        </div>
        <div class="dashboard-card double-bezel">
          <div class="inner-core" style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;color:#94a3b8;">Score Riesgo Prom.</div>
              <div style="font-size:1.6rem;font-weight:700;color:#38bdf8;">${kpis.avg_riesgo}%</div>
            </div>
            <span style="font-size:2rem;color:#475569;">⚠️</span>
          </div>
        </div>
        <div class="dashboard-card double-bezel">
          <div class="inner-core" style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;color:#94a3b8;">Alertas OSINT</div>
              <div style="font-size:1.6rem;font-weight:700;color:#38bdf8;">${kpis.total_alertas.toLocaleString()}</div>
            </div>
            <span style="font-size:2rem;color:#475569;">👁️</span>
          </div>
        </div>
      `;

      // Renderizar gráficos en layout 2 columnas
      chartsEl.innerHTML = `
        <div style="display:grid;grid-template-columns:7fr 5fr;gap:16px;margin-bottom:16px;">
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.line_casos}</div></div>
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.bar_monto}</div></div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.bar_dept}</div></div>
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.donut_tipo}</div></div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.bar_canal_prioridad}</div></div>
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.osint_indicador}</div></div>
        </div>
      `;

      if (loading) loading.style.display = "none";
      intelDashboardLoaded = true;
    } catch (err) {
      console.error("Error cargando dashboard intel:", err);
      if (loading) loading.textContent = "Error al cargar el dashboard de inteligencia.";
    }
  }
```

### Paso 6e: Registrar hallazgos en `cargarDatosDelPanel`

- [ ] **Step 5: Agregar `panel-hallazgos` en el switch de paneles**

Localizar `cargarDatosDelPanel` (línea ~71):
```javascript
  function cargarDatosDelPanel(panelId) {
    if (panelId === "panel-casos") {
      fetchCasos();
    } else if (panelId === "panel-entidades") {
      fetchEntidades();
    } else if (panelId === "panel-inteligencia") {
      fetchRelaciones();
    } else if (panelId === "panel-dashboard") {
      fetchDashboardData();
    }
  }
```

Reemplazar con:
```javascript
  function cargarDatosDelPanel(panelId) {
    if (panelId === "panel-casos") {
      fetchCasos();
    } else if (panelId === "panel-entidades") {
      fetchEntidades();
    } else if (panelId === "panel-inteligencia") {
      fetchRelaciones();
    } else if (panelId === "panel-dashboard") {
      fetchDashboardData();
    } else if (panelId === "panel-hallazgos") {
      fetchIntelDashboard();
    }
  }
```

- [ ] **Step 6: Commit final**

```bash
git add static/console.js
git commit -m "feat(console): redirect fetchCasos to dataset CSV, add fetchIntelDashboard"
```

---

## Self-Review

**Spec coverage:**
- [x] `/api/dataset/casos` → Task 2
- [x] `/api/intel/dashboard` → Task 3
- [x] Registro blueprint → Task 4
- [x] Quitar vis-network + osint-graph scripts → Task 5, Step 1
- [x] Quitar nav "Grafo de Relaciones" → Task 5, Step 2
- [x] Reemplazar `panel-hallazgos` → Task 5, Step 3
- [x] Eliminar `panel-grafo` → Task 5, Step 4
- [x] Cambiar URL en fetchCasos → Task 6, Step 1
- [x] Cambiar URL en fetchDashboardData → Task 6, Step 2
- [x] Deshabilitar botón estado demo → Task 6, Step 3
- [x] Agregar fetchIntelDashboard → Task 6, Step 4
- [x] Registrar en cargarDatosDelPanel → Task 6, Step 5

**Placeholders:** Ninguno.

**Type consistency:** Las claves del JSON de `/api/dataset/casos` (`id_reporte`, `prioridad`, `estado`, `unidad_gaula`, `alias_sospechoso`, `numero_extorsivo`, `valor_exigido`, `medio_pago`, `descripcion`) coinciden con lo que leen `renderCasos()`, `filtrarCasos()`, `actualizarKPIsDashboard()` y `window.verDetalleCaso()` en `console.js`.
