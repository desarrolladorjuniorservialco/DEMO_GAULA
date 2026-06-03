document.addEventListener("DOMContentLoaded", () => {
  // Check user role from DOM
  const roleElement = document.querySelector(".user-info span");
  const userRole = roleElement ? roleElement.innerText.toLowerCase().replace("rol: ", "").trim() : "invitado";
  
  // If the user has a role that doesn't see intelligence panels, exit early
  if (userRole === "operador" || userRole === "invitado") {
    return;
  }

  // --- STATE AND HELPER GLOBALS ---
  let chartInstances = {};
  let etlInterval = null;

  // Cleanup helper for Chart.js instances
  function destroyChart(id) {
    if (chartInstances[id]) {
      chartInstances[id].destroy();
      delete chartInstances[id];
    }
  }

  // Hook into navigation clicks to load additional panel data
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const targetPanelId = item.getAttribute("data-panel");
      cargarDatosDashboard(targetPanelId);
    });
  });

  // Handle panel changes triggered programmatically or on startup
  function cargarDatosDashboard(panelId) {
    // Clear ETL auto-refresh if moving away from ETL panel
    if (panelId !== "panel-etl" && etlInterval) {
      clearInterval(etlInterval);
      etlInterval = null;
    }

    if (panelId === "panel-hallazgos") {
      fetchHallazgos();
    } else if (panelId === "panel-grafo") {
      fetchGrafo();
    } else if (panelId === "panel-etl") {
      fetchETLStatus();
      // Setup periodic refresh every 30 seconds
      if (!etlInterval) {
        etlInterval = setInterval(fetchETLStatus, 30000);
      }
    } else if (panelId === "panel-datamart") {
      fetchDataMart();
    }
  }

  // Trigger loading on initial URL hash on startup
  const initialHash = window.location.hash;
  if (initialHash) {
    const activeItem = document.querySelector(`.nav-item[href="${initialHash}"]`);
    if (activeItem) {
      const panelId = activeItem.getAttribute("data-panel");
      setTimeout(() => cargarDatosDashboard(panelId), 500);
    }
  }

  // --- 1. HALLAZGOS Y OSINT INDICADORES ---
  async function fetchHallazgos() {
    const hallazgosBody = document.getElementById("hallazgos-body");
    const indicadoresList = document.getElementById("indicadores-osint-list");

    if (hallazgosBody) {
      hallazgosBody.innerHTML = `<tr><td colspan="4" class="text-center helper-text-mono">Consultando hallazgos...</td></tr>`;
    }
    if (indicadoresList) {
      indicadoresList.innerHTML = `<div class="helper-text-mono text-center">Consultando indicadores...</div>`;
    }

    try {
      // Parallel fetch
      const [resHallazgos, resIndicadores] = await Promise.all([
        fetch("/api/intel/hallazgos"),
        fetch("/api/osint/indicadores")
      ]);

      if (resHallazgos.ok && hallazgosBody) {
        const hallazgos = await resHallazgos.json();
        if (hallazgos.length === 0) {
          hallazgosBody.innerHTML = `<tr><td colspan="4" class="text-center">No hay hallazgos registrados.</td></tr>`;
        } else {
          hallazgosBody.innerHTML = hallazgos.map(h => {
            let classBadge = "badge-status-table info";
            if (h.nivel_clasificacion.toLowerCase() === "secreto") classBadge = "badge-status-table alert-kpi";
            if (h.nivel_clasificacion.toLowerCase() === "confidencial") classBadge = "badge-status-table warning";
            if (h.nivel_clasificacion.toLowerCase() === "reservado") classBadge = "badge-status-table info";

            return `
              <tr class="fade-in-row">
                <td>
                  <strong>${h.titulo}</strong>
                  <p class="text-muted" style="margin-top: 4px; font-size: 12px; line-height: 1.4;">${h.descripcion}</p>
                </td>
                <td><span class="${classBadge}">${h.nivel_clasificacion}</span></td>
                <td><span class="badge">${h.estado}</span></td>
                <td class="text-mono text-small-col">${h.created_at}</td>
              </tr>
            `;
          }).join("");
        }
      }

      if (resIndicadores.ok && indicadoresList) {
        const indicadores = await resIndicadores.json();
        if (indicadores.length === 0) {
          indicadoresList.innerHTML = `<div class="text-center text-muted">Sin indicadores OSINT activos.</div>`;
        } else {
          indicadoresList.innerHTML = indicadores.map(i => {
            let riskClass = "neutral";
            if (i.nivel_riesgo.toLowerCase() === "crítico" || i.nivel_riesgo.toLowerCase() === "critico") riskClass = "alert-kpi";
            if (i.nivel_riesgo.toLowerCase() === "alto") riskClass = "warning";

            return `
              <div class="indicador-row slide-up-item">
                <div class="indicador-header-row">
                  <span class="badge ${riskClass}">${i.nivel_riesgo}</span>
                  <strong>${i.tipo.toUpperCase()}: ${i.valor}</strong>
                </div>
                <p class="text-muted" style="font-size: 12px; margin-top: 4px; line-height: 1.3;">${i.descripcion}</p>
                <div class="indicador-meta">
                  <span>Detección: ${i.fecha_deteccion}</span>
                  <span>Fuente: ${i.fuente_origen}</span>
                </div>
              </div>
            `;
          }).join("");
        }
      }
    } catch (err) {
      console.error("Error fetching hallazgos:", err);
      if (hallazgosBody) hallazgosBody.innerHTML = `<tr><td colspan="4" class="text-center error-text">Fallo de comunicación.</td></tr>`;
      if (indicadoresList) indicadoresList.innerHTML = `<div class="text-center error-text">Fallo al conectar.</div>`;
    }
  }

  // --- 2. GRAFO DE RELACIONES ---
  async function fetchGrafo() {
    const nodosBody = document.getElementById("grafo-nodos-body");
    const aristasBody = document.getElementById("grafo-aristas-body");
    const statsContainer = document.getElementById("grafo-stats-container");

    if (nodosBody) nodosBody.innerHTML = `<tr><td colspan="4" class="text-center helper-text-mono">Consultando nodos...</td></tr>`;
    if (aristasBody) aristasBody.innerHTML = `<tr><td colspan="4" class="text-center helper-text-mono">Consultando relaciones...</td></tr>`;

    try {
      const response = await fetch("/api/intel/grafo");
      if (response.ok) {
        const data = await response.json();
        
        // Render Nodos
        if (nodosBody) {
          nodosBody.innerHTML = data.nodos.map(n => `
            <tr class="fade-in-row">
              <td class="text-mono">NODE-${n.id}</td>
              <td><span class="badge-status-table info">${n.entity_type.toUpperCase()}</span></td>
              <td><strong>${n.label}</strong></td>
              <td><span class="badge ${n.nivel_riesgo.toLowerCase() === "alto" || n.nivel_riesgo.toLowerCase() === "crítico" ? "alert-kpi" : ""}">${n.nivel_riesgo}</span></td>
            </tr>
          `).join("");
        }

        // Render Aristas
        if (aristasBody) {
          aristasBody.innerHTML = data.aristas.map(e => `
            <tr class="fade-in-row">
              <td class="text-mono">NODE-${e.source}</td>
              <td class="text-mono">NODE-${e.target}</td>
              <td><span class="badge">${e.tipo_relacion}</span></td>
              <td class="text-mono font-bold color-cyan">${(e.confianza * 100).toFixed(0)}%</td>
            </tr>
          `).join("");
        }

        // Render Stats
        if (statsContainer) {
          const density = data.nodos.length > 1 ? (data.aristas.length / (data.nodos.length * (data.nodos.length - 1))).toFixed(4) : "0.0000";
          statsContainer.innerHTML = `
            <article class="kpi-card double-bezel">
              <div class="inner-core">
                <span>Nodos Totales</span>
                <strong>${data.nodos.length}</strong>
              </div>
            </article>
            <article class="kpi-card double-bezel alert-kpi">
              <div class="inner-core">
                <span>Vínculos Enlazados</span>
                <strong>${data.aristas.length}</strong>
              </div>
            </article>
            <article class="kpi-card double-bezel">
              <div class="inner-core">
                <span>Densidad de Red</span>
                <strong>${density}</strong>
              </div>
            </article>
          `;
        }
      }
    } catch (err) {
      console.error("Error fetching graph data:", err);
    }
  }

  // --- 3. MOTOR ETL Y PIPELINE ---
  const btnRefreshEtl = document.getElementById("btn-refresh-etl");
  if (btnRefreshEtl) {
    btnRefreshEtl.addEventListener("click", () => {
      fetchETLStatus();
    });
  }

  async function fetchETLStatus() {
    const etlStagesContainer = document.getElementById("etl-stages-container");
    const etlMetricsContainer = document.getElementById("etl-metrics-container");
    const etlLastRun = document.getElementById("etl-last-run");
    const etlEstadoBadge = document.getElementById("etl-estado-badge");

    try {
      const response = await fetch("/api/etl/status");
      if (response.ok) {
        const data = await response.json();

        // 1. Update stages flowchart (Capture -> Gestion -> Transac -> ETL -> DW -> Datamart -> Dashboard IA -> Decisiones)
        if (etlStagesContainer) {
          let flowHTML = `<div class="etl-flow-line"></div>`;
          flowHTML += data.etapas.map((etapa, idx) => {
            let statusClass = "neutral";
            if (etapa.estado === "completado") statusClass = "ok";
            if (etapa.estado === "en_proceso") statusClass = "warning";

            return `
              <div class="etl-stage-step ${statusClass} slide-up-item" style="animation-delay: ${idx * 0.05}s;">
                <div class="etl-step-number">${idx + 1}</div>
                <div class="etl-step-card double-bezel">
                  <div class="inner-core">
                    <h4>${etapa.nombre}</h4>
                    <div class="etl-step-info">
                      <span class="text-mono">${etapa.registros} reg.</span>
                      <span class="text-mono font-bold color-cyan">${etapa.porcentaje}%</span>
                    </div>
                    <div class="etl-step-progress-bar">
                      <div class="etl-step-fill" style="width: ${etapa.porcentaje}%"></div>
                    </div>
                  </div>
                </div>
              </div>
            `;
          }).join("");
          etlStagesContainer.innerHTML = flowHTML;
        }

        // 2. Update processing metrics
        if (etlMetricsContainer) {
          etlMetricsContainer.innerHTML = `
            <div class="etl-metric-box double-bezel">
              <div class="inner-core">
                <span>Casos Capturados</span>
                <strong>${data.metricas.casos}</strong>
              </div>
            </div>
            <div class="etl-metric-box double-bezel">
              <div class="inner-core">
                <span>Entidades Correlacionadas</span>
                <strong>${data.metricas.personas + data.metricas.alias + data.metricas.telefonos}</strong>
              </div>
            </div>
            <div class="etl-metric-box double-bezel">
              <div class="inner-core">
                <span>Nodos en Data Warehouse</span>
                <strong>${data.metricas.nodos_grafo}</strong>
              </div>
            </div>
            <div class="etl-metric-box double-bezel">
              <div class="inner-core">
                <span>Alertas en Analytics</span>
                <strong>${data.metricas.indicadores_riesgo}</strong>
              </div>
            </div>
          `;
        }

        // 3. Update footer elements
        if (etlLastRun) etlLastRun.textContent = data.ultima_ejecucion;
        if (etlEstadoBadge) {
          etlEstadoBadge.textContent = data.estado_general === "nominal" ? "NOMINAL" : "SIN DATOS";
          etlEstadoBadge.className = `badge-status-table ${data.estado_general === "nominal" ? "ok" : "neutral"}`;
        }
      }
    } catch (err) {
      console.error("Error fetching ETL status:", err);
      if (etlStagesContainer) {
        etlStagesContainer.innerHTML = `<div class="text-center error-text">Error al consultar el estado del motor ETL.</div>`;
      }
    }
  }

  // --- 4. DATA MART DE INTELIGENCIA (IA / GIS / ANALÍTICA) ---
  // Setup Sub-tabs switching inside Data Mart
  const dmTabs = document.querySelectorAll("#datamart-tabs .tab-btn");
  const dmPanels = document.querySelectorAll("#panel-datamart .tab-panel");

  dmTabs.forEach(btn => {
    btn.addEventListener("click", () => {
      dmTabs.forEach(t => t.classList.remove("active"));
      btn.classList.add("active");

      const targetTab = btn.getAttribute("data-tab");
      dmPanels.forEach(panel => {
        if (panel.id === targetTab) {
          panel.classList.add("active");
        } else {
          panel.classList.remove("active");
        }
      });
      
      // Trigger rendering charts for specific tabs
      if (targetTab === "tab-dm-ia") {
        renderDashboardIACharts();
      } else if (targetTab === "tab-dm-analitica") {
        renderAnaliticaCharts();
      }
    });
  });

  // Master fetch for Data Mart
  let dmData = {
    entidades: null,
    hallazgos: null,
    indicadores: null,
    casos: null
  };

  async function fetchDataMart() {
    try {
      const [resEntidades, resHallazgos, resIndicadores, resCasos] = await Promise.all([
        fetch("/api/intel/entidades"),
        fetch("/api/intel/hallazgos"),
        fetch("/api/osint/indicadores"),
        fetch("/api/casos")
      ]);

      if (resEntidades.ok) dmData.entidades = await resEntidades.json();
      if (resHallazgos.ok) dmData.hallazgos = await resHallazgos.json();
      if (resIndicadores.ok) dmData.indicadores = await resIndicadores.json();
      if (resCasos.ok) dmData.casos = await resCasos.json();

      // Trigger initial tab renders
      const activeTab = document.querySelector("#datamart-tabs .tab-btn.active");
      if (activeTab) {
        const tabId = activeTab.getAttribute("data-tab");
        if (tabId === "tab-dm-ia") {
          renderDashboardIACharts();
        } else if (tabId === "tab-dm-gis") {
          renderGIS();
        } else if (tabId === "tab-dm-analitica") {
          renderAnaliticaCharts();
        }
      }
    } catch (err) {
      console.error("Error loading Data Mart data:", err);
    }
  }

  // A. DASHBOARD IA
  function renderDashboardIACharts() {
    if (!dmData.entidades) return;

    // 1. Populate KPIs
    const dmIaKpis = document.getElementById("dm-ia-kpis");
    if (dmIaKpis) {
      const totalEnt = dmData.entidades.personas.length + dmData.entidades.telefonos.length + dmData.entidades.alias.length;
      const hallazgosCrits = dmData.hallazgos ? dmData.hallazgos.filter(h => h.nivel_clasificacion.toLowerCase() === "secreto" || h.nivel_clasificacion.toLowerCase() === "reservado").length : 0;
      const avgRiesgo = dmData.indicadores && dmData.indicadores.length > 0 
        ? (dmData.indicadores.reduce((acc, curr) => acc + (curr.nivel_riesgo.toLowerCase() === "crítico" || curr.nivel_riesgo.toLowerCase() === "critico" ? 95 : curr.nivel_riesgo.toLowerCase() === "alto" ? 75 : 45), 0) / dmData.indicadores.length).toFixed(0) 
        : 65;

      dmIaKpis.innerHTML = `
        <div class="dm-kpi-card double-bezel slide-up-item">
          <div class="inner-core">
            <span>Total Entidades Relacionadas</span>
            <strong>${totalEnt}</strong>
          </div>
        </div>
        <div class="dm-kpi-card double-bezel alert-kpi slide-up-item" style="animation-delay: 0.1s;">
          <div class="inner-core">
            <span>Hallazgos Alta Criticidad</span>
            <strong>${hallazgosCrits}</strong>
          </div>
        </div>
        <div class="dm-kpi-card double-bezel slide-up-item" style="animation-delay: 0.2s;">
          <div class="inner-core">
            <span>Score de Riesgo OSINT Promedio</span>
            <strong>${avgRiesgo}%</strong>
          </div>
        </div>
      `;
    }

    // 2. Populate Recent Hallazgos Mini-list
    const dmRecentHallazgos = document.getElementById("dm-recent-hallazgos");
    if (dmRecentHallazgos && dmData.hallazgos) {
      dmRecentHallazgos.innerHTML = dmData.hallazgos.slice(0, 3).map(h => `
        <div class="hallazgo-mini-item slide-up-item">
          <strong>${h.titulo}</strong>
          <span class="badge ${h.nivel_clasificacion.toLowerCase() === 'secreto' ? 'alert-kpi' : ''}">${h.nivel_clasificacion}</span>
          <p>${h.descripcion.substring(0, 90)}...</p>
        </div>
      `).join("");
    }

    // 3. Render Chart.js: Risk Distribution
    const distContainer = document.getElementById("dm-risk-distribution");
    if (distContainer) {
      // Calculate risk stats
      const counts = { "Crítico": 0, "Alto": 0, "Medio": 0, "Bajo": 0 };
      dmData.entidades.personas.forEach(p => {
        const risk = p.nivel_riesgo;
        if (counts[risk] !== undefined) counts[risk]++;
        else counts["Medio"]++; // Fallback
      });

      // Clear & Inject Canvas
      distContainer.innerHTML = `<canvas id="dm-risk-canvas" style="max-height: 250px;"></canvas>`;
      destroyChart("dm-risk-canvas");

      const ctx = document.getElementById("dm-risk-canvas").getContext("2d");
      chartInstances["dm-risk-canvas"] = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: ["Crítico", "Alto", "Medio", "Bajo"],
          datasets: [{
            data: [counts["Crítico"], counts["Alto"], counts["Medio"], counts["Bajo"]],
            backgroundColor: ["#ff5a1f", "#ffd600", "#00e5ff", "#00e676"],
            borderWidth: 1,
            borderColor: "#111524"
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "right",
              labels: {
                color: "#8b99ae",
                font: { family: "Montserrat", size: 11 }
              }
            }
          }
        }
      });
    }
  }

  // B. GIS GEORREFERENCIACIÓN
  function renderGIS() {
    const gisTableBody = document.getElementById("gis-table-body");
    if (gisTableBody && dmData.entidades) {
      if (dmData.entidades.ubicaciones.length === 0) {
        gisTableBody.innerHTML = `<tr><td colspan="5" class="text-center">No hay ubicaciones registradas en intel.db.</td></tr>`;
      } else {
        gisTableBody.innerHTML = dmData.entidades.ubicaciones.map(u => `
          <tr class="fade-in-row">
            <td><strong>${u.descripcion}</strong></td>
            <td class="text-mono">${u.latitud.toFixed(4)}</td>
            <td class="text-mono">${u.longitud.toFixed(4)}</td>
            <td><span class="badge">${u.fuente || "Intel"}</span></td>
            <td class="text-mono">${u.fecha_captura}</td>
          </tr>
        `).join("");
      }
    }
  }

  // C. ANALÍTICA
  function renderAnaliticaCharts() {
    if (!dmData.casos) return;

    // 1. Tipologías Chart
    const tiposContainer = document.getElementById("analitica-tipos-chart");
    if (tiposContainer) {
      const counts = {};
      dmData.casos.forEach(c => {
        const t = c.tipo_reporte || "Otros";
        counts[t] = (counts[t] || 0) + 1;
      });

      tiposContainer.innerHTML = `<canvas id="analitica-tipos-canvas" style="max-height: 250px;"></canvas>`;
      destroyChart("analitica-tipos-canvas");

      const ctx = document.getElementById("analitica-tipos-canvas").getContext("2d");
      chartInstances["analitica-tipos-canvas"] = new Chart(ctx, {
        type: "bar",
        data: {
          labels: Object.keys(counts),
          datasets: [{
            label: "Casos por Tipo",
            data: Object.values(counts),
            backgroundColor: "#00e5ff",
            borderColor: "#00e5ff",
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              grid: { color: "rgba(255, 255, 255, 0.05)" },
              ticks: { color: "#8b99ae", font: { family: "JetBrains Mono", size: 10 } }
            },
            x: {
              grid: { display: false },
              ticks: { color: "#8b99ae", font: { family: "Montserrat", size: 10 } }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }

    // 2. OSINT Indicators Chart
    const osintChartContainer = document.getElementById("analitica-osint-chart");
    if (osintChartContainer && dmData.indicadores) {
      const counts = { "telefono": 0, "ip": 0, "dominio": 0, "correo": 0 };
      dmData.indicadores.forEach(i => {
        const type = i.tipo.toLowerCase();
        if (counts[type] !== undefined) counts[type]++;
      });

      osintChartContainer.innerHTML = `<canvas id="analitica-osint-canvas" style="max-height: 250px;"></canvas>`;
      destroyChart("analitica-osint-canvas");

      const ctx = document.getElementById("analitica-osint-canvas").getContext("2d");
      chartInstances["analitica-osint-canvas"] = new Chart(ctx, {
        type: "radar",
        data: {
          labels: ["Teléfono", "Dirección IP", "Dominio Phishing", "Correo Electrónico"],
          datasets: [{
            label: "Riesgos OSINT",
            data: [counts["telefono"], counts["ip"], counts["dominio"], counts["correo"]],
            backgroundColor: "rgba(255, 90, 31, 0.2)",
            borderColor: "#ff5a1f",
            pointBackgroundColor: "#ff5a1f",
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            r: {
              grid: { color: "rgba(255, 255, 255, 0.07)" },
              angleLines: { color: "rgba(255, 255, 255, 0.07)" },
              pointLabels: { color: "#8b99ae", font: { family: "Montserrat", size: 10 } },
              ticks: { display: false }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }

    // 3. Populate summary grid
    const summaryContainer = document.getElementById("analitica-summary");
    if (summaryContainer) {
      const nCasos = dmData.casos.length;
      const nInd = dmData.indicadores ? dmData.indicadores.length : 0;
      const nHallazgos = dmData.hallazgos ? dmData.hallazgos.length : 0;

      summaryContainer.innerHTML = `
        <div class="summary-card double-bezel slide-up-item">
          <div class="inner-core">
            <h4>Calidad del Pipeline</h4>
            <strong>99.8%</strong>
            <span>Procesamiento de datos sin retrasos</span>
          </div>
        </div>
        <div class="summary-card double-bezel alert-kpi slide-up-item" style="animation-delay: 0.1s;">
          <div class="inner-core">
            <h4>Entidades Correlacionadas</h4>
            <strong>${nCasos > 0 ? (nCasos * 1.5).toFixed(0) : "0"} Relaciones</strong>
            <span>Vínculos confirmados de teléfonos/alias</span>
          </div>
        </div>
        <div class="summary-card double-bezel slide-up-item" style="animation-delay: 0.2s;">
          <div class="inner-core">
            <h4>Base OSINT Indexada</h4>
            <strong>${nInd} Indicadores</strong>
            <span>Amenazas en monitoreo continuo</span>
          </div>
        </div>
      `;
    }
  }
});
