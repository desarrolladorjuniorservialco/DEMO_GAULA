# Hallazgos Intel — Proyecciones Inerciales Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar una sección "FASE 2: Proyecciones Inerciales" al final del panel `#panel-hallazgos` con 4 gráficas Plotly que proyectan 6 meses usando regresión lineal y 3 escenarios (Optimista / Realista / Pesimista).

**Architecture:** Todo en frontend. Las nuevas funciones JS operan sobre `intelDashboardState.rawCases` (ya cargado), aplican los filtros activos del panel, calculan regresión lineal por mínimos cuadrados, y renderizan con el mismo helper `renderIntelPlot` existente. No hay cambios de backend.

**Tech Stack:** Vanilla JS (ES6+), Plotly.js (ya incluido en la página), Flask/Jinja2 para el template HTML.

---

## File Map

| Archivo | Acción | Qué cambia |
|---|---|---|
| `templates/casos/console.html` | Modificar | Insertar bloque HTML de proyecciones antes de `</section>` del `#panel-hallazgos` (línea 1035) |
| `static/console.js` | Modificar | 6 funciones nuevas + 2 hooks en funciones existentes |

---

## Task 1: HTML — Skeleton de la sección de proyecciones

**Files:**
- Modify: `templates/casos/console.html:1035`

- [ ] **Step 1: Localizar el punto de inserción**

Abre [templates/casos/console.html](templates/casos/console.html) y busca la línea que contiene `</section>` que cierra el bloque `<!-- PANEL HALLAZGOS INTEL -->`. Está en la línea 1036 (después del cierre del `dashboard-grid intel-chart-grid`).

Texto a encontrar (justo antes de `</section>`):
```html
          </div>
        </section>


        <!-- PANEL MOTOR ETL Y CORRELACIÓN -->
```

- [ ] **Step 2: Insertar el HTML de la sección**

Insertar el siguiente bloque **antes** del `</section>` que cierra `#panel-hallazgos`:

```html

          <!-- SECCIÓN PROYECCIONES INERCIALES -->
          <div class="intel-projection-section" id="intel-projection-section">

            <div class="section-header-tactical intel-section-header" style="margin-top:2rem;">
              <div>
                <h3>FASE 2: Proyecciones Inerciales</h3>
                <p>Modelos de regresión lineal sobre el histórico filtrado. Horizonte: 6 meses.</p>
              </div>
              <div class="intel-live-chip">
                <span class="intel-live-dot" style="background:#eab308;box-shadow:0 0 6px #eab30888;"></span>
                <div>
                  <strong>Motor predictivo activo</strong>
                  <span>Proyección actualizada con los filtros del panel</span>
                </div>
              </div>
            </div>

            <div class="dashboard-card double-bezel" style="margin-bottom:1rem;">
              <div class="inner-core" style="text-align:center;">
                <span class="helper-text-mono" style="display:block;margin-bottom:12px;">Escenario de proyección:</span>
                <div id="intel-scenario-btns" style="display:flex;justify-content:center;gap:.75rem;flex-wrap:wrap;">
                  <button class="btn btn-secondary-tactical intel-scenario-btn" data-scenario="optimista">🟢 OPTIMISTA</button>
                  <button class="btn btn-primary-tactical intel-scenario-btn active" data-scenario="realista">🟡 REALISTA</button>
                  <button class="btn btn-secondary-tactical intel-scenario-btn" data-scenario="pesimista">🔴 PESIMISTA</button>
                </div>
              </div>
            </div>

            <div class="dashboard-card double-bezel" id="intel-projection-analysis" style="margin-bottom:1rem;">
              <div class="inner-core" id="intel-projection-analysis-body">
                <!-- Inyectado por buildProjectionAnalysis() -->
              </div>
            </div>

            <div class="dashboard-grid intel-chart-grid">
              <div class="dashboard-card double-bezel col-span-6 intel-chart-card">
                <div class="inner-core">
                  <div class="intel-chart-header">
                    <div><h3>Proyección: Volumen de Casos</h3><p>Casos mensuales — histórico + 6 meses.</p></div>
                    <span class="intel-chart-tag">Proyección</span>
                  </div>
                  <div id="proj-chart-volumen" class="intel-plot"></div>
                </div>
              </div>
              <div class="dashboard-card double-bezel col-span-6 intel-chart-card">
                <div class="inner-core">
                  <div class="intel-chart-header">
                    <div><h3>Proyección: Impacto Económico ($ COP)</h3><p>Monto mensual estimado — histórico + 6 meses.</p></div>
                    <span class="intel-chart-tag">Proyección</span>
                  </div>
                  <div id="proj-chart-monto" class="intel-plot"></div>
                </div>
              </div>
              <div class="dashboard-card double-bezel col-span-6 intel-chart-card">
                <div class="inner-core">
                  <div class="intel-chart-header">
                    <div><h3>Proyección: Score de Riesgo Promedio</h3><p>Criticidad esperada — histórico + 6 meses.</p></div>
                    <span class="intel-chart-tag">Proyección</span>
                  </div>
                  <div id="proj-chart-riesgo" class="intel-plot"></div>
                </div>
              </div>
              <div class="dashboard-card double-bezel col-span-6 intel-chart-card">
                <div class="inner-core">
                  <div class="intel-chart-header">
                    <div><h3>Proyección: Top Tipos de Delito</h3><p>Evolución proyectada — top 3 tipos de reporte.</p></div>
                    <span class="intel-chart-tag">Proyección</span>
                  </div>
                  <div id="proj-chart-tipos" class="intel-plot"></div>
                </div>
              </div>
            </div>

          </div>
          <!-- /SECCIÓN PROYECCIONES -->
```

- [ ] **Step 3: Verificar que el HTML es válido**

Abrir la consola del navegador después de recargar la página y ejecutar:
```js
console.assert(document.getElementById('intel-projection-section') !== null, 'Sección proyecciones existe');
console.assert(document.getElementById('proj-chart-volumen') !== null, 'proj-chart-volumen existe');
console.assert(document.querySelectorAll('.intel-scenario-btn').length === 3, '3 botones de escenario');
```
Expected: sin errores de aserción.

- [ ] **Step 4: Commit**

```bash
git add templates/casos/console.html
git commit -m "feat(hallazgos): add projection section HTML skeleton"
```

---

## Task 2: JS — Funciones matemáticas puras

**Files:**
- Modify: `static/console.js` — insertar después de la línea 1327 (cierre de `renderIntelRiskMunicipio`), antes de `function syncIntelFilterState()`

Las tres funciones son independientes entre sí: se pueden probar en consola antes de integrarlas.

- [ ] **Step 1: Verificar el punto de inserción**

Buscar en [static/console.js](static/console.js) el texto exacto:
```js
  function syncIntelFilterState() {
```
La inserción va **inmediatamente antes** de esa línea (actualmente línea ~1329).

- [ ] **Step 2: Insertar las 3 funciones de utilidad**

Insertar el siguiente bloque antes de `function syncIntelFilterState()`:

```js
  // ── Proyecciones: utilidades matemáticas ──────────────────────────────────

  function calcLinearRegression(xArr, yArr) {
    const n = xArr.length;
    if (n < 2) return { slope: 0, intercept: yArr[0] || 0 };
    const sumX  = xArr.reduce((a, b) => a + b, 0);
    const sumY  = yArr.reduce((a, b) => a + b, 0);
    const sumXY = xArr.reduce((s, x, i) => s + x * yArr[i], 0);
    const sumX2 = xArr.reduce((s, x) => s + x * x, 0);
    const denom = n * sumX2 - sumX * sumX;
    if (denom === 0) return { slope: 0, intercept: sumY / n };
    const slope     = (n * sumXY - sumX * sumY) / denom;
    const intercept = (sumY - slope * sumX) / n;
    return { slope, intercept };
  }

  function buildFutureMonths(lastMonthStr, n) {
    const months = [];
    const [y, m] = lastMonthStr.split("-").map(Number);
    for (let i = 1; i <= n; i++) {
      const d = new Date(y, m - 1 + i, 1);
      months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
    }
    return months;
  }

  function getScenarioModifiers(escenario, steps) {
    const linspace = (start, end, n) =>
      Array.from({ length: n }, (_, i) => start + (end - start) * (i / (n - 1)));
    if (escenario === "optimista")  return { mods: linspace(0.85, 0.50, steps), color: "#22c55e" };
    if (escenario === "pesimista")  return { mods: linspace(1.20, 2.10, steps), color: "#ef4444" };
    return { mods: linspace(0.97, 1.03, steps), color: "#eab308" };  // realista
  }
```

- [ ] **Step 3: Probar en consola del navegador**

Abrir las DevTools en la página de la consola (panel Hallazgos Intel activo) y ejecutar:

```js
// Regresión perfecta y = 2x + 1
const reg = calcLinearRegression([0,1,2,3], [1,3,5,7]);
console.assert(Math.abs(reg.slope - 2) < 0.001,     'slope correcto');
console.assert(Math.abs(reg.intercept - 1) < 0.001, 'intercept correcto');

// Meses futuros a partir de diciembre 2025
const months = buildFutureMonths("2025-12", 3);
console.assert(months[0] === "2026-01", 'mes 1 correcto');
console.assert(months[2] === "2026-03", 'mes 3 correcto');

// Modificadores: pesimista creciente
const { mods, color } = getScenarioModifiers("pesimista", 6);
console.assert(mods[0] < mods[5],  'pesimista crece');
console.assert(color === "#ef4444", 'color pesimista rojo');

console.log("✅ calcLinearRegression, buildFutureMonths, getScenarioModifiers OK");
```

Expected: `✅ calcLinearRegression, buildFutureMonths, getScenarioModifiers OK` en consola.

- [ ] **Step 4: Commit**

```bash
git add static/console.js
git commit -m "feat(hallazgos): add projection math utilities (regression, months, modifiers)"
```

---

## Task 3: JS — buildProjectionSeries + buildProjectionAnalysis

**Files:**
- Modify: `static/console.js` — insertar después del bloque insertado en Task 2, antes de `function syncIntelFilterState()`

- [ ] **Step 1: Insertar `buildProjectionSeries`**

Agregar inmediatamente después del bloque de Task 2 (justo antes de `function syncIntelFilterState()`):

```js
  function buildProjectionSeries(historicMonths, historicValues, escenario) {
    const n = historicValues.length;
    if (n < 2) return { futureMonths: [], futureValues: [] };
    const xArr = historicValues.map((_, i) => i);
    const { slope, intercept } = calcLinearRegression(xArr, historicValues);
    const { mods } = getScenarioModifiers(escenario, 6);
    const futureMonths = buildFutureMonths(historicMonths[historicMonths.length - 1], 6);
    const futureValues = mods.map((mod, i) => Math.max(0, Math.round((slope * (n + i) + intercept) * mod)));
    return { futureMonths, futureValues };
  }
```

- [ ] **Step 2: Insertar `buildProjectionAnalysis`**

Agregar justo después de `buildProjectionSeries`:

```js
  function buildProjectionAnalysis(escenario, tendencia, totalCasos, monto) {
    const escenarioConfig = {
      optimista: {
        icon: "🟢", label: "OPTIMISTA", borderColor: "#22c55e",
        resumen: "El modelo de contención proyecta una inflexión negativa en la curva. Las medidas preventivas muestran efectividad.",
        acciones: [
          "Mantener cobertura física en cuadrantes críticos identificados.",
          "Migrar recursos logísticos remanentes hacia cibervigilancia.",
          "Sincronizar bases locales con la central para consolidar la tendencia.",
        ],
      },
      pesimista: {
        icon: "🔴", label: "PESIMISTA", borderColor: "#ef4444",
        resumen: "ANOMALÍA CRÍTICA: La simulación de estrés proyecta un brote operativo inminente. El volumen superará los umbrales de contención.",
        acciones: [
          "Urgente: instaurar Puesto de Mando Unificado (PMU) con autoridades locales.",
          "Desplegar unidades tácticas especiales para mitigar el vector de amenaza.",
          "Activar protocolos de bloqueo preventivo sobre estructuras de financiamiento.",
        ],
      },
      realista: {
        icon: "🟡", label: "REALISTA", borderColor: "#eab308",
        resumen: "La proyección no detecta desvíos atípicos. El vector mantiene una tasa estable dentro de los rangos previstos.",
        acciones: [
          "Sostener el monitoreo operativo Fase 2 sobre el vector delictivo.",
          "Actualizar semanalmente los diccionarios de inteligencia digital y fuentes OSINT.",
          "Optimizar la tasa de respuesta del canal 147 para romper ciclos delictivos.",
        ],
      },
    };

    const cfg = escenarioConfig[escenario] || escenarioConfig.realista;
    const tendenciaLabel = tendencia > 0 ? "al alza ↑" : tendencia < 0 ? "a la baja ↓" : "estable →";

    const el = document.getElementById("intel-projection-analysis-body");
    if (!el) return;
    el.innerHTML = `
      <div style="border-left:4px solid ${cfg.borderColor};padding-left:1rem;">
        <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem;">
          <span style="font-size:1.5rem;">${cfg.icon}</span>
          <div>
            <strong style="color:${cfg.borderColor};font-size:1rem;">ESCENARIO ${cfg.label}</strong>
            <span class="helper-text-mono" style="display:block;font-size:.75rem;">Tendencia histórica: ${tendenciaLabel} · ${totalCasos.toLocaleString("es-CO")} casos · $${monto.toLocaleString("es-CO")} COP</span>
          </div>
        </div>
        <p style="margin-bottom:.75rem;color:#c0ccdc;">${cfg.resumen}</p>
        <strong style="display:block;margin-bottom:.5rem;color:#8b99ae;font-size:.8rem;letter-spacing:.07em;">ACCIONES SUGERIDAS:</strong>
        <ul style="margin:0;padding-left:1.25rem;">
          ${cfg.acciones.map(a => `<li style="color:#f0f4fa;margin-bottom:.35rem;">${a}</li>`).join("")}
        </ul>
      </div>
    `;
  }
```

- [ ] **Step 3: Probar en consola del navegador**

Con el panel Hallazgos Intel abierto (después de que los datos cargaron):

```js
// buildProjectionSeries — serie con pendiente positiva conocida
const hist = [1, 2, 3, 4, 5];
const months = ["2025-08","2025-09","2025-10","2025-11","2025-12"];
const res = buildProjectionSeries(months, hist, "realista");
console.assert(res.futureMonths.length === 6,          'futureMonths tiene 6 entradas');
console.assert(res.futureMonths[0] === "2026-01",      'primer mes futuro correcto');
console.assert(res.futureValues.every(v => v >= 0),    'sin valores negativos');

// buildProjectionAnalysis — verifica que inyecta HTML
buildProjectionAnalysis("pesimista", 1, 120, 5000000);
const body = document.getElementById("intel-projection-analysis-body");
console.assert(body && body.innerHTML.includes("PESIMISTA"), 'análisis pesimista renderizado');

console.log("✅ buildProjectionSeries, buildProjectionAnalysis OK");
```

Expected: `✅ buildProjectionSeries, buildProjectionAnalysis OK`

- [ ] **Step 4: Commit**

```bash
git add static/console.js
git commit -m "feat(hallazgos): add buildProjectionSeries and buildProjectionAnalysis"
```

---

## Task 4: JS — renderIntelProjections (4 gráficas)

**Files:**
- Modify: `static/console.js` — insertar después de `buildProjectionAnalysis`, antes de `function syncIntelFilterState()`

- [ ] **Step 1: Insertar `renderIntelProjections`**

```js
  function renderIntelProjections(filteredRecords, escenario) {
    const STEPS = 6;
    const projChartIds = ["proj-chart-volumen", "proj-chart-monto", "proj-chart-riesgo", "proj-chart-tipos"];

    if (filteredRecords.length < 2) {
      projChartIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = '<p style="color:#8b99ae;padding:1rem;font-size:.8rem;">Datos insuficientes para proyección (mínimo 2 meses).</p>';
      });
      return;
    }

    const { color: projColor } = getScenarioModifiers(escenario, STEPS);

    // Agrupa registros por mes-año
    function monthBuckets(records, valueFn) {
      const map = new Map();
      records.forEach(r => {
        const d = parseIntelDate(r.fecha_registro);
        if (!d) return;
        const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
        const prev = map.get(key) || { sum: 0, count: 0 };
        const v = valueFn(r);
        map.set(key, { sum: prev.sum + v, count: prev.count + 1 });
      });
      return Array.from(map.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([k, v]) => ({ month: k, sum: v.sum, count: v.count, avg: v.sum / v.count }));
    }

    const histLayout = (xTitle, yTitle) => ({
      xaxis: { title: xTitle },
      yaxis: { title: yTitle },
      showlegend: true,
      margin: { l: 52, r: 24, t: 12, b: 60 },
    });

    // Pre-compute para buildProjectionAnalysis antes de los renders
    const volData    = monthBuckets(filteredRecords, () => 1);
    const volMonths  = volData.map(d => d.month);
    const volValues  = volData.map(d => d.count);
    const volSlope   = calcLinearRegression(volValues.map((_, i) => i), volValues).slope;
    const montoDataPre  = monthBuckets(filteredRecords, r => Number(normalizeIntelValue(r.valor_exigido).replace(/[^0-9.]/g, "")) || 0);
    const totalMontoPre = montoDataPre.reduce((s, d) => s + d.sum, 0);
    buildProjectionAnalysis(escenario, volSlope, filteredRecords.length, totalMontoPre);

    // ── G1: Volumen de casos ────────────────────────────────────────────────
    const { futureMonths: volFM, futureValues: volFV } = buildProjectionSeries(volMonths, volValues, escenario);

    renderIntelPlot("proj-chart-volumen", [
      { type: "scatter", mode: "lines+markers", name: "Histórico",    x: volMonths, y: volValues,  line: { color: "#94a3b8" } },
      { type: "scatter", mode: "lines+markers", name: "Proyección",   x: volFM,     y: volFV,      line: { color: projColor, dash: "dot" }, marker: { symbol: "diamond" } },
    ], histLayout("Mes/Año", "Casos"));

    // ── G2: Impacto económico ───────────────────────────────────────────────
    // montoDataPre ya calculado arriba (reutilizar)
    const montoData   = montoDataPre;
    const montoMonths = montoData.map(d => d.month);
    const montoValues = montoData.map(d => d.sum);
    const { futureMonths: montoFM, futureValues: montoFV } = buildProjectionSeries(montoMonths, montoValues, escenario);

    renderIntelPlot("proj-chart-monto", [
      { type: "bar",     name: "Histórico ($)", x: montoMonths, y: montoValues, marker: { color: "#38bdf8" } },
      { type: "scatter", mode: "lines+markers", name: "Proyección ($)", x: montoFM, y: montoFV, line: { color: projColor, dash: "dot" }, marker: { symbol: "diamond" } },
    ], histLayout("Mes/Año", "Monto ($)"));

    // ── G3: Score de riesgo promedio ────────────────────────────────────────
    const riesgoData   = monthBuckets(filteredRecords, r => parseIntelScore(r.score_riesgo));
    const riesgoMonths = riesgoData.map(d => d.month);
    const riesgoValues = riesgoData.map(d => parseFloat(d.avg.toFixed(1)));
    const { futureMonths: riesgoFM, futureValues: riesgoFV } = buildProjectionSeries(riesgoMonths, riesgoValues, escenario);

    renderIntelPlot("proj-chart-riesgo", [
      { type: "scatter", mode: "lines+markers", name: "Score histórico", x: riesgoMonths, y: riesgoValues, line: { color: "#94a3b8" } },
      { type: "scatter", mode: "lines+markers", name: "Proyección",      x: riesgoFM,     y: riesgoFV,     line: { color: projColor, dash: "dot" }, marker: { symbol: "diamond" } },
    ], histLayout("Mes/Año", "Score promedio"));

    // ── G4: Top 3 tipos de delito ───────────────────────────────────────────
    const tipoCount = new Map();
    filteredRecords.forEach(r => {
      const t = normalizeIntelValue(r.tipo_reporte);
      if (t) tipoCount.set(t, (tipoCount.get(t) || 0) + 1);
    });
    const top3 = Array.from(tipoCount.entries()).sort((a, b) => b[1] - a[1]).slice(0, 3).map(e => e[0]);
    const tipoColors = ["#38bdf8", "#a78bfa", "#fb923c"];

    const tipoTraces = top3.flatMap((tipo, idx) => {
      const tipoRecords = filteredRecords.filter(r => normalizeIntelValue(r.tipo_reporte) === tipo);
      const tData = monthBuckets(tipoRecords, () => 1);
      const tMonths = tData.map(d => d.month);
      const tValues = tData.map(d => d.count);
      const { futureMonths: tFM, futureValues: tFV } = buildProjectionSeries(tMonths, tValues, escenario);
      return [
        { type: "scatter", mode: "lines", name: tipo,               x: tMonths, y: tValues, line: { color: tipoColors[idx], width: 2 } },
        { type: "scatter", mode: "lines", name: `${tipo} (proy.)`,  x: tFM,     y: tFV,     line: { color: tipoColors[idx], dash: "dot", width: 1.5 }, showlegend: false },
      ];
    });
    renderIntelPlot("proj-chart-tipos", tipoTraces, histLayout("Mes/Año", "Casos por tipo"));
  }
```

- [ ] **Step 2: Verificar en el navegador (sin escenario wired aún)**

Abrir la consola con datos cargados y ejecutar manualmente:
```js
// Usar los datos ya cargados del panel
const sample = intelDashboardState.rawCases.slice(0, 50);
renderIntelProjections(sample, "realista");
```

Expected: Las 4 gráficas aparecen en el DOM (`proj-chart-*`) con datos visibles. Sin errores en consola.

- [ ] **Step 3: Commit**

```bash
git add static/console.js
git commit -m "feat(hallazgos): add renderIntelProjections with 4 Plotly charts"
```

---

## Task 5: JS — Wire: hooks en renderIntelDashboardCharts y bindIntelDashboardEvents

**Files:**
- Modify: `static/console.js:1118` (hook en renderIntelDashboardCharts)
- Modify: `static/console.js:1372` (bindProjectionScenario dentro de bindIntelDashboardEvents)

- [ ] **Step 1: Agregar hook al final de `renderIntelDashboardCharts`**

Localizar la línea:
```js
    renderIntelRiskMunicipio(riskMunicipioBuckets);
  }
```
(actualmente líneas 1118-1119)

Reemplazar por:
```js
    renderIntelRiskMunicipio(riskMunicipioBuckets);

    const activeScenario = document.querySelector(".intel-scenario-btn.active")?.dataset.scenario || "realista";
    renderIntelProjections(filtered, activeScenario);
  }
```

- [ ] **Step 2: Agregar `bindProjectionScenario` y llamarla desde `bindIntelDashboardEvents`**

Localizar el cierre de `bindIntelDashboardEvents` (la llave `}` después del bloque del `resetBtn`):
```js
    }
  }

  async function fetchIntelDashboard() {
```

Reemplazar ese bloque final por:
```js
    }

    document.querySelectorAll(".intel-scenario-btn").forEach(btn => {
      if (btn.dataset.projBound === "1") return;
      btn.dataset.projBound = "1";
      btn.addEventListener("click", () => {
        document.querySelectorAll(".intel-scenario-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const filtered = (() => {
          const ndf = applyIntelNonDateFilters(intelDashboardState.rawCases);
          return applyIntelDateFilters(ndf);
        })();
        // renderIntelProjections llama buildProjectionAnalysis internamente — no duplicar
        renderIntelProjections(filtered, btn.dataset.scenario);
      });
    });
  }

  async function fetchIntelDashboard() {
```

- [ ] **Step 3: Verificar integración completa**

1. Navegar al panel **Hallazgos Intel**.
2. Esperar que los datos carguen (las 8 gráficas existentes aparecen).
3. Hacer scroll al final — deben aparecer las 4 gráficas de proyección con escenario REALISTA activo.
4. Hacer clic en **PESIMISTA** — las 4 gráficas de proyección cambian a curvas rojas crecientes; el texto de análisis se actualiza.
5. Hacer clic en **OPTIMISTA** — curvas verdes decrecientes.
6. Cambiar el filtro de **Departamento** a "Antioquia" — las 8 gráficas descriptivas Y las 4 de proyección se actualizan al mismo tiempo.
7. Clic en **Limpiar filtros** — todo vuelve al estado nacional.

Expected en todos los pasos: sin errores en consola del navegador.

- [ ] **Step 4: Commit**

```bash
git add static/console.js
git commit -m "feat(hallazgos): wire projection scenario selector and filter hook"
```

---

## Task 6: Edge case — datos insuficientes

**Files:**
- No new code — ya implementado en Task 4 (el guard `filteredRecords.length < 2`)

- [ ] **Step 1: Verificar el edge case manualmente**

Con el panel Hallazgos Intel visible, ejecutar en consola:
```js
renderIntelProjections([], "realista");
```
Expected: los 4 divs `proj-chart-*` muestran el mensaje "Datos insuficientes para proyección (mínimo 2 meses)." y no se producen errores.

```js
renderIntelProjections([intelDashboardState.rawCases[0]], "realista");
```
Expected: mismo mensaje (1 registro < 2 meses mínimos).

- [ ] **Step 2: Verificar que el filtro extremo no rompe nada**

En el panel, establecer:
- Departamento = cualquier departamento con 1 o 0 casos
- Expected: gráficas descriptivas vacías + mensaje de datos insuficientes en proyecciones + sin JS errors.

- [ ] **Step 3: Commit final de cierre**

```bash
git add templates/casos/console.html static/console.js
git commit -m "feat(hallazgos): projection charts complete — 4 charts, 3 scenarios, filter-aware"
```

---

## Checklist de criterios de aceptación (del spec)

- [ ] La sección aparece debajo de las 8 gráficas existentes en Hallazgos Intel
- [ ] El selector de escenario cambia las curvas proyectadas en las 4 gráficas
- [ ] Cambiar un filtro del panel actualiza también las proyecciones
- [ ] Con datos insuficientes (< 2 meses) se muestra mensaje en lugar del gráfico
- [ ] El texto de análisis táctico refleja tendencia y escenario activos
- [ ] Ninguna funcionalidad existente del panel se rompe

---

## Notas de harness engineering

- **Sin estado extra:** el escenario activo se lee del DOM (`.intel-scenario-btn.active`), sin ampliar `intelDashboardState`.
- **Guard de re-binding:** `btn.dataset.projBound` y `node.dataset.intelBound` evitan listeners duplicados al re-entrar en el panel.
- **Token-efficient diffs:** cada task modifica solo el fragmento necesario; no se reescriben funciones existentes, solo se añaden líneas al final de las que corresponde.
- **Commits atómicos:** cada task termina con un commit que deja el repositorio en estado válido y ejecutable.
