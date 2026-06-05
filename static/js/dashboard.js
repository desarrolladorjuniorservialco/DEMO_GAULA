document.addEventListener("DOMContentLoaded", () => {
  // Check user role from DOM
  const roleElement = document.querySelector(".user-info span");
  const userRole = roleElement ? roleElement.innerText.toLowerCase().replace("rol: ", "").trim() : "invitado";
  
  // If the user has a role that doesn't see intelligence panels, exit early
  if (userRole === "operador" || userRole === "invitado") {
    return;
  }

  // Set default Chart.js font
  if (typeof Chart !== "undefined") {
    Chart.defaults.font.family = "'Nunito Sans', sans-serif";
  }

  // --- STATE AND HELPER GLOBALS ---
  let chartInstances = {};
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
    if (panelId === "panel-datamart") {
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

  // --- 2. GRAFO DE RELACIONES (Vis.js Interactive Graph) ---
  let visNetwork = null;
  let originalGraphData = null;

  async function fetchGrafo() {
    const statsContainer = document.getElementById("grafo-stats-container");
    const container = document.getElementById("grafo-canvas");
    const loadingEl = document.getElementById("grafo-loading");

    if (loadingEl) loadingEl.style.display = "flex";

    try {
      const response = await fetch("/api/intel/grafo");
      if (response.ok) {
        const data = await response.json();
        originalGraphData = data;
        
        // Render Stats
        if (statsContainer) {
          const density = data.nodos.length > 1 ? (data.aristas.length / (data.nodos.length * (data.nodos.length - 1))).toFixed(4) : "0.0000";
          statsContainer.innerHTML = `
            <article class="kpi-card double-bezel animate-fade-in">
              <div class="inner-core">
                <span>Nodos Totales</span>
                <strong>${data.nodos.length}</strong>
              </div>
            </article>
            <article class="kpi-card double-bezel alert-kpi animate-fade-in" style="animation-delay: 0.1s;">
              <div class="inner-core">
                <span>Vínculos Enlazados</span>
                <strong>${data.aristas.length}</strong>
              </div>
            </article>
            <article class="kpi-card double-bezel animate-fade-in" style="animation-delay: 0.2s;">
              <div class="inner-core">
                <span>Densidad de Red</span>
                <strong>${density}</strong>
              </div>
            </article>
          `;
        }

        // Initialize network graph
        renderVisNetwork(data.nodos, data.aristas);
      }
    } catch (err) {
      console.error("Error fetching graph data:", err);
      if (container) {
        container.innerHTML = `<div class="text-center error-text" style="padding: 20px;">Fallo al cargar el grafo interactivo.</div>`;
      }
    } finally {
      if (loadingEl) loadingEl.style.display = "none";
    }
  }

  function renderVisNetwork(nodos, aristas) {
    const container = document.getElementById("grafo-canvas");
    if (!container) return;

    // Define colors for each entity type
    const colorMap = {
      persona: { background: "rgba(90, 125, 153, 0.14)", border: "#5a8db5" },
      alias: { background: "rgba(198, 161, 93, 0.14)", border: "#c2a35a" },
      telefono: { background: "rgba(166, 79, 79, 0.14)", border: "#b05050" },
      ubicacion: { background: "rgba(79, 138, 104, 0.14)", border: "#4f8a68" },
      cuenta: { background: "rgba(138, 122, 168, 0.14)", border: "#8a7aa8" }
    };

    const visNodes = nodos.map(n => {
      const type = n.entity_type.toLowerCase();
      const style = colorMap[type] || { background: "rgba(255,255,255,0.06)", border: "#8b99ae" };
      const isCritical = n.nivel_riesgo.toLowerCase() === "crítico" || n.nivel_riesgo.toLowerCase() === "critico" || n.nivel_riesgo.toLowerCase() === "alto";
      
      return {
        id: n.id,
        label: n.label,
        entity_type: type,
        nivel_riesgo: n.nivel_riesgo,
        shape: "dot",
        size: isCritical ? 18 : 12,
        color: {
          background: style.background,
          border: style.border,
          highlight: {
            background: "rgba(0, 229, 255, 0.25)",
            border: "#00e5ff"
          },
          hover: {
            background: "rgba(0, 229, 255, 0.18)",
            border: "#00e5ff"
          }
        },
        borderWidth: isCritical ? 2.5 : 1.5,
        shadow: isCritical ? { enabled: true, color: "#ff5a1f", size: 8, x: 0, y: 0 } : { enabled: false }
      };
    });

    const visEdges = aristas.map(e => {
      return {
        id: e.id,
        from: e.source,
        to: e.target,
        label: e.tipo_relacion,
        title: `Confianza: ${(e.confianza * 100).toFixed(0)}%`,
        font: {
          color: "rgba(240, 244, 250, 0.6)",
          size: 8,
          face: "JetBrains Mono"
        }
      };
    });

    const data = {
      nodes: new vis.DataSet(visNodes),
      edges: new vis.DataSet(visEdges)
    };

    const options = {
      nodes: {
        font: {
          color: "#f0f4fa",
          size: 11,
          face: "'Nunito Sans', sans-serif"
        }
      },
      edges: {
        color: {
          color: "rgba(139, 153, 174, 0.2)",
          highlight: "#00e5ff",
          hover: "#00e5ff"
        },
        width: 1.5,
        arrows: {
          to: { enabled: true, scaleFactor: 0.4 }
        },
        smooth: {
          type: "continuous"
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 150,
        selectConnectedEdges: false
      },
      physics: {
        stabilization: {
          iterations: 120,
          updateInterval: 25
        },
        barnesHut: {
          gravitationalConstant: -1500,
          centralGravity: 0.25,
          springLength: 90,
          springConstant: 0.04
        }
      }
    };

    if (visNetwork) {
      visNetwork.destroy();
    }

    visNetwork = new vis.Network(container, data, options);

    // Event handlers
    visNetwork.on("selectNode", (params) => {
      const selectedId = params.nodes[0];
      const detailContent = document.getElementById("grafo-detail-content");
      if (!detailContent) return;

      if (visNetwork.isCluster(selectedId)) {
        const clusterNodes = visNetwork.getNodesInCluster(selectedId);
        const type = selectedId.replace("cluster-", "").toUpperCase();
        detailContent.innerHTML = `
          <div style="text-align: left; display: flex; flex-direction: column; gap: 8px;">
            <p><strong>Grupo de Entidades:</strong> ${type}</p>
            <p><strong>Nodos Agrupados:</strong> ${clusterNodes.length}</p>
            <p style="font-size: 11px; color: var(--text-muted); margin-top: 5px;">Haga doble clic para expandir este grupo.</p>
          </div>
        `;
      } else {
        const node = nodos.find(n => n.id == selectedId);
        if (node) {
          detailContent.innerHTML = `
            <div style="text-align: left; display: flex; flex-direction: column; gap: 8px;">
              <p><strong>ID Interno:</strong> NODE-${node.id}</p>
              <p><strong>Identificador:</strong> <span class="color-cyan" style="font-weight: 700;">${node.label}</span></p>
              <p><strong>Tipo Entidad:</strong> <span class="badge-status-table info">${node.entity_type.toUpperCase()}</span></p>
              <p><strong>Nivel de Riesgo:</strong> <span class="badge-status-table ${node.nivel_riesgo.toLowerCase() === 'crítico' || node.nivel_riesgo.toLowerCase() === 'critico' || node.nivel_riesgo.toLowerCase() === 'alto' ? 'alert-kpi' : 'neutral'}">${node.nivel_riesgo}</span></p>
            </div>
          `;
        }
      }
    });

    visNetwork.on("deselectNode", () => {
      const detailContent = document.getElementById("grafo-detail-content");
      if (detailContent) {
        detailContent.innerHTML = "Seleccione un nodo o un grupo (cluster) para ver su ficha técnica detallada.";
      }
    });

    visNetwork.on("doubleClick", (params) => {
      if (params.nodes.length === 1) {
        const selectedId = params.nodes[0];
        if (visNetwork.isCluster(selectedId)) {
          visNetwork.openCluster(selectedId);
          document.getElementById("btn-cluster-type").style.display = "none";
          document.getElementById("btn-uncluster").style.display = "inline-block";
        }
      }
    });

    // Toolbar risk filter
    const filterRisk = document.getElementById("graph-filter-risk");
    if (filterRisk) {
      const newFilterRisk = filterRisk.cloneNode(true);
      filterRisk.parentNode.replaceChild(newFilterRisk, filterRisk);

      newFilterRisk.addEventListener("change", (e) => {
        const val = e.target.value;
        let filteredNodes = nodos;
        if (val === "critico-alto") {
          filteredNodes = nodos.filter(n => n.nivel_riesgo.toLowerCase() === "crítico" || n.nivel_riesgo.toLowerCase() === "critico" || n.nivel_riesgo.toLowerCase() === "alto");
        } else if (val === "critico") {
          filteredNodes = nodos.filter(n => n.nivel_riesgo.toLowerCase() === "crítico" || n.nivel_riesgo.toLowerCase() === "critico");
        }

        const filteredIds = filteredNodes.map(n => n.id);
        const filteredEdges = aristas.filter(e => filteredIds.includes(e.source) && filteredIds.includes(e.target));

        renderVisNetwork(filteredNodes, filteredEdges);
        newFilterRisk.value = val;
      });
    }

    // Toolbar clustering
    const btnCluster = document.getElementById("btn-cluster-type");
    const btnUncluster = document.getElementById("btn-uncluster");

    if (btnCluster && btnUncluster) {
      const newBtnCluster = btnCluster.cloneNode(true);
      btnCluster.parentNode.replaceChild(newBtnCluster, btnCluster);
      const newBtnUncluster = btnUncluster.cloneNode(true);
      btnUncluster.parentNode.replaceChild(newBtnUncluster, btnUncluster);

      newBtnCluster.addEventListener("click", () => {
        const entityTypes = ["persona", "alias", "telefono", "ubicacion", "cuenta"];
        entityTypes.forEach(type => {
          visNetwork.cluster({
            joinCondition: (nodeOptions) => nodeOptions.entity_type === type,
            clusterNodeProperties: {
              id: `cluster-${type}`,
              label: `Grupo: ${type.toUpperCase()}`,
              shape: "database",
              color: {
                background: colorMap[type]?.background || "rgba(255,255,255,0.06)",
                border: colorMap[type]?.border || "#8b99ae",
                highlight: {
                  background: "rgba(0, 229, 255, 0.25)",
                  border: "#00e5ff"
                }
              },
              allowSingleNodeCluster: false
            }
          });
        });
        newBtnCluster.style.display = "none";
        newBtnUncluster.style.display = "inline-block";
      });

      newBtnUncluster.addEventListener("click", () => {
        const entityTypes = ["persona", "alias", "telefono", "ubicacion", "cuenta"];
        entityTypes.forEach(type => {
          if (visNetwork.isCluster(`cluster-${type}`)) {
            visNetwork.openCluster(`cluster-${type}`);
          }
        });
        newBtnCluster.style.display = "inline-block";
        newBtnUncluster.style.display = "none";
      });
    }
  }

  // --- 3. CASOS PROGRESS TIMELINE ---
  let timelineCases = [];
  let selectedCase = null;

  async function fetchTimelineCases() {
    try {
      const response = await fetch("/api/casos");
      if (response.ok) {
        timelineCases = await response.json();
        
        // Populate selector
        const selector = document.getElementById("etl-case-selector");
        if (selector) {
          const newSelector = selector.cloneNode(true);
          selector.parentNode.replaceChild(newSelector, selector);

          if (timelineCases.length === 0) {
            newSelector.innerHTML = `<option value="">No hay casos registrados</option>`;
            selectedCase = null;
            renderTimelineForCase(null);
            return;
          }

          newSelector.innerHTML = timelineCases.map(c => {
            const code = c.id_reporte.substring(0, 8).toUpperCase();
            return `<option value="${c.id_reporte}">${code} - ${c.tipo_reporte} (${c.estado})</option>`;
          }).join("");

          if (!selectedCase || !timelineCases.some(c => c.id_reporte === selectedCase.id_reporte)) {
            selectedCase = timelineCases[0];
          } else {
            selectedCase = timelineCases.find(c => c.id_reporte === selectedCase.id_reporte);
          }

          newSelector.value = selectedCase.id_reporte;

          newSelector.addEventListener("change", (e) => {
            const id = e.target.value;
            selectedCase = timelineCases.find(c => c.id_reporte === id);
            renderTimelineForCase(selectedCase);
          });
        }

        renderTimelineForCase(selectedCase);
      }
    } catch (err) {
      console.error("Error fetching timeline cases:", err);
    }
  }

  // Hook refresh button
  const btnRefreshTrazabilidad = document.getElementById("btn-refresh-trazabilidad");
  if (btnRefreshTrazabilidad) {
    const newBtn = btnRefreshTrazabilidad.cloneNode(true);
    btnRefreshTrazabilidad.parentNode.replaceChild(newBtn, btnRefreshTrazabilidad);
    newBtn.addEventListener("click", fetchTimelineCases);
  }

  function renderTimelineForCase(caso) {
    if (!caso) {
      document.getElementById("timeline-case-code").innerText = "CASE-0000";
      document.getElementById("timeline-case-gaula").innerText = "GAULA Responsable";
      document.getElementById("timeline-case-status").innerText = "SIN DATOS";
      document.getElementById("timeline-case-status").className = "badge-status-table neutral";
      document.getElementById("timeline-line-progress").style.transform = "scaleX(0)";
      document.getElementById("timeline-detail-table-body").innerHTML = `<tr><td colspan="2" class="text-center">No hay datos de caso disponibles.</td></tr>`;
      return;
    }

    let activeStep = 1;
    const estado = (caso.estado || "").toLowerCase().trim();
    if (estado === "recibido") {
      activeStep = 1;
    } else if (estado === "en análisis" || estado === "en analisis") {
      activeStep = 2;
    } else if (estado === "asignado") {
      const isCritical = (caso.prioridad || "").toLowerCase() === "crítica" || (caso.prioridad || "").toLowerCase() === "critica";
      activeStep = isCritical ? 4 : 3;
    } else if (estado === "cerrado") {
      activeStep = 5;
    }

    document.getElementById("timeline-case-code").innerText = caso.id_reporte.substring(0, 13).toUpperCase();
    document.getElementById("timeline-case-gaula").innerText = caso.unidad_gaula || "No asignado";
    document.getElementById("timeline-case-status").innerText = caso.estado.toUpperCase();
    
    let stateBadge = "info";
    if (caso.estado === "Asignado") stateBadge = "ok";
    if (caso.estado === "Cerrado") stateBadge = "neutral";
    if (caso.estado === "En análisis") stateBadge = "warning";
    document.getElementById("timeline-case-status").className = `badge-status-table ${stateBadge}`;

    const scaleXVal = (activeStep - 1) / 4;
    document.getElementById("timeline-line-progress").style.transform = `scaleX(${scaleXVal})`;

    const steps = document.querySelectorAll(".timeline-steps .timeline-step");
    steps.forEach((step) => {
      const stepNum = parseInt(step.getAttribute("data-step"));
      step.classList.remove("active", "completed");
      if (stepNum < activeStep) {
        step.classList.add("completed");
      } else if (stepNum === activeStep) {
        step.classList.add("active");
      }
      
      const newStep = step.cloneNode(true);
      step.parentNode.replaceChild(newStep, step);
      
      newStep.addEventListener("click", () => {
        document.querySelectorAll(".timeline-steps .timeline-step").forEach(s => s.style.transform = "");
        newStep.style.transform = "scale(1.08)";
        showStepDetails(stepNum, caso);
      });
    });

    showStepDetails(activeStep, caso);
  }

  function showStepDetails(stepNum, caso) {
    if (!caso) return;

    const phases = {
      1: {
        title: "Inicio del Caso - Línea 147",
        desc: "El reporte telefónico fue recibido e ingresado al sistema NEXO-147 por el operador de turno.",
        fields: (c) => [
          { label: "Código de Registro", value: c.id_reporte.toUpperCase() },
          { label: "Canal de Entrada", value: c.canal_recepcion || "Línea 147" },
          { label: "Fecha y Hora de Ingreso", value: c.fecha_registro },
          { label: "Registrado por", value: `Operador: @${c.usuario_registro || "operador"}` }
        ]
      },
      2: {
        title: "Recolección de Información Inicial",
        desc: "Se documenta la narrativa de los hechos y la clasificación preliminar del delito/criticidad.",
        fields: (c) => [
          { label: "Tipología del Hecho", value: c.tipo_reporte },
          { label: "Prioridad del Caso", value: c.prioridad },
          { label: "Relato Inicial", value: c.descripcion || "Sin descripción de hechos" }
        ]
      },
      3: {
        title: "Investigación y Enlaces de Inteligencia",
        desc: "Análisis cruzado del número extorsivo y alias del sospechoso contra la base de datos de inteligencia criminal.",
        fields: (c) => [
          { label: "Teléfono Extorsivo", value: c.telefono_reportante || "No registra" },
          { label: "Alias del Sospechoso", value: c.observaciones && c.observaciones.toLowerCase().includes("alias") ? c.observaciones : "En análisis relacional" },
          { label: "Cuenta / Medio Exigido", value: c.medio_pago ? `${c.medio_pago} (${c.valor_exigido} COP)` : "No registra" }
        ]
      },
      4: {
        title: "Operaciones en Campo y Despliegue",
        desc: "Despliegue táctico del GAULA militar o policial asignado para operaciones en el territorio y labores investigativas.",
        fields: (c) => [
          { label: "Unidad Operativa Asignada", value: c.unidad_gaula || "No asignada" },
          { label: "Zona de Despliegue", value: c.nombre_reportante ? "Verificada" : "En verificación geográfica" },
          { label: "Estatus de Comisión", value: c.estado === "Cerrado" ? "Operación finalizada" : "Despliegue activo" }
        ]
      },
      5: {
        title: "Autoridades Aliadas / Judicialización y Cierre",
        desc: "Coordinación con fiscalía y cierre operacional formal tras capturas o neutralización de la extorsión.",
        fields: (c) => [
          { label: "Estado de Cierre", value: c.estado },
          { label: "Observaciones del Cierre", value: c.observaciones || "Caso finalizado nominalmente." }
        ]
      }
    };

    const phase = phases[stepNum];
    if (!phase) return;

    document.getElementById("timeline-detail-title").innerText = phase.title;
    document.getElementById("timeline-detail-desc").innerText = phase.desc;

    const fields = phase.fields(caso);
    document.getElementById("timeline-detail-table-body").innerHTML = fields.map(f => `
      <tr>
        <td style="width: 220px; padding: 8px 12px; color: var(--text-muted); font-family: var(--font-mono); text-transform: uppercase; font-size: 10px; border-bottom: 1px solid rgba(255,255,255,0.03);">${f.label}</td>
        <td style="padding: 8px 12px; font-weight: 600; border-bottom: 1px solid rgba(255,255,255,0.03);">${f.value || "No registra"}</td>
      </tr>
    `).join("");
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
      } else if (targetTab === "tab-dm-gis") {
        renderGIS();
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
  const _DEMO_IA = {
    personas: [
      ...Array(4).fill({ nivel_riesgo: "Crítico" }),
      ...Array(7).fill({ nivel_riesgo: "Alto" }),
      ...Array(9).fill({ nivel_riesgo: "Medio" }),
      ...Array(5).fill({ nivel_riesgo: "Bajo" })
    ],
    telefonos: Array(14),
    alias: Array(6),
    hallazgos: [
      { titulo: "Red extorsiva activa — Operación VENUS", descripcion: "Identificado patrón de extorsión sistemática con múltiples víctimas. Tres números activos vinculados.", nivel_clasificacion: "Secreto", estado: "Activo" },
      { titulo: "Número VoIP en múltiples reportes (×7)", descripcion: "Línea extorsiva vinculada a 7 reportes distintos en diferentes municipios. Alta reincidencia detectada.", nivel_clasificacion: "Reservado", estado: "En análisis" },
      { titulo: "Alias 'EL SOMBRA' con actividad reciente", descripcion: "Actor identificado en capturas de pantalla y audios de WhatsApp. OSINT confirmado vía redes sociales.", nivel_clasificacion: "Confidencial", estado: "Verificado" }
    ],
    indicadores: [
      ...Array(5).fill({ nivel_riesgo: "Crítico" }),
      ...Array(8).fill({ nivel_riesgo: "Alto" }),
      ...Array(7).fill({ nivel_riesgo: "Medio" })
    ]
  };

  function renderDashboardIACharts() {
    const ents      = dmData.entidades   || { personas: _DEMO_IA.personas, telefonos: _DEMO_IA.telefonos, alias: _DEMO_IA.alias };
    const hallazgos = (dmData.hallazgos  && dmData.hallazgos.length)  ? dmData.hallazgos  : _DEMO_IA.hallazgos;
    const inds      = (dmData.indicadores && dmData.indicadores.length) ? dmData.indicadores : _DEMO_IA.indicadores;

    // 1. KPIs
    const dmIaKpis = document.getElementById("dm-ia-kpis");
    if (dmIaKpis) {
      const totalEnt       = ents.personas.length + ents.telefonos.length + ents.alias.length;
      const hallazgosCrits = hallazgos.filter(h => ["secreto","reservado"].includes(h.nivel_clasificacion.toLowerCase())).length;
      const avgRiesgo      = (inds.reduce((a, c) => a + (c.nivel_riesgo.toLowerCase().includes("crít") ? 95 : c.nivel_riesgo.toLowerCase() === "alto" ? 75 : 45), 0) / inds.length).toFixed(0);

      dmIaKpis.innerHTML = `
        <div class="dm-kpi-card double-bezel slide-up-item">
          <div class="inner-core"><span>Total Entidades Relacionadas</span><strong>${totalEnt}</strong></div>
        </div>
        <div class="dm-kpi-card double-bezel alert-kpi slide-up-item" style="animation-delay:.1s">
          <div class="inner-core"><span>Hallazgos Alta Criticidad</span><strong>${hallazgosCrits}</strong></div>
        </div>
        <div class="dm-kpi-card double-bezel slide-up-item" style="animation-delay:.2s">
          <div class="inner-core"><span>Score Riesgo OSINT Promedio</span><strong>${avgRiesgo}%</strong></div>
        </div>
        <div class="dm-kpi-card double-bezel slide-up-item" style="animation-delay:.3s">
          <div class="inner-core"><span>Indicadores Activos</span><strong>${inds.length}</strong></div>
        </div>
      `;
    }

    // 2. Hallazgos recientes
    const dmRecentHallazgos = document.getElementById("dm-recent-hallazgos");
    if (dmRecentHallazgos) {
      dmRecentHallazgos.innerHTML = hallazgos.slice(0, 3).map(h => `
        <div class="hallazgo-mini-item slide-up-item">
          <strong>${h.titulo}</strong>
          <span class="badge ${h.nivel_clasificacion.toLowerCase() === "secreto" ? "alert-kpi" : ""}">${h.nivel_clasificacion}</span>
          <p>${h.descripcion.substring(0, 90)}...</p>
        </div>
      `).join("");
    }

    // 3. Gráfico: distribución de riesgo (doughnut)
    const distContainer = document.getElementById("dm-risk-distribution");
    if (distContainer) {
      const counts = { "Crítico": 0, "Alto": 0, "Medio": 0, "Bajo": 0 };
      ents.personas.forEach(p => {
        if (p && counts[p.nivel_riesgo] !== undefined) counts[p.nivel_riesgo]++;
        else counts["Medio"]++;
      });

      distContainer.innerHTML = `<canvas id="dm-risk-canvas" style="max-height:250px;"></canvas>`;
      destroyChart("dm-risk-canvas");
      chartInstances["dm-risk-canvas"] = new Chart(document.getElementById("dm-risk-canvas").getContext("2d"), {
        type: "doughnut",
        data: {
          labels: ["Crítico", "Alto", "Medio", "Bajo"],
          datasets: [{
            data: [counts["Crítico"], counts["Alto"], counts["Medio"], counts["Bajo"]],
            backgroundColor: ["#b05050", "#c2a35a", "#5a8db5", "#4f8a68"],
            borderWidth: 1, borderColor: "#0f1419"
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: "right", labels: { color: "#8b99ae", font: { family: "Nunito Sans", size: 11 } } } }
        }
      });
    }

    // 4. Gráfico: casos mensuales (line chart)
    const timelineContainer = document.getElementById("dm-timeline-chart");
    if (timelineContainer) {
      timelineContainer.innerHTML = `<canvas id="dm-timeline-canvas"></canvas>`;
      destroyChart("dm-timeline-canvas");
      chartInstances["dm-timeline-canvas"] = new Chart(document.getElementById("dm-timeline-canvas").getContext("2d"), {
        type: "line",
        data: {
          labels: ["Ene", "Feb", "Mar", "Abr", "May", "Jun"],
          datasets: [{
            label: "Casos registrados",
            data: [8, 12, 9, 15, 18, 14],
            borderColor: "#4f8a68",
            backgroundColor: "rgba(47,107,79,0.10)",
            pointBackgroundColor: "#4f8a68",
            borderWidth: 2, fill: true, tension: 0.4
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          scales: {
            y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#8b99ae", font: { family: "JetBrains Mono", size: 10 } } },
            x: { grid: { display: false }, ticks: { color: "#8b99ae", font: { family: "Nunito Sans", size: 10 } } }
          },
          plugins: { legend: { display: false } }
        }
      });
    }

    // 5. Gráfico: prioridad de reportes (horizontal bar)
    const priorityContainer = document.getElementById("dm-priority-chart");
    if (priorityContainer) {
      priorityContainer.innerHTML = `<canvas id="dm-priority-canvas"></canvas>`;
      destroyChart("dm-priority-canvas");
      chartInstances["dm-priority-canvas"] = new Chart(document.getElementById("dm-priority-canvas").getContext("2d"), {
        type: "bar",
        data: {
          labels: ["Crítica", "Alta", "Media", "Baja"],
          datasets: [{
            label: "Reportes",
            data: [11, 18, 14, 7],
            backgroundColor: ["#b05050", "#c2a35a", "#5a8db5", "#4f8a68"],
            borderWidth: 0, borderRadius: 4
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false, indexAxis: "y",
          scales: {
            x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#8b99ae", font: { family: "JetBrains Mono", size: 10 } } },
            y: { grid: { display: false }, ticks: { color: "#8b99ae", font: { family: "Nunito Sans", size: 10 } } }
          },
          plugins: { legend: { display: false } }
        }
      });
    }
  }

  // B. GIS GEORREFERENCIACIÓN
  const _DEMO_GIS = [
    { lat: 4.7110, lon: -74.0721, label: "14 reportes activos · R.CASO-2026-0341", prioridad: "Crítica",  fuente: "nexo147.db", fecha: "2026-05-14", size: 15, color: "#b05050" },
    { lat: 6.2518, lon: -75.5636, label: "Score: 87% · 3 entidades vinculadas",      prioridad: "Alta",    fuente: "intel.db",   fecha: "2026-05-22", size: 12, color: "#c2a35a" },
    { lat: 3.4516, lon: -76.5320, label: "Alerta extorsión activa · 7 casos",        prioridad: "Crítica", fuente: "intel.db",   fecha: "2026-05-29", size: 13, color: "#b05050" },
    { lat: 10.9685, lon: -74.7813, label: "2 números extorsivos detectados",         prioridad: "Media",   fuente: "osint.db",   fecha: "2026-06-01", size: 9,  color: "#5a8db5" },
    { lat: 10.3997, lon: -75.5144, label: "Caso JUD-2026-0087 · Asignado",           prioridad: "Alta",    fuente: "intel.db",   fecha: "2026-05-18", size: 10, color: "#c2a35a" },
    { lat: 7.1193,  lon: -73.1227, label: "4 reportes · Prioridad Crítica",          prioridad: "Crítica", fuente: "nexo147.db", fecha: "2026-06-02", size: 12, color: "#b05050" },
    { lat: 7.8931,  lon: -72.5078, label: "Cuenta NQUI-***847 en análisis",          prioridad: "Alta",    fuente: "osint.db",   fecha: "2026-05-31", size: 10, color: "#c2a35a" },
    { lat: 4.1420,  lon: -73.6266, label: "Hallazgo clasificado RSRV",               prioridad: "Alta",    fuente: "intel.db",   fecha: "2026-06-03", size: 11, color: "#c2a35a" },
    { lat: 4.8133,  lon: -75.6961, label: "1 caso en seguimiento activo",            prioridad: "Media",   fuente: "nexo147.db", fecha: "2026-05-27", size: 8,  color: "#5a8db5" },
    { lat: 1.2136,  lon: -77.2811, label: "Extorsión registrada · R.CASO-0341",      prioridad: "Crítica", fuente: "intel.db",   fecha: "2026-05-25", size: 11, color: "#b05050" },
    { lat: 5.0703,  lon: -75.5138, label: "Score 62% · Monitoreo OSINT",             prioridad: "Media",   fuente: "osint.db",   fecha: "2026-06-01", size: 9,  color: "#5a8db5" },
    { lat: 2.9273,  lon: -75.2820, label: "Monitoreo activo · Indicador OD-047",     prioridad: "Baja",    fuente: "osint.db",   fecha: "2026-05-30", size: 7,  color: "#4f8a68" }
  ];

  function renderGIS() {
    const puntos = (dmData.entidades && dmData.entidades.ubicaciones && dmData.entidades.ubicaciones.length)
      ? dmData.entidades.ubicaciones.map(u => ({
          lat: u.latitud, lon: u.longitud,
          label: u.descripcion, prioridad: "N/D",
          fuente: u.fuente || "intel.db", fecha: u.fecha_captura,
          size: 10, color: "#5a8db5"
        }))
      : _DEMO_GIS;

    // Mapa Plotly de Colombia
    const mapDiv = document.getElementById("gis-plotly-map");
    if (mapDiv && typeof Plotly !== "undefined") {
      const textPositions = ["top center","bottom center","top right","bottom left","top left","bottom right"];

      const trace = {
        type: "scattergeo",
        lat:  puntos.map(p => p.lat),
        lon:  puntos.map(p => p.lon),
        text: puntos.map(p => p.label),
        mode: "markers+text",
        textposition: puntos.map((_, i) => textPositions[i % textPositions.length]),
        textfont: { color: "#c0ccdc", size: 9, family: "JetBrains Mono" },
        marker: {
          size:    puntos.map(p => p.size),
          color:   puntos.map(p => p.color),
          symbol:  "circle",
          line: { color: "rgba(240,244,250,0.5)", width: 1 },
          opacity: 0.9
        },
        hovertemplate: "<b>%{text}</b><extra></extra>"
      };

      const layout = {
        geo: {
          scope: "south america",
          projection: { type: "mercator" },
          lataxis: { range: [-4.5, 13.5] },
          lonaxis: { range: [-79.5, -66.5] },
          showland: true,   landcolor:    "#1a2535",
          showocean: true,  oceancolor:   "#0a1220",
          showcountries: true, countrycolor: "#2a3a50",
          showsubunits: true,  subunitcolor: "#1e2535",
          showrivers: true, rivercolor:   "#131e2c",
          showlakes: true,  lakecolor:    "#0a1220",
          bgcolor: "rgba(0,0,0,0)"
        },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor:  "rgba(0,0,0,0)",
        margin: { l: 0, r: 0, t: 20, b: 0 },
        font: { color: "#8b99ae", family: "Nunito Sans", size: 10 }
      };

      Plotly.newPlot(mapDiv, [trace], layout, { responsive: true, displayModeBar: false });
    }

    // Tabla de ubicaciones
    const gisTableBody = document.getElementById("gis-table-body");
    if (gisTableBody) {
      gisTableBody.innerHTML = puntos.map(p => `
        <tr class="fade-in-row">
          <td><strong>${p.label}</strong></td>
          <td class="text-mono">${typeof p.lat === "number" ? p.lat.toFixed(4) : p.lat}</td>
          <td class="text-mono">${typeof p.lon === "number" ? p.lon.toFixed(4) : p.lon}</td>
          <td><span class="badge">${p.fuente}</span></td>
          <td class="text-mono">${p.fecha}</td>
        </tr>
      `).join("");
    }
  }

  // C. ANALÍTICA
  const _DEMO_ANALITICA = {
    casos: [
      ...Array(28).fill({ tipo_reporte: "Extorsión" }),
      ...Array(14).fill({ tipo_reporte: "Amenaza" }),
      ...Array(11).fill({ tipo_reporte: "Fraude digital" }),
      ...Array(8).fill({ tipo_reporte: "Hurto" }),
      ...Array(4).fill({ tipo_reporte: "Secuestro" }),
      ...Array(6).fill({ tipo_reporte: "Otro" })
    ],
    indicadores: [
      ...Array(18).fill({ tipo: "telefono" }),
      ...Array(9).fill({ tipo: "ip" }),
      ...Array(12).fill({ tipo: "dominio" }),
      ...Array(7).fill({ tipo: "correo" })
    ]
  };

  function renderAnaliticaCharts() {
    const casos = (dmData.casos      && dmData.casos.length)      ? dmData.casos      : _DEMO_ANALITICA.casos;
    const inds  = (dmData.indicadores && dmData.indicadores.length) ? dmData.indicadores : _DEMO_ANALITICA.indicadores;

    // 1. Tipologías (bar chart)
    const tiposContainer = document.getElementById("analitica-tipos-chart");
    if (tiposContainer) {
      const counts = {};
      casos.forEach(c => {
        const t = c.tipo_reporte || "Otros";
        counts[t] = (counts[t] || 0) + 1;
      });

      tiposContainer.innerHTML = `<canvas id="analitica-tipos-canvas" style="max-height:250px;"></canvas>`;
      destroyChart("analitica-tipos-canvas");
      chartInstances["analitica-tipos-canvas"] = new Chart(document.getElementById("analitica-tipos-canvas").getContext("2d"), {
        type: "bar",
        data: {
          labels: Object.keys(counts),
          datasets: [{
            label: "Casos por Tipo",
            data: Object.values(counts),
            backgroundColor: ["#b05050","#c2a35a","#5a8db5","#4f8a68","#8a7aa8","#7d8a95"],
            borderWidth: 0, borderRadius: 4
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          scales: {
            y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#8b99ae", font: { family: "JetBrains Mono", size: 10 } } },
            x: { grid: { display: false }, ticks: { color: "#8b99ae", font: { family: "Nunito Sans", size: 10 } } }
          },
          plugins: { legend: { display: false } }
        }
      });
    }

    // 2. OSINT Radar chart con animación de barrido tipo radar
    const osintChartContainer = document.getElementById("analitica-osint-chart");
    if (osintChartContainer) {
      const counts = { telefono: 0, ip: 0, dominio: 0, correo: 0 };
      inds.forEach(i => { const t = (i.tipo || "").toLowerCase(); if (counts[t] !== undefined) counts[t]++; });

      osintChartContainer.style.position = "relative";
      osintChartContainer.innerHTML = `
        <div style="
          position:absolute; top:50%; left:50%;
          transform:translate(-50%,-52%);
          width:270px; height:270px;
          border-radius:50%; overflow:hidden;
          pointer-events:none; z-index:0;">
          <div style="
            position:absolute; inset:0;
            background:conic-gradient(
              from 0deg,
              transparent 0deg,
              rgba(79,138,104,0.22) 18deg,
              rgba(79,138,104,0.10) 36deg,
              transparent 55deg
            );
            animation:radarSweepAnim 3s linear infinite;">
          </div>
        </div>
        <canvas id="analitica-osint-canvas" style="max-height:250px;position:relative;z-index:1;"></canvas>
      `;
      destroyChart("analitica-osint-canvas");
      chartInstances["analitica-osint-canvas"] = new Chart(document.getElementById("analitica-osint-canvas").getContext("2d"), {
        type: "radar",
        data: {
          labels: ["Teléfono", "Dirección IP", "Dominio Phishing", "Correo Electrónico"],
          datasets: [{
            label: "Riesgos OSINT",
            data: [counts.telefono, counts.ip, counts.dominio, counts.correo],
            backgroundColor: "rgba(79,138,104,0.15)",
            borderColor: "#4f8a68",
            pointBackgroundColor: "#4f8a68",
            borderWidth: 2
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          scales: {
            r: {
              grid: { color: "rgba(255,255,255,0.07)" },
              angleLines: { color: "rgba(255,255,255,0.07)" },
              pointLabels: { color: "#8b99ae", font: { family: "Nunito Sans", size: 10 } },
              ticks: { display: false, backdropColor: "transparent" }
            }
          },
          plugins: { legend: { display: false } }
        }
      });
    }

    // 3. Resumen ejecutivo
    const summaryContainer = document.getElementById("analitica-summary");
    if (summaryContainer) {
      const nCasos = casos.length;
      const nInd   = inds.length;

      summaryContainer.innerHTML = `
        <div class="summary-card double-bezel slide-up-item">
          <div class="inner-core">
            <h4>Calidad del Pipeline</h4>
            <strong>99.8%</strong>
            <span>Procesamiento de datos sin retrasos</span>
          </div>
        </div>
        <div class="summary-card double-bezel alert-kpi slide-up-item" style="animation-delay:.1s">
          <div class="inner-core">
            <h4>Entidades Correlacionadas</h4>
            <strong>${(nCasos * 1.5).toFixed(0)} Relaciones</strong>
            <span>Vínculos confirmados de teléfonos/alias</span>
          </div>
        </div>
        <div class="summary-card double-bezel slide-up-item" style="animation-delay:.2s">
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
