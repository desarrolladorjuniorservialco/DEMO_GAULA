document.addEventListener("DOMContentLoaded", () => {
  // --- ELEMENTOS DE DOM PRINCIPALES ---
  const sidebar = document.getElementById("sidebar");
  const sidebarToggleOpen = document.getElementById("sidebar-toggle-open");
  const sidebarToggleClose = document.getElementById("sidebar-toggle-close");
  const sidebarNav = document.getElementById("sidebar-nav");
  const currentPanelTitle = document.getElementById("current-panel-title");
  const systemTime = document.getElementById("system-time");
  
  // Vistas
  const panels = document.querySelectorAll(".panel-section");
  const navItems = document.querySelectorAll(".nav-item");

  // Inferencia de Rol
  const roleElement = document.querySelector(".user-info span");
  const userRole = roleElement ? roleElement.innerText.toLowerCase().replace("rol: ", "").trim() : "invitado";
  
  // --- RELOJ TÁCTICO EN TIEMPO REAL ---
  function updateTime() {
    const now = new Date();
    const timeString = now.toISOString().replace("T", " ").substring(0, 19) + " UTC";
    systemTime.textContent = timeString;
  }
  setInterval(updateTime, 1000);
  updateTime();

  // --- CONTROLES DEL SIDEBAR (RESPONSIVE) ---
  if (sidebarToggleOpen) {
    sidebarToggleOpen.addEventListener("click", () => {
      sidebar.classList.add("open");
    });
  }
  if (sidebarToggleClose) {
    sidebarToggleClose.addEventListener("click", () => {
      sidebar.classList.remove("open");
    });
  }

  // --- NAVEGACIÓN SPA ---
  navItems.forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const targetPanelId = item.getAttribute("data-panel");
      
      // Activar clase en menú
      navItems.forEach(i => i.classList.remove("active"));
      item.classList.add("active");

      // Mostrar Panel correspondiente
      panels.forEach(panel => {
        if (panel.id === targetPanelId) {
          panel.classList.add("active");
        } else {
          panel.classList.remove("active");
        }
      });

      // Actualizar título de topbar
      const panelName = item.querySelector("span").innerText;
      currentPanelTitle.textContent = panelName;

      // Cerrar sidebar en dispositivos móviles
      sidebar.classList.remove("open");

      // Cargar datos según el panel activo
      cargarDatosDelPanel(targetPanelId);
    });
  });

  // Cargar datos contextuales según la pestaña abierta
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

  // --- CONFIGURACIÓN DE ACCESOS DIRECTOS SEGÚN ROL ---
  const shortcutsContainer = document.getElementById("shortcuts-container");
  if (shortcutsContainer) {
    let shortcutsHTML = "";
    if (userRole === "operador") {
      shortcutsHTML = `
        <button class="shortcut-card double-bezel" data-target="panel-formulario">
          <div class="inner-core">
            <span class="icon"><i class="shortcut-icon" data-lucide="phone"></i></span>
            <strong>Nuevo Reporte 147</strong>
            <p>Registrar una llamada de extorsión activa</p>
          </div>
        </button>
        <button class="shortcut-card double-bezel" id="btn-shortcut-mis-reportes">
          <div class="inner-core">
            <span class="icon"><i class="shortcut-icon" data-lucide="folder"></i></span>
            <strong>Mis Reportes</strong>
            <p>Ver histórico de llamadas ingresadas por ti</p>
          </div>
        </button>
      `;
    } else if (userRole === "analista") {
      shortcutsHTML = `
        <button class="shortcut-card double-bezel" data-target="panel-casos">
          <div class="inner-core">
            <span class="icon"><i class="shortcut-icon" data-lucide="shield"></i></span>
            <strong>Bandeja de Casos</strong>
            <p>Analizar denuncias y cambiar su estado operativo</p>
          </div>
        </button>
        <button class="shortcut-card double-bezel" data-target="panel-entidades">
          <div class="inner-core">
            <span class="icon"><i class="shortcut-icon" data-lucide="search"></i></span>
            <strong>Buscador de Entidades</strong>
            <p>Explorar teléfonos, alias y vinculaciones cruzadas</p>
          </div>
        </button>
        <button class="shortcut-card double-bezel" data-target="panel-inteligencia">
          <div class="inner-core">
            <span class="icon"><i class="shortcut-icon" data-lucide="network"></i></span>
            <strong>Correlaciones y OSINT</strong>
            <p>Vincular celdas y auditar brechas externas</p>
          </div>
        </button>
      `;
    } else if (userRole === "director" || userRole === "admin") {
      shortcutsHTML = `
        <button class="shortcut-card double-bezel" data-target="panel-dashboard">
          <div class="inner-core">
            <span class="icon"><i class="shortcut-icon" data-lucide="bar-chart-2"></i></span>
            <strong>Centro de Mando</strong>
            <p>Monitorear KPIs, radar táctico y mapas de calor</p>
          </div>
        </button>
        <button class="shortcut-card double-bezel" data-target="panel-casos">
          <div class="inner-core">
            <span class="icon"><i class="shortcut-icon" data-lucide="folder-open"></i></span>
            <strong>Casos Recientes</strong>
            <p>Ver asignaciones operacionales activas</p>
          </div>
        </button>
        <button class="shortcut-card double-bezel" data-target="panel-inteligencia">
          <div class="inner-core">
            <span class="icon"><i class="shortcut-icon" data-lucide="globe"></i></span>
            <strong>OSINT e Inteligencia</strong>
            <p>Escanear brechas de seguridad externas</p>
          </div>
        </button>
      `;
    }
    
    shortcutsContainer.innerHTML = shortcutsHTML;
    if (typeof lucide !== "undefined") {
      lucide.createIcons();
    }

    // Asignar listeners a los accesos directos
    shortcutsContainer.querySelectorAll("button").forEach(btn => {
      btn.addEventListener("click", () => {
        if (btn.id === "btn-shortcut-mis-reportes") {
          const navCasos = document.querySelector('[data-panel="panel-casos"]');
          if (navCasos) navCasos.click();
        } else {
          const target = btn.getAttribute("data-target");
          const navItem = document.querySelector(`[data-panel="${target}"]`);
          if (navItem) navItem.click();
        }
      });
    });
  }

  // --- LOGS DE ACTIVIDAD MOCK EN VIVO ---
  const activityLogBody = document.getElementById("activity-log-body");
  const mockActivities = [
    { accion: "Ingreso Reporte", detalle: "Llamada 147 registrada desde Bogotá", operador: "operador", hora: "08:14" },
    { accion: "Asignación Caso", detalle: "Caso #247 reasignado a GAULA Medellín", operador: "analista", hora: "08:21" },
    { accion: "Actualización", detalle: "Número 3124567890 marcado como EXTORSIVO", operador: "analista", hora: "08:45" },
    { accion: "Análisis OSINT", detalle: "Escaneo de brechas de seguridad ejecutado", operador: "director", hora: "09:12" },
    { accion: "Consulta DB", detalle: "Búsqueda relacional para alias 'El Zarco'", operador: "analista", hora: "09:33" }
  ];

  function renderActivityLogs() {
    if (!activityLogBody) return;
    activityLogBody.innerHTML = mockActivities.map(act => `
      <tr>
        <td><span class="badge-status-table info">${act.accion}</span></td>
        <td>${act.detalle}</td>
        <td><code>${act.operador}</code></td>
        <td class="text-mono">${act.hora}</td>
      </tr>
    `).join("");
  }
  renderActivityLogs();

  // --- REGISTRO DE REPORTES ASÍNCRONO ---
  const btnEnviarReporte = document.getElementById("btn-enviar-reporte");
  const formRegistro = document.getElementById("formulario-registro-reporte");
  const feedbackReporte = document.getElementById("feedback-reporte-console");

  if (btnEnviarReporte && formRegistro) {
    btnEnviarReporte.addEventListener("click", async () => {
      // Validar campos requeridos
      const tipo = document.getElementById("tipo_reporte").value;
      const prioridad = document.getElementById("prioridad").value;
      const canal = document.getElementById("canal_recepcion").value;
      const gaula = document.getElementById("unidad_gaula").value;
      const descripcion = document.getElementById("descripcion").value;

      if (!tipo || !prioridad || !canal || !gaula || !descripcion) {
        mostrarFeedback("Por favor llene todos los campos obligatorios (*)", "error");
        return;
      }

      // Animación de envío
      btnEnviarReporte.disabled = true;
      btnEnviarReporte.classList.add("loading");
      btnEnviarReporte.querySelector("span").innerText = "Registrando...";

      // Recopilar datos del formulario
      const formData = new FormData(formRegistro);
      const dataJson = {};
      formData.forEach((val, key) => { dataJson[key] = val; });

      try {
        const response = await fetch("/registrar-reporte", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(dataJson)
        });

        const resData = await response.json();

        if (response.ok) {
          mostrarFeedback(resData.mensaje || "Reporte guardado correctamente en JSON.", "ok");
          formRegistro.reset();
          
          // Registrar en log local de actividad
          const now = new Date();
          const timeStr = now.toTimeString().substring(0, 5);
          mockActivities.unshift({
            accion: "Ingreso Reporte",
            detalle: `Reporte clasificado como ${tipo} guardado localmente`,
            operador: roleElement ? roleElement.innerText.split(":")[1].trim().toLowerCase() : "operador",
            hora: timeStr
          });
          renderActivityLogs();
          
          // Actualizar conteo de alertas críticas si corresponde
          if (prioridad === "Crítica") {
            triggerAlertPulse();
          }
        } else {
          mostrarFeedback(resData.error || "Ocurrió un error al procesar el reporte.", "error");
        }
      } catch (err) {
        console.error(err);
        mostrarFeedback("Error de comunicación con el servidor.", "error");
      } finally {
        btnEnviarReporte.disabled = false;
        btnEnviarReporte.classList.remove("loading");
        btnEnviarReporte.querySelector("span").innerText = "Registrar Caso";
      }
    });
  }

  function mostrarFeedback(msg, tipo) {
    if (!feedbackReporte) return;
    feedbackReporte.textContent = msg;
    feedbackReporte.className = `feedback-indicator ${tipo}`;
    feedbackReporte.classList.remove("hidden");
    setTimeout(() => {
      feedbackReporte.classList.add("hidden");
    }, 6000);
  }

  function triggerAlertPulse() {
    const indicator = document.getElementById("alert-indicator");
    const countVal = document.getElementById("alert-count-val");
    if (indicator && countVal) {
      let count = parseInt(countVal.innerText);
      count++;
      countVal.innerText = count;
      indicator.classList.add("pulse-alert-active");
      setTimeout(() => {
        indicator.classList.remove("pulse-alert-active");
      }, 3000);
    }
  }

  // --- BANDEJA DE CASOS: CARGA Y DETALLE ---
  let casosGlobales = [];
  const casesTableBody = document.getElementById("cases-table-body");
  const caseDetailPanel = document.getElementById("case-detail-panel");
  const btnCloseDetail = document.getElementById("btn-close-detail-panel");
  
  // Elementos del Panel de Detalles
  const detailCaseId = document.getElementById("detail-case-id");
  const detailCaseTipo = document.getElementById("detail-case-tipo");
  const detailCasePrioridad = document.getElementById("detail-case-prioridad");
  const detailCaseEstado = document.getElementById("detail-case-estado");
  const detailCaseGaula = document.getElementById("detail-case-gaula");
  const detailCaseTelefonoExt = document.getElementById("detail-case-telefono-ext");
  const detailCaseAlias = document.getElementById("detail-case-alias");
  const detailCaseMonto = document.getElementById("detail-case-monto");
  const detailCasePago = document.getElementById("detail-case-pago");
  const detailCaseDescripcion = document.getElementById("detail-case-descripcion");
  const selectDetailStatus = document.getElementById("detail-change-status");
  const btnSaveCaseStatus = document.getElementById("btn-save-case-status");

  let casoSeleccionadoId = null;

  async function fetchCasos() {
    if (!casesTableBody) return;
    casesTableBody.innerHTML = `<tr><td colspan="6" class="text-center">Consultando nodo de reportes...</td></tr>`;
    
    try {
      const response = await fetch("/api/dataset/casos");
      if (response.ok) {
        casosGlobales = await response.json();
        renderCasos(casosGlobales);
        actualizarKPIsDashboard(casosGlobales);
      } else {
        casesTableBody.innerHTML = `<tr><td colspan="6" class="text-center error-text">Error al consultar reportes.</td></tr>`;
      }
    } catch (err) {
      console.error(err);
      casesTableBody.innerHTML = `<tr><td colspan="6" class="text-center error-text">Fallo de conexión.</td></tr>`;
    }
  }

  function renderCasos(casos) {
    if (!casesTableBody) return;
    if (casos.length === 0) {
      casesTableBody.innerHTML = `<tr><td colspan="6" class="text-center">No hay reportes registrados en la base local.</td></tr>`;
      return;
    }

    casesTableBody.innerHTML = casos.map(c => {
      const shortId = c.id_reporte.substring(0, 7).toUpperCase();
      const pBadge = c.prioridad.toLowerCase() === "crítica" ? "alert-kpi" : "";
      
      let stateBadge = "info";
      if (c.estado === "Asignado") stateBadge = "ok";
      if (c.estado === "Cerrado") stateBadge = "neutral";
      if (c.estado === "En análisis") stateBadge = "warning";

      return `
        <tr data-id="${c.id_reporte}">
          <td>
            <strong>${shortId}</strong>
            <div class="date-sub-text">${c.fecha_registro}</div>
          </td>
          <td>${c.tipo_reporte}</td>
          <td><span class="badge ${pBadge}">${c.prioridad}</span></td>
          <td>${c.unidad_gaula || "No asignado"}</td>
          <td><span class="badge-status-table ${stateBadge}">${c.estado}</span></td>
          <td>
            <button class="btn btn-detail-action" onclick="window.verDetalleCaso('${c.id_reporte}')">Ver Ficha</button>
          </td>
        </tr>
      `;
    }).join("");
  }

  // Hacer ver detalle accesible globalmente
  window.verDetalleCaso = function(id) {
    const caso = casosGlobales.find(c => c.id_reporte === id);
    if (!caso) return;

    casoSeleccionadoId = id;
    
    detailCaseId.innerText = caso.id_reporte.substring(0, 13).toUpperCase() + "...";
    detailCaseTipo.innerText = caso.tipo_reporte;
    
    // Prioridad badge
    detailCasePrioridad.innerText = caso.prioridad;
    detailCasePrioridad.className = `badge ${caso.prioridad.toLowerCase() === "crítica" ? "alert-kpi" : ""}`;

    // Estado badge
    detailCaseEstado.innerText = caso.estado;
    let stateBadge = "info";
    if (caso.estado === "Asignado") stateBadge = "ok";
    if (caso.estado === "Cerrado") stateBadge = "neutral";
    if (caso.estado === "En análisis") stateBadge = "warning";
    detailCaseEstado.className = `badge-status-table ${stateBadge}`;

    detailCaseGaula.innerText = caso.unidad_gaula || "No asignado";
    detailCaseTelefonoExt.innerText = caso.numero_extorsivo || "No registra";
    detailCaseAlias.innerText = caso.alias_sospechoso || "No registra";
    detailCaseMonto.innerText = caso.valor_exigido ? `${caso.valor_exigido} COP` : "No registra";
    detailCasePago.innerText = caso.medio_pago || "No registra";
    detailCaseDescripcion.innerText = caso.descripcion || "Sin descripción de hechos.";

    selectDetailStatus.value = caso.estado;

    caseDetailPanel.classList.remove("hidden");

    if (btnSaveCaseStatus) {
      btnSaveCaseStatus.disabled = true;
      btnSaveCaseStatus.textContent = "Solo lectura (dataset demo)";
    }
  };

  if (btnCloseDetail) {
    btnCloseDetail.addEventListener("click", () => {
      caseDetailPanel.classList.add("hidden");
      casoSeleccionadoId = null;
    });
  }

  // Guardar cambio de estado
  if (btnSaveCaseStatus) {
    btnSaveCaseStatus.addEventListener("click", async () => {
      if (!casoSeleccionadoId) return;
      const nuevoEstado = selectDetailStatus.value;
      
      btnSaveCaseStatus.disabled = true;
      btnSaveCaseStatus.innerText = "Guardando...";

      try {
        const response = await fetch(`/api/casos/${casoSeleccionadoId}/estado`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ estado: nuevoEstado })
        });

        if (response.ok) {
          // Loggear en auditoría
          const now = new Date();
          const timeStr = now.toTimeString().substring(0, 5);
          mockActivities.unshift({
            accion: "Actualización",
            detalle: `Caso #${casoSeleccionadoId.substring(0,7).toUpperCase()} cambiado a ${nuevoEstado}`,
            operador: roleElement ? roleElement.innerText.split(":")[1].trim().toLowerCase() : "operador",
            hora: timeStr
          });
          renderActivityLogs();

          // Recargar tabla de casos
          await fetchCasos();
          
          // Actualizar vista de detalles
          window.verDetalleCaso(casoSeleccionadoId);
        } else {
          alert("Error al actualizar el estado del caso.");
        }
      } catch (err) {
        console.error(err);
        alert("Fallo la comunicación al cambiar el estado.");
      } finally {
        btnSaveCaseStatus.disabled = false;
        btnSaveCaseStatus.innerText = "Actualizar Estado";
      }
    });
  }

  // Filtros y búsquedas en tiempo real
  const searchCasos = document.getElementById("search-casos");
  const filterPrioridad = document.getElementById("filter-prioridad");
  const filterEstado = document.getElementById("filter-estado");

  function filtrarCasos() {
    if (casosGlobales.length === 0) return;
    const query = searchCasos.value.toLowerCase().trim();
    const prio = filterPrioridad.value;
    const est = filterEstado.value;

    const filtrados = casosGlobales.filter(c => {
      const matchQuery = !query || 
        c.id_reporte.toLowerCase().includes(query) ||
        (c.nombre_reportante && c.nombre_reportante.toLowerCase().includes(query)) ||
        (c.alias_sospechoso && c.alias_sospechoso.toLowerCase().includes(query)) ||
        (c.unidad_gaula && c.unidad_gaula.toLowerCase().includes(query));
      
      const matchPrio = !prio || c.prioridad === prio;
      const matchEst = !est || c.estado === est;

      return matchQuery && matchPrio && matchEst;
    });

    renderCasos(filtrados);
  }

  if (searchCasos) searchCasos.addEventListener("input", filtrarCasos);
  if (filterPrioridad) filterPrioridad.addEventListener("change", filtrarCasos);
  if (filterEstado) filterEstado.addEventListener("change", filtrarCasos);


  // --- EXPLORADOR DE ENTIDADES (TABS) ---
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const targetTab = btn.getAttribute("data-tab");
      tabPanels.forEach(panel => {
        if (panel.id === targetTab) {
          panel.classList.add("active");
        } else {
          panel.classList.remove("active");
        }
      });
    });
  });

  async function fetchEntidades() {
    const personasBody = document.getElementById("entities-personas-body");
    if (!personasBody) return;

    personasBody.innerHTML = `<tr><td colspan="4" class="text-center">Consultando registros intel...</td></tr>`;
    
    try {
      const response = await fetch("/api/entidades");
      if (response.ok) {
        const data = await response.json();
        
        // Render Personas
        personasBody.innerHTML = data.personas.map(p => `
          <tr>
            <td><strong>${p.nombre}</strong></td>
            <td class="text-mono">${p.documento}</td>
            <td><span class="badge ${p.rol.toLowerCase() === "sospechoso" ? "alert-kpi" : ""}">${p.rol}</span></td>
            <td class="text-mono text-small-col">${p.casos_vinculados.join(", ")}</td>
          </tr>
        `).join("");

        // Render Telefonos
        document.getElementById("entities-telefonos-body").innerHTML = data.telefonos.map(t => `
          <tr>
            <td class="text-mono"><strong>${t.numero}</strong></td>
            <td>${t.compania}</td>
            <td><span class="badge ${t.tipo.toLowerCase() === "extorsivo" ? "alert-kpi" : ""}">${t.tipo}</span></td>
            <td class="text-mono text-small-col">${t.casos_vinculados.join(", ")}</td>
          </tr>
        `).join("");

        // Render Alias
        document.getElementById("entities-alias-body").innerHTML = data.alias.map(a => `
          <tr>
            <td><strong class="color-cyan">${a.nombre}</strong></td>
            <td>${a.descripcion}</td>
            <td class="text-mono text-small-col">${a.casos_vinculados.join(", ")}</td>
          </tr>
        `).join("");

        // Render Ubicaciones
        document.getElementById("entities-ubicaciones-body").innerHTML = data.ubicaciones.map(u => `
          <tr>
            <td><strong>${u.nombre}</strong></td>
            <td class="text-mono">${u.coordenadas}</td>
            <td><span class="badge">${u.tipo}</span></td>
            <td class="text-mono text-small-col">${u.casos_vinculados.join(", ")}</td>
          </tr>
        `).join("");
      }
    } catch (err) {
      console.error(err);
      personasBody.innerHTML = `<tr><td colspan="4" class="text-center error-text">Fallo de conexión.</td></tr>`;
    }
  }


  // --- CORRELACIONES Y OSINT ---
  async function fetchRelaciones() {
    const relBody = document.getElementById("intel-relations-body");
    if (!relBody) return;

    relBody.innerHTML = `<tr><td colspan="4" class="text-center">Buscando relaciones cruzadas...</td></tr>`;

    try {
      const response = await fetch("/api/inteligencia/relaciones");
      if (response.ok) {
        const data = await response.json();
        relBody.innerHTML = data.relaciones.map(r => `
          <tr>
            <td><strong class="text-mono">${r.origen}</strong></td>
            <td><strong class="text-mono color-cyan">${r.destino}</strong></td>
            <td><span class="badge">${r.tipo}</span></td>
            <td class="text-mono font-bold">${r.confianza}</td>
          </tr>
        `).join("");
      }
    } catch (err) {
      console.error(err);
      relBody.innerHTML = `<tr><td colspan="4" class="text-center error-text">Error de carga.</td></tr>`;
    }
  }

  // Escáner OSINT (HaveIBeenPwned API)
  const btnLoadOsint = document.getElementById("btn-load-osint");
  const intelOsintBody = document.getElementById("intel-osint-body");

  if (btnLoadOsint) {
    btnLoadOsint.addEventListener("click", async () => {
      intelOsintBody.innerHTML = `<tr><td colspan="4" class="text-center">Conectando con base externa... (Escaner de Credenciales expuestas)</td></tr>`;
      btnLoadOsint.disabled = true;
      btnLoadOsint.innerText = "Escaneando...";

      try {
        const response = await fetch("/api/brechas");
        if (response.ok) {
          const brechas = await response.json();
          intelOsintBody.innerHTML = brechas.map(b => `
            <tr>
              <td><strong>${b.Nombre}</strong></td>
              <td><code>${b.Dominio}</code></td>
              <td class="text-mono">${b.Fecha}</td>
              <td class="text-mono font-bold color-orange">${b.Cantidad_afectados.toLocaleString()}</td>
            </tr>
          `).join("");
        } else {
          intelOsintBody.innerHTML = `<tr><td colspan="4" class="text-center error-text">No se pudo acceder a la API externa de OSINT.</td></tr>`;
        }
      } catch (err) {
        console.error(err);
        intelOsintBody.innerHTML = `<tr><td colspan="4" class="text-center error-text">Fallo de conexión externa.</td></tr>`;
      } finally {
        btnLoadOsint.disabled = false;
        btnLoadOsint.innerText = "Escanear Brechas Activas";
      }
    });
  }


  // --- ACTUALIZACIÓN DE KPIS EN DASHBOARD EJECUTIVO ---
  function actualizarKPIsDashboard(casos) {
    const kpiActive = document.getElementById("kpi-active-cases");
    const kpiCritical = document.getElementById("kpi-critical-cases");
    if (!kpiActive || !kpiCritical) return;

    kpiActive.innerText = casos.length;
    kpiCritical.innerText = casos.filter(c => c.prioridad.toLowerCase() === "crítica").length;
  }

  async function fetchDashboardData() {
    // Si la lista de casos está vacía, cargamos casos primero
    if (casosGlobales.length === 0) {
      try {
        const response = await fetch("/api/dataset/casos");
        if (response.ok) casosGlobales = await response.json();
      } catch (err) {
        console.error(err);
      }
    }

    actualizarKPIsDashboard(casosGlobales);
    renderDistribucionDelitos(casosGlobales);
  }

  let intelDashboardLoaded = false;

  async function fetchIntelDashboard() {
    if (intelDashboardLoaded) return;

    const loading = document.getElementById("intel-dashboard-loading");
    const kpisEl = document.getElementById("intel-kpis");
    const chartsEl = document.getElementById("intel-charts-container");
    if (!chartsEl || !kpisEl) return;

    loading && (loading.textContent = "Cargando dashboard de inteligencia...");

    try {
      const response = await fetch("/api/intel/dashboard");
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      const kpis = data.kpis || {};
      const charts = data.charts || {};

      kpisEl.innerHTML = `
        <div class="dashboard-card double-bezel">
          <div class="inner-core" style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;color:#94a3b8;">Total Casos</div>
              <div style="font-size:1.6rem;font-weight:700;color:#38bdf8;">${Number(kpis.total_casos || 0).toLocaleString()}</div>
            </div>
            <span style="font-size:2rem;color:#475569;">📁</span>
          </div>
        </div>
        <div class="dashboard-card double-bezel">
          <div class="inner-core" style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;color:#94a3b8;">Impacto Económico</div>
              <div style="font-size:1.6rem;font-weight:700;color:#38bdf8;">$${Number(kpis.total_monto || 0).toLocaleString()} COP</div>
            </div>
            <span style="font-size:2rem;color:#475569;">💰</span>
          </div>
        </div>
        <div class="dashboard-card double-bezel">
          <div class="inner-core" style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;color:#94a3b8;">Score Riesgo Prom.</div>
              <div style="font-size:1.6rem;font-weight:700;color:#38bdf8;">${Number(kpis.avg_riesgo || 0)}%</div>
            </div>
            <span style="font-size:2rem;color:#475569;">⚠️</span>
          </div>
        </div>
        <div class="dashboard-card double-bezel">
          <div class="inner-core" style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;color:#94a3b8;">Alertas OSINT</div>
              <div style="font-size:1.6rem;font-weight:700;color:#38bdf8;">${Number(kpis.total_alertas || 0).toLocaleString()}</div>
            </div>
            <span style="font-size:2rem;color:#475569;">👁️</span>
          </div>
        </div>
      `;

      chartsEl.innerHTML = `
        <div style="display:grid;grid-template-columns:7fr 5fr;gap:16px;margin-bottom:16px;">
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.line_casos || ""}</div></div>
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.bar_monto || ""}</div></div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.bar_dept || ""}</div></div>
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.donut_tipo || ""}</div></div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.bar_canal_prioridad || ""}</div></div>
          <div class="dashboard-card double-bezel"><div class="inner-core">${charts.osint_indicador || ""}</div></div>
        </div>
      `;

      if (loading) loading.style.display = "none";
      intelDashboardLoaded = true;
    } catch (err) {
      console.error("Error cargando dashboard intel:", err);
      if (loading) loading.textContent = "Error al cargar el dashboard de inteligencia.";
    }
  }

  function renderDistribucionDelitos(casos) {
    const container = document.getElementById("kpi-distribution-bars");
    if (!container) return;

    // Calcular distribución
    const conteo = {};
    casos.forEach(c => {
      const tipo = c.tipo_reporte || "Otros";
      conteo[tipo] = (conteo[tipo] || 0) + 1;
    });

    // Caso de base de datos vacía (Usamos mock con fines visuales de demo)
    if (Object.keys(conteo).length === 0) {
      conteo["Extorsión"] = 18;
      conteo["Hurto"] = 11;
      conteo["Fraude digital"] = 9;
      conteo["Secuestro"] = 3;
    }

    const maxVal = Math.max(...Object.values(conteo));
    const listHtml = Object.entries(conteo).map(([tipo, cant]) => {
      const pct = Math.round((cant / maxVal) * 100);
      return `
        <div class="bar-row-tactical">
          <div class="bar-labels">
            <span>${tipo}</span>
            <small class="text-mono">${cant} registros</small>
          </div>
          <div class="bar-track">
            <div class="bar-fill" style="width: ${pct}%;"></div>
          </div>
        </div>
      `;
    }).join("");

    container.innerHTML = listHtml;
  }

  // --- ARRANQUE AUTOMÁTICO SEGÚN ROL ---
  // Redirigir a paneles lógicos por defecto
  function autoRouteByRole() {
    if (userRole === "operador") {
      const navItemForm = document.querySelector('[data-panel="panel-formulario"]');
      if (navItemForm) navItemForm.click();
    } else if (userRole === "analista") {
      const navItemCasos = document.querySelector('[data-panel="panel-casos"]');
      if (navItemCasos) navItemCasos.click();
    } else if (userRole === "director") {
      const navItemDash = document.querySelector('[data-panel="panel-dashboard"]');
      if (navItemDash) navItemDash.click();
    } else {
      // Admin o generales
      const navItemInicio = document.querySelector('[data-panel="panel-inicio"]');
      if (navItemInicio) navItemInicio.click();
    }
  }
  autoRouteByRole();
});
