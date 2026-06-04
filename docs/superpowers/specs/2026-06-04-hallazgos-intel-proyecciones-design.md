# Spec: Gráficas de Proyección Inercial — Panel Hallazgos Intel

**Fecha:** 2026-06-04  
**Branch:** feat/osint-graph-sigma  
**Enfoque elegido:** Frontend JS puro (Opción A)

---

## 1. Objetivo

Añadir una sección "FASE 2: Proyecciones Inerciales" al final del panel `#panel-hallazgos` en `console.html`. La sección presenta 4 gráficas Plotly que proyectan 6 meses hacia el futuro usando regresión lineal sobre los datos históricos del CSV (`nexo147_casos_demo_500.csv`), con tres escenarios seleccionables: Optimista, Realista y Pesimista.

La lógica vive completamente en `static/console.js` y opera sobre `intelDashboardState.rawCases` (ya cargado). Los filtros activos del panel (departamento, municipio, tipo, etc.) se aplican automáticamente a las proyecciones.

---

## 2. Alcance

### Archivos modificados

| Archivo | Naturaleza del cambio |
|---|---|
| `templates/casos/console.html` | Agregar bloque HTML de proyecciones al `#panel-hallazgos` |
| `static/console.js` | Agregar ~5 funciones JS nuevas + hook en `renderIntelDashboardCharts` |

No se crea ningún archivo nuevo, no se toca el backend.

### Fuera de alcance

- Modelos estadísticos avanzados (ARIMA, Prophet).
- Nuevo endpoint de backend.
- Cambios en otros paneles.

---

## 3. Diseño de la UI

### Ubicación

La sección se inserta **después** del `<div class="dashboard-grid intel-chart-grid">` existente (las 8 gráficas actuales), dentro del `<section id="panel-hallazgos">`.

### Estructura HTML

```html
<!-- SECCIÓN PROYECCIONES -->
<div class="intel-projection-section" id="intel-projection-section">

  <!-- Encabezado de sección -->
  <div class="section-header-tactical intel-section-header" style="margin-top: 2rem;">
    <div>
      <h3>FASE 2: Proyecciones Inerciales</h3>
      <p>Modelos de regresión lineal sobre el histórico filtrado. Horizonte: 6 meses.</p>
    </div>
    <div class="intel-live-chip">
      <span class="intel-live-dot" style="background:#eab308;"></span>
      <div>
        <strong>Motor predictivo activo</strong>
        <span>Proyección actualizada con los filtros del panel</span>
      </div>
    </div>
  </div>

  <!-- Selector de escenario -->
  <div class="dashboard-card double-bezel intel-scenario-selector">
    <div class="inner-core" style="text-align:center;">
      <span class="helper-text-mono" style="display:block;margin-bottom:12px;">
        Selecciona el escenario de proyección:
      </span>
      <div class="intel-scenario-btns" id="intel-scenario-btns">
        <button class="btn btn-secondary-tactical intel-scenario-btn" data-scenario="optimista">
          🟢 OPTIMISTA
        </button>
        <button class="btn btn-primary-tactical intel-scenario-btn active" data-scenario="realista">
          🟡 REALISTA
        </button>
        <button class="btn btn-secondary-tactical intel-scenario-btn" data-scenario="pesimista">
          🔴 PESIMISTA
        </button>
      </div>
    </div>
  </div>

  <!-- Texto de análisis táctico -->
  <div class="dashboard-card double-bezel intel-projection-analysis" id="intel-projection-analysis">
    <div class="inner-core">
      <!-- Inyectado dinámicamente por buildProjectionAnalysis() -->
    </div>
  </div>

  <!-- Grid de 4 gráficas -->
  <div class="dashboard-grid intel-chart-grid">

    <div class="dashboard-card double-bezel col-span-6 intel-chart-card">
      <div class="inner-core">
        <div class="intel-chart-header">
          <div>
            <h3>Proyección: Volumen de Casos Mensuales</h3>
            <p>Histórico + proyección inercial a 6 meses.</p>
          </div>
          <span class="intel-chart-tag">Proyección</span>
        </div>
        <div id="proj-chart-volumen" class="intel-plot"></div>
      </div>
    </div>

    <div class="dashboard-card double-bezel col-span-6 intel-chart-card">
      <div class="inner-core">
        <div class="intel-chart-header">
          <div>
            <h3>Proyección: Impacto Económico Mensual ($ COP)</h3>
            <p>Monto exigido/pérdida estimada proyectado.</p>
          </div>
          <span class="intel-chart-tag">Proyección</span>
        </div>
        <div id="proj-chart-monto" class="intel-plot"></div>
      </div>
    </div>

    <div class="dashboard-card double-bezel col-span-6 intel-chart-card">
      <div class="inner-core">
        <div class="intel-chart-header">
          <div>
            <h3>Proyección: Score de Riesgo Promedio</h3>
            <p>Evolución esperada del nivel de criticidad.</p>
          </div>
          <span class="intel-chart-tag">Proyección</span>
        </div>
        <div id="proj-chart-riesgo" class="intel-plot"></div>
      </div>
    </div>

    <div class="dashboard-card double-bezel col-span-6 intel-chart-card">
      <div class="inner-core">
        <div class="intel-chart-header">
          <div>
            <h3>Proyección: Top Tipos de Delito</h3>
            <p>Evolución proyectada por tipo de reporte (top 3).</p>
          </div>
          <span class="intel-chart-tag">Proyección</span>
        </div>
        <div id="proj-chart-tipos" class="intel-plot"></div>
      </div>
    </div>

  </div>
</div>
```

---

## 4. Funciones JS (static/console.js)

### 4.1 `calcLinearRegression(xArr, yArr)`

Regresión lineal por mínimos cuadrados (equivale a `np.polyfit(x, y, 1)`).

```
Input:  xArr = [0, 1, 2, ...n] (índices), yArr = valores históricos
Output: { slope, intercept }
Fórmula: slope = (n·Σxy - Σx·Σy) / (n·Σx² - (Σx)²)
          intercept = (Σy - slope·Σx) / n
```

### 4.2 `buildFutureMonths(lastMonthStr, n)`

Genera N etiquetas `YYYY-MM` consecutivas a partir de `lastMonthStr`.

```
Input:  "2025-12", n=6
Output: ["2026-01", "2026-02", ..., "2026-06"]
```

### 4.3 `getScenarioModifiers(escenario, steps)`

Devuelve array de `steps` multiplicadores según escenario:

| Escenario | Lógica | Color |
|---|---|---|
| `optimista` | linspace(0.85, 0.50, steps) | `#22c55e` |
| `realista` | `linspace(0.97, 1.03, steps)` — oscila levemente alrededor de la tendencia base | `#eab308` |
| `pesimista` | linspace(1.20, 2.10, steps) | `#ef4444` |

### 4.4 `buildProjectionSeries(historicMonths, historicValues, escenario)`

Orquesta la proyección para una variable escalar:

1. Llama `calcLinearRegression` con `x=[0..n-1]`, `y=historicValues`.
2. Extrae la última predicción lineal en `x=n, n+1..n+5`.
3. Multiplica por `getScenarioModifiers`.
4. Devuelve `{ futureMonths, futureValues }`.

### 4.5 `buildProjectionAnalysis(escenario, tendencia, casos, monto)`

Genera el HTML del texto de análisis táctico y lo inyecta en `#intel-projection-analysis .inner-core`. Sin efecto typewriter. Incluye:
- Descripción de tendencia detectada (al alza / a la baja / estable).
- Resumen del escenario seleccionado.
- 3 acciones operativas sugeridas (igual estructura que el código de referencia).

### 4.6 `renderIntelProjections(filteredRecords, escenario)`

Función principal. Construye los datos y llama a `renderIntelPlot` para cada una de las 4 gráficas:

**`proj-chart-volumen`**: línea gris (histórico) + línea punteada coloreada (proyección).

**`proj-chart-monto`**: barras azules (histórico) + marcadores punteados (proyección).

**`proj-chart-riesgo`**: línea gris (score promedio mensual histórico) + línea punteada (proyección).

**`proj-chart-tipos`**: top 3 tipos de delito, cada uno con línea histórica (gris claro) + línea proyectada (coloreada).

### 4.7 Hook en `renderIntelDashboardCharts`

Al final de la función existente, agregar:

```js
const activeScenario = document.querySelector('.intel-scenario-btn.active')?.dataset.scenario || 'realista';
renderIntelProjections(filtered, activeScenario);
buildProjectionAnalysis(activeScenario, /* tendencia */, /* casos */, /* monto */);
```

### 4.8 `bindProjectionScenario()`

Agrega event listeners a los botones `.intel-scenario-btn` para cambiar el escenario activo y re-renderizar. Se llama desde `bindIntelDashboardEvents()` que ya existe.

---

## 5. Estado de proyección

El escenario activo se almacena como atributo `data-scenario` de la clase `.active` en los botones, sin estado extra. No se necesita ampliar `intelDashboardState`.

---

## 6. Compatibilidad y edge cases

- Si hay **menos de 2 meses históricos** en el set filtrado: mostrar mensaje "Datos insuficientes para proyección" en lugar de la gráfica.
- Si **todos los valores son 0**: devolver proyección de ceros (no ejecutar regresión).
- La sección de proyecciones usa los mismos estilos que las gráficas existentes (`intel-chart-card`, `intel-plot`, `double-bezel`). No se requieren estilos nuevos salvo la clase `.intel-scenario-btns` (flex, gap, centrado).

---

## 7. Criterios de aceptación

- [ ] La sección aparece debajo de las 8 gráficas existentes en el panel Hallazgos Intel.
- [ ] El selector de escenario cambia las curvas proyectadas en las 4 gráficas.
- [ ] Cambiar un filtro del panel (departamento, tipo, etc.) actualiza también las proyecciones.
- [ ] Con datos insuficientes (< 2 meses), se muestra mensaje de alerta en lugar del gráfico.
- [ ] El texto de análisis táctico refleja la tendencia y el escenario seleccionados.
- [ ] No se rompe ninguna funcionalidad existente del panel.
