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

  const intelDashboardState = {
    loaded: false,
    loading: false,
    rawCases: [],
    filters: {
      dateFrom: "",
      dateTo: "",
      departamento: "",
      municipio: "",
      tipo: "",
      estado: "",
      prioridad: "",
      group: "daily",
    },
  };

  const intelFilterIds = [
    "intel-filter-date-from",
    "intel-filter-date-to",
    "intel-filter-departamento",
    "intel-filter-municipio",
    "intel-filter-tipo",
    "intel-filter-estado",
    "intel-filter-prioridad",
    "intel-filter-group",
  ];

  const intelChartIds = [
    "intel-chart-municipios",
    "intel-chart-departamentos",
    "intel-chart-fecha",
    "intel-chart-evolucion",
    "intel-chart-tipos",
    "intel-chart-modalidades",
    "intel-chart-riesgo",
    "intel-chart-riesgo-municipio",
  ];

  function normalizeIntelValue(value) {
    return (value ?? "").toString().trim();
  }

  function normalizeIntelKey(value) {
    return normalizeIntelValue(value).toLowerCase();
  }

  function parseIntelDate(value) {
    if (!value) return null;
    const raw = normalizeIntelValue(value);
    const datePart = raw.length >= 10 ? raw.slice(0, 10) : raw;
    const parsed = new Date(datePart + "T00:00:00");
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function formatIntelDate(date) {
    if (!date) return "";
    return date.toISOString().slice(0, 10);
  }

  function formatIntelLabel(date, mode) {
    if (!date) return "";
    if (mode === "monthly") {
      return date.toLocaleDateString("es-CO", { month: "short", year: "numeric" });
    }
    return date.toLocaleDateString("es-CO", { day: "2-digit", month: "short" });
  }

  function parseIntelScore(value) {
    const parsed = Number.parseFloat(normalizeIntelValue(value));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function buildIntelChartLayout(overrides = {}) {
    return {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: {
        color: "#f0f4fa",
        family: "Nunito Sans, sans-serif",
      },
      margin: { l: 48, r: 28, t: 12, b: 48 },
      hovermode: "closest",
      showlegend: true,
      legend: {
        orientation: "h",
        y: -0.18,
        font: { color: "#8b99ae", size: 11 },
      },
      xaxis: {
        gridcolor: "rgba(255,255,255,0.06)",
        zerolinecolor: "rgba(255,255,255,0.08)",
        tickfont: { color: "#8b99ae", size: 11 },
        linecolor: "rgba(255,255,255,0.08)",
        automargin: true,
      },
      yaxis: {
        gridcolor: "rgba(255,255,255,0.06)",
        zerolinecolor: "rgba(255,255,255,0.08)",
        tickfont: { color: "#8b99ae", size: 11 },
        linecolor: "rgba(255,255,255,0.08)",
        automargin: true,
      },
      ...overrides,
    };
  }

  function renderIntelPlot(targetId, traces, layoutOverrides = {}) {
    const target = document.getElementById(targetId);
    if (!target || typeof Plotly === "undefined") return;
    const layout = buildIntelChartLayout(layoutOverrides);
    Plotly.react(target, traces, layout, {
      responsive: true,
      displayModeBar: false,
      staticPlot: false,
    });
  }

  function getIntelFilters() {
    return { ...intelDashboardState.filters };
  }

  function applyIntelNonDateFilters(records) {
    const filters = getIntelFilters();
    return records.filter(record => {
      const dept = normalizeIntelKey(record.departamento);
      const muni = normalizeIntelKey(record.municipio);
      const tipo = normalizeIntelKey(record.tipo_reporte);
      const estado = normalizeIntelKey(record.estado);
      const prioridad = normalizeIntelKey(record.prioridad);

      return (!filters.departamento || dept === normalizeIntelKey(filters.departamento)) &&
        (!filters.municipio || muni === normalizeIntelKey(filters.municipio)) &&
        (!filters.tipo || tipo === normalizeIntelKey(filters.tipo)) &&
        (!filters.estado || estado === normalizeIntelKey(filters.estado)) &&
        (!filters.prioridad || prioridad === normalizeIntelKey(filters.prioridad));
    });
  }

  function applyIntelDateFilters(records) {
    const filters = getIntelFilters();
    const dateFrom = filters.dateFrom ? parseIntelDate(filters.dateFrom) : null;
    const dateTo = filters.dateTo ? parseIntelDate(filters.dateTo) : null;
    if (!dateFrom && !dateTo) return records.slice();

    return records.filter(record => {
      const date = parseIntelDate(record.fecha_registro);
      if (!date) return false;
      if (dateFrom && date < dateFrom) return false;
      if (dateTo) {
        const end = new Date(dateTo);
        end.setHours(23, 59, 59, 999);
        if (date > end) return false;
      }
      return true;
    });
  }

  function groupIntelRecords(records, keyGetter, valueGetter = () => 1) {
    const bucket = new Map();
    records.forEach(record => {
      const key = keyGetter(record) || "Sin dato";
      const current = bucket.get(key) || 0;
      bucket.set(key, current + valueGetter(record));
    });
    return Array.from(bucket.entries());
  }

  function sortIntelBucket(entries, desc = true) {
    return entries.sort((a, b) => desc ? b[1] - a[1] : a[1] - b[1]);
  }

  function getIntelWindow(records) {
    const filters = getIntelFilters();
    const dates = records
      .map(record => parseIntelDate(record.fecha_registro))
      .filter(Boolean)
      .sort((a, b) => a - b);

    if (!dates.length) {
      return { currentStart: null, currentEnd: null, previousStart: null, previousEnd: null };
    }

    let currentStart = filters.dateFrom ? parseIntelDate(filters.dateFrom) : null;
    let currentEnd = filters.dateTo ? parseIntelDate(filters.dateTo) : null;

    if (!currentStart || !currentEnd) {
      currentEnd = dates[dates.length - 1];
      currentStart = new Date(currentEnd);
      currentStart.setDate(currentStart.getDate() - 29);
    }

    if (currentStart && currentEnd && currentEnd < currentStart) {
      const swap = currentStart;
      currentStart = currentEnd;
      currentEnd = swap;
    }

    const spanDays = Math.max(1, Math.round((currentEnd - currentStart) / 86400000) + 1);
    const previousEnd = new Date(currentStart);
    previousEnd.setDate(previousEnd.getDate() - 1);
    const previousStart = new Date(previousEnd);
    previousStart.setDate(previousStart.getDate() - (spanDays - 1));

    return { currentStart, currentEnd, previousStart, previousEnd };
  }

  function formatIntelWindowLabel(start, end) {
    if (!start || !end) return "Sin filtro";
    const startLabel = start.toLocaleDateString("es-CO", { day: "2-digit", month: "short" });
    const endLabel = end.toLocaleDateString("es-CO", { day: "2-digit", month: "short" });
    if (startLabel === endLabel) return startLabel;
    return `${startLabel} a ${endLabel}`;
  }

  function fillIntelSeries(records, start, end, groupBy) {
    if (!start || !end) return [];

    const normalized = new Map();
    records.forEach(record => {
      const date = parseIntelDate(record.fecha_registro);
      if (!date || date < start || date > end) return;
      const keyDate = new Date(date);
      const bucketKey = groupBy === "monthly"
        ? `${keyDate.getFullYear()}-${String(keyDate.getMonth() + 1).padStart(2, "0")}`
        : formatIntelDate(keyDate);
      normalized.set(bucketKey, (normalized.get(bucketKey) || 0) + 1);
    });

    const cursor = new Date(start);
    const points = [];
    while (cursor <= end) {
      const key = groupBy === "monthly"
        ? `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, "0")}`
        : formatIntelDate(cursor);
      if (groupBy === "monthly") {
        if (!points.length || points[points.length - 1].key !== key) {
          points.push({ key, label: formatIntelLabel(cursor, groupBy), value: normalized.get(key) || 0 });
        } else {
          points[points.length - 1].value += normalized.get(key) || 0;
        }
        const nextMonth = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
        cursor.setFullYear(nextMonth.getFullYear(), nextMonth.getMonth(), 1);
      } else {
        points.push({ key, label: formatIntelLabel(cursor, groupBy), value: normalized.get(key) || 0 });
        cursor.setDate(cursor.getDate() + 1);
      }
    }

    return points;
  }

  function setSelectOptions(selectId, values, placeholder) {
    const select = document.getElementById(selectId);
    if (!select) return;

    const currentValue = select.value;
    select.innerHTML = "";
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = placeholder;
    select.appendChild(defaultOption);

    values.forEach(value => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });

    if (currentValue && values.includes(currentValue)) {
      select.value = currentValue;
    }
  }

  function populateIntelFilters(records) {
    const departments = Array.from(new Set(records.map(r => normalizeIntelValue(r.departamento)).filter(Boolean))).sort((a, b) => a.localeCompare(b, "es"));
    const municipalities = Array.from(new Set(records.map(r => normalizeIntelValue(r.municipio)).filter(Boolean))).sort((a, b) => a.localeCompare(b, "es"));
    const types = Array.from(new Set(records.map(r => normalizeIntelValue(r.tipo_reporte)).filter(Boolean))).sort((a, b) => a.localeCompare(b, "es"));
    const states = Array.from(new Set(records.map(r => normalizeIntelValue(r.estado)).filter(Boolean))).sort((a, b) => a.localeCompare(b, "es"));
    const priorities = Array.from(new Set(records.map(r => normalizeIntelValue(r.prioridad)).filter(Boolean))).sort((a, b) => a.localeCompare(b, "es"));

    setSelectOptions("intel-filter-departamento", departments, "Todos los departamentos");
    setSelectOptions("intel-filter-municipio", municipalities, "Todos los municipios");
    setSelectOptions("intel-filter-tipo", types, "Todos los tipos");
    setSelectOptions("intel-filter-estado", states, "Todos los estados");
    setSelectOptions("intel-filter-prioridad", priorities, "Todas las prioridades");

    const dates = records.map(r => parseIntelDate(r.fecha_registro)).filter(Boolean).sort((a, b) => a - b);
    const dateFrom = document.getElementById("intel-filter-date-from");
    const dateTo = document.getElementById("intel-filter-date-to");
    if (dates.length) {
      const minDate = formatIntelDate(dates[0]);
      const maxDate = formatIntelDate(dates[dates.length - 1]);
      if (dateFrom && !dateFrom.value) dateFrom.min = minDate;
      if (dateTo && !dateTo.value) dateTo.min = minDate;
      if (dateFrom && !dateFrom.value) dateFrom.max = maxDate;
      if (dateTo && !dateTo.value) dateTo.max = maxDate;
    }
  }

  function buildIntelKpis(allRecords, filteredRecords, currentRecords, previousRecords) {
    const total = filteredRecords.length;
    const avgScore = total ? filteredRecords.reduce((sum, record) => sum + parseIntelScore(record.score_riesgo), 0) / total : 0;
    const critical = filteredRecords.filter(record => {
      const score = parseIntelScore(record.score_riesgo);
      return score >= 80 || normalizeIntelKey(record.prioridad) === "crítica" || normalizeIntelKey(record.prioridad) === "critica";
    }).length;
    const municipalityBuckets = sortIntelBucket(groupIntelRecords(filteredRecords, record => normalizeIntelValue(record.municipio)));
    const typeBuckets = sortIntelBucket(groupIntelRecords(filteredRecords, record => normalizeIntelValue(record.tipo_reporte)));
    const modalityBuckets = sortIntelBucket(groupIntelRecords(filteredRecords, record => normalizeIntelValue(record.modalidad)));
    const topMunicipality = municipalityBuckets[0] ? municipalityBuckets[0][0] : "Sin dato";
    const topType = typeBuckets[0] ? typeBuckets[0][0] : "Sin dato";
    const topModality = modalityBuckets[0] ? modalityBuckets[0][0] : "Sin dato";
    const currentTotal = currentRecords.length;
    const previousTotal = previousRecords.length;
    const growth = previousTotal > 0 ? ((currentTotal - previousTotal) / previousTotal) * 100 : (currentTotal > 0 ? 100 : 0);
    const activeMunicipios = new Set(filteredRecords.map(record => normalizeIntelValue(record.municipio)).filter(Boolean)).size;

    const growthClass = growth > 0 ? "intel-kpi-positive" : growth < 0 ? "intel-kpi-negative" : "intel-kpi-neutral";
    const growthLabel = `${growth >= 0 ? "+" : ""}${growth.toFixed(1)}% vs periodo previo`;

    return `
      <article class="kpi-card double-bezel intel-kpi-card">
        <div class="inner-core">
          <span>Reportes filtrados</span>
          <strong>${total.toLocaleString("es-CO")}</strong>
          <small>${allRecords.length.toLocaleString("es-CO")} en universo total</small>
        </div>
      </article>
      <article class="kpi-card double-bezel intel-kpi-card">
        <div class="inner-core">
          <span>Score riesgo promedio</span>
          <strong>${avgScore.toFixed(1)}%</strong>
          <small>Lectura media del universo activo</small>
        </div>
      </article>
      <article class="kpi-card double-bezel alert-kpi intel-kpi-card">
        <div class="inner-core">
          <span>Casos críticos</span>
          <strong>${critical.toLocaleString("es-CO")}</strong>
          <small>Score alto o prioridad crítica</small>
        </div>
      </article>
      <article class="kpi-card double-bezel intel-kpi-card">
        <div class="inner-core">
          <span>Municipios activos</span>
          <strong>${activeMunicipios.toLocaleString("es-CO")}</strong>
          <small>Huella territorial observada</small>
        </div>
      </article>
      <article class="kpi-card double-bezel intel-kpi-card ${growthClass}">
        <div class="inner-core">
          <span>Crecimiento temporal</span>
          <strong>${growthLabel}</strong>
          <small>${currentTotal} en ventana actual, ${previousTotal} en la anterior</small>
        </div>
      </article>
      <article class="kpi-card double-bezel intel-kpi-card">
        <div class="inner-core">
          <span>Lectura dominante</span>
          <strong>${topType}</strong>
          <small>${topMunicipality} | ${topModality}</small>
        </div>
      </article>
    `;
  }

  function clearIntelCharts() {
    intelChartIds.forEach(id => {
      const node = document.getElementById(id);
      if (node) node.innerHTML = "";
    });
  }

  function renderIntelDashboardCharts(baseRecords) {
    const filters = getIntelFilters();
    const groupBy = filters.group === "monthly" ? "monthly" : "daily";
    const nonDateFiltered = applyIntelNonDateFilters(baseRecords);
    const filteredRecords = applyIntelDateFilters(nonDateFiltered);
    const windowInfo = getIntelWindow(nonDateFiltered.length ? nonDateFiltered : filteredRecords);
    const currentWindowRecords = nonDateFiltered.filter(record => {
      const date = parseIntelDate(record.fecha_registro);
      if (!date || !windowInfo.currentStart || !windowInfo.currentEnd) return false;
      return date >= windowInfo.currentStart && date <= windowInfo.currentEnd;
    });
    const previousWindowRecords = nonDateFiltered.filter(record => {
      const date = parseIntelDate(record.fecha_registro);
      if (!date || !windowInfo.previousStart || !windowInfo.previousEnd) return false;
      return date >= windowInfo.previousStart && date <= windowInfo.previousEnd;
    });
    const filtered = filteredRecords;

    const totalNode = document.getElementById("intel-signal-total");
    const windowNode = document.getElementById("intel-signal-window");
    const themeNode = document.getElementById("intel-signal-theme");
    const summaryCount = document.getElementById("intel-filter-summary-count");
    const summaryDetail = document.getElementById("intel-filter-summary-detail");

    if (totalNode) totalNode.textContent = filtered.length.toLocaleString("es-CO");
    if (windowNode) windowNode.textContent = formatIntelWindowLabel(windowInfo.currentStart, windowInfo.currentEnd);
    if (themeNode) {
      const modalityBuckets = sortIntelBucket(groupIntelRecords(filtered, record => normalizeIntelValue(record.modalidad)));
      const topModality = modalityBuckets[0] ? modalityBuckets[0][0] : "Sin dato";
      themeNode.textContent = topModality;
    }
    if (summaryCount) summaryCount.textContent = `${filtered.length.toLocaleString("es-CO")} reportes`;
    if (summaryDetail) {
      summaryDetail.textContent = `${nonDateFiltered.length.toLocaleString("es-CO")} en el universo filtrado antes de la ventana temporal`;
    }

    const kpisNode = document.getElementById("intel-kpis");
    if (kpisNode) {
      kpisNode.innerHTML = buildIntelKpis(baseRecords, filtered, currentWindowRecords, previousWindowRecords);
    }

    const emptyState = document.getElementById("intel-dashboard-empty");

    if (!filtered.length) {
      clearIntelCharts();
      const loading = document.getElementById("intel-dashboard-loading");
      if (emptyState) emptyState.classList.remove("hidden");
      if (loading) {
        loading.style.display = "none";
      }
      return;
    }

    if (emptyState) emptyState.classList.add("hidden");

    const municipioTop = sortIntelBucket(groupIntelRecords(filtered, record => normalizeIntelValue(record.municipio))).slice(0, 10);
    const deptBuckets = sortIntelBucket(groupIntelRecords(filtered, record => normalizeIntelValue(record.departamento)));
    const fechaBuckets = sortIntelRecordsByDate(filtered, groupBy);
    const typeBuckets = sortIntelBucket(groupIntelRecords(filtered, record => normalizeIntelValue(record.tipo_reporte)));
    const modalityBuckets = sortIntelBucket(groupIntelRecords(filtered, record => normalizeIntelValue(record.modalidad)));
    const scoreValues = filtered.map(record => parseIntelScore(record.score_riesgo)).filter(value => Number.isFinite(value));
    const riskMunicipioBuckets = Array.from(
      new Map(
        filtered
          .map(record => normalizeIntelValue(record.municipio))
          .filter(Boolean)
          .map(municipio => {
            const municipioRecords = filtered.filter(record => normalizeIntelValue(record.municipio) === municipio);
            const avg = municipioRecords.reduce((sum, record) => sum + parseIntelScore(record.score_riesgo), 0) / Math.max(1, municipioRecords.length);
            return [municipio, avg];
          })
      ).entries()
    )
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);

    renderIntelTopMunicipios(municipioTop);
    renderIntelDepartamentos(deptBuckets);
    renderIntelTrend(fechaBuckets, groupBy);
    renderIntelEvolution(currentWindowRecords, previousWindowRecords, groupBy, windowInfo);
    renderIntelTipos(typeBuckets);
    renderIntelModalidades(modalityBuckets);
    renderIntelRiskHistogram(scoreValues);
    renderIntelRiskMunicipio(riskMunicipioBuckets);
  }

  function sortIntelRecordsByDate(records, groupBy) {
    const map = new Map();
    records.forEach(record => {
      const date = parseIntelDate(record.fecha_registro);
      if (!date) return;
      const key = groupBy === "monthly"
        ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`
        : formatIntelDate(date);
      map.set(key, (map.get(key) || 0) + 1);
    });

    const result = Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    return result;
  }

  function renderIntelTopMunicipios(entries) {
    const labels = entries.map(entry => entry[0]);
    const values = entries.map(entry => entry[1]);
    renderIntelPlot("intel-chart-municipios", [{
      type: "bar",
      x: values,
      y: labels,
      orientation: "h",
      marker: {
        color: values,
        colorscale: [
          [0, "rgba(0, 229, 255, 0.35)"],
          [1, "#00e5ff"],
        ],
        line: { color: "rgba(0,229,255,0.35)", width: 1 },
      },
      text: values.map(value => value.toString()),
      textposition: "outside",
      hovertemplate: "%{y}<br>Reportes: %{x}<extra></extra>",
    }], {
      margin: { l: 160, r: 24, t: 12, b: 36 },
      xaxis: { title: "Cantidad de reportes" },
      yaxis: { automargin: true, autorange: "reversed" },
    });
  }

  function renderIntelDepartamentos(entries) {
    const labels = entries.map(entry => entry[0]);
    const values = entries.map(entry => entry[1]);
    renderIntelPlot("intel-chart-departamentos", [{
      type: "bar",
      x: values,
      y: labels,
      orientation: "h",
      marker: {
        color: values,
        colorscale: [
          [0, "rgba(111,202,82,0.35)"],
          [0.5, "rgba(0,229,255,0.72)"],
          [1, "rgba(255,90,31,0.95)"],
        ],
      },
      hovertemplate: "%{y}<br>Casos: %{x}<extra></extra>",
    }], {
      margin: { l: 140, r: 24, t: 12, b: 36 },
      xaxis: { title: "Número de reportes" },
      yaxis: { automargin: true, autorange: "reversed" },
      showlegend: false,
    });
  }

  function renderIntelTrend(entries, groupBy) {
    const labels = entries.map(entry => entry[0]);
    const values = entries.map(entry => entry[1]);
    renderIntelPlot("intel-chart-fecha", [{
      type: "bar",
      x: labels,
      y: values,
      marker: {
        color: values,
        colorscale: "Blues",
        line: { color: "rgba(0,229,255,0.32)", width: 1 },
      },
      hovertemplate: "%{x}<br>Reportes: %{y}<extra></extra>",
    }], {
      xaxis: { title: groupBy === "monthly" ? "Mes registro" : "Fecha registro", tickangle: -35 },
      yaxis: { title: "Número de reportes" },
      showlegend: false,
      margin: { l: 48, r: 28, t: 12, b: 72 },
    });
  }

  function renderIntelEvolution(currentRecords, previousRecords, groupBy, windowInfo) {
    const currentSeries = fillIntelSeries(currentRecords, windowInfo.currentStart, windowInfo.currentEnd, groupBy);
    const previousSeries = fillIntelSeries(previousRecords, windowInfo.previousStart, windowInfo.previousEnd, groupBy);
    const currentX = currentSeries.map(point => point.label);
    const previousX = previousSeries.map(point => point.label);

    renderIntelPlot("intel-chart-evolucion", [
      {
        type: "scatter",
        mode: "lines+markers",
        x: currentX,
        y: currentSeries.map(point => point.value),
        name: "Periodo actual",
        line: { color: "#00e5ff", width: 3 },
        marker: { color: "#00e5ff", size: 6 },
        hovertemplate: "%{x}<br>Actual: %{y}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines+markers",
        x: previousX,
        y: previousSeries.map(point => point.value),
        name: "Periodo anterior",
        line: { color: "#ff5a1f", width: 3, dash: "dot" },
        marker: { color: "#ff5a1f", size: 6 },
        hovertemplate: "%{x}<br>Anterior: %{y}<extra></extra>",
      },
    ], {
      xaxis: { title: groupBy === "monthly" ? "Mes" : "Fecha", tickangle: -35 },
      yaxis: { title: "Reportes" },
      showlegend: true,
      legend: { orientation: "h", y: -0.28, font: { color: "#8b99ae", size: 11 } },
      margin: { l: 48, r: 28, t: 12, b: 88 },
    });
  }

  function renderIntelTipos(entries) {
    const labels = entries.map(entry => entry[0]);
    const values = entries.map(entry => entry[1]);
    renderIntelPlot("intel-chart-tipos", [{
      type: "pie",
      labels,
      values,
      hole: 0.46,
      sort: false,
      textinfo: "label+percent",
      textposition: "outside",
      marker: {
        colors: labels.map((_, index) => `hsl(${190 + index * 16}, 88%, ${52 - Math.min(index * 2, 18)}%)`),
        line: { color: "rgba(7,8,12,0.8)", width: 2 },
      },
      hovertemplate: "%{label}<br>Cantidad: %{value}<extra></extra>",
    }], {
      margin: { l: 24, r: 24, t: 12, b: 24 },
      showlegend: false,
    });
  }

  function renderIntelModalidades(entries) {
    const labels = entries.map(entry => entry[0]);
    const values = entries.map(entry => entry[1]);
    renderIntelPlot("intel-chart-modalidades", [{
      type: "pie",
      labels,
      values,
      hole: 0.58,
      sort: false,
      textinfo: "label+percent",
      textposition: "outside",
      marker: {
        colors: labels.map((_, index) => `hsl(${25 + index * 26}, 92%, ${54 - Math.min(index * 2, 16)}%)`),
        line: { color: "rgba(7,8,12,0.8)", width: 2 },
      },
      hovertemplate: "%{label}<br>Cantidad: %{value}<extra></extra>",
    }], {
      margin: { l: 8, r: 8, t: 12, b: 18 },
      showlegend: false,
    });
  }

  function renderIntelRiskHistogram(values) {
    renderIntelPlot("intel-chart-riesgo", [{
      type: "histogram",
      x: values,
      nbinsx: 12,
      marker: {
        color: "rgba(0,229,255,0.85)",
        line: { color: "rgba(255,255,255,0.2)", width: 1 },
      },
      hovertemplate: "Score: %{x}<extra></extra>",
    }], {
      xaxis: { title: "Score de riesgo" },
      yaxis: { title: "Frecuencia" },
      showlegend: false,
    });
  }

  function renderIntelRiskMunicipio(entries) {
    const labels = entries.map(entry => entry[0]);
    const values = entries.map(entry => entry[1]);
    renderIntelPlot("intel-chart-riesgo-municipio", [{
      type: "bar",
      x: labels,
      y: values,
      marker: {
        color: values,
        colorscale: [
          [0, "rgba(0,230,118,0.35)"],
          [0.5, "rgba(255,214,0,0.75)"],
          [1, "rgba(255,90,31,0.95)"],
        ],
      },
      hovertemplate: "%{x}<br>Score promedio: %{y:.1f}<extra></extra>",
    }], {
      xaxis: { title: "Municipio" },
      yaxis: { title: "Score promedio" },
      showlegend: false,
      margin: { l: 52, r: 24, t: 12, b: 110 },
    });
  }

  // ── Proyecciones: utilidades matemáticas ──────────────────────────────────

  function calcLinearRegression(xArr, yArr) {
    const n = xArr.length;
    if (xArr.length !== yArr.length) {
      console.warn("calcLinearRegression: arrays must have equal length");
      return { slope: 0, intercept: 0 };
    }
    if (n < 2) return { slope: 0, intercept: yArr[0] ?? 0 };
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
    if (!lastMonthStr || !/^\d{4}-\d{2}$/.test(lastMonthStr)) {
      console.warn("buildFutureMonths: expected YYYY-MM, got:", lastMonthStr);
      return [];
    }
    const months = [];
    const [y, m] = lastMonthStr.split("-").map(Number);
    for (let i = 1; i <= n; i++) {
      const d = new Date(y, m - 1 + i, 1);
      months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
    }
    return months;
  }

  function getScenarioModifiers(escenario, steps) {
    const linspace = (start, end, len) => {
      if (len <= 0) return [];
      if (len === 1) return [start];
      return Array.from({ length: len }, (_, i) => start + (end - start) * (i / (len - 1)));
    };
    if (escenario === "optimista")  return { mods: linspace(0.85, 0.50, steps), color: "#22c55e" };
    if (escenario === "pesimista")  return { mods: linspace(1.20, 2.10, steps), color: "#ef4444" };
    return { mods: linspace(0.97, 1.03, steps), color: "#eab308" };  // realista
  }

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

  function buildProjectionAnalysis(escenario, tendencia, totalCasos, monto) {
    const safeTotal = Number.isFinite(totalCasos) ? totalCasos : 0;
    const safeMonto = Number.isFinite(monto)      ? monto      : 0;
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
    const safeColor = /^#[0-9a-fA-F]{3,8}$/.test(cfg.borderColor) ? cfg.borderColor : "#eab308";
    const tendenciaLabel = tendencia > 0 ? "al alza ↑" : tendencia < 0 ? "a la baja ↓" : "estable →";

    const el = document.getElementById("intel-projection-analysis-body");
    if (!el) { console.warn("buildProjectionAnalysis: #intel-projection-analysis-body not found"); return; }
    el.innerHTML = `
      <div style="border-left:4px solid ${safeColor};padding-left:1rem;">
        <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem;">
          <span style="font-size:1.5rem;">${cfg.icon}</span>
          <div>
            <strong style="color:${safeColor};font-size:1rem;">ESCENARIO ${cfg.label}</strong>
            <span class="helper-text-mono" style="display:block;font-size:.75rem;">Tendencia histórica: ${tendenciaLabel} · ${safeTotal.toLocaleString("es-CO")} casos · $${safeMonto.toLocaleString("es-CO")} COP</span>
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
      { type: "scatter", mode: "lines+markers", name: "Histórico",  x: volMonths, y: volValues, line: { color: "#94a3b8" } },
      { type: "scatter", mode: "lines+markers", name: "Proyección", x: volFM,     y: volFV,     line: { color: projColor, dash: "dot" }, marker: { symbol: "diamond" } },
    ], histLayout("Mes/Año", "Casos"));

    // ── G2: Impacto económico ───────────────────────────────────────────────
    const montoData   = montoDataPre;
    const montoMonths = montoData.map(d => d.month);
    const montoValues = montoData.map(d => d.sum);
    const { futureMonths: montoFM, futureValues: montoFV } = buildProjectionSeries(montoMonths, montoValues, escenario);

    renderIntelPlot("proj-chart-monto", [
      { type: "bar",     name: "Histórico ($)",    x: montoMonths, y: montoValues, marker: { color: "#38bdf8" } },
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
        { type: "scatter", mode: "lines", name: tipo,              x: tMonths, y: tValues, line: { color: tipoColors[idx], width: 2 } },
        { type: "scatter", mode: "lines", name: `${tipo} (proy.)`, x: tFM,     y: tFV,     line: { color: tipoColors[idx], dash: "dot", width: 1.5 }, showlegend: false },
      ];
    });
    renderIntelPlot("proj-chart-tipos", tipoTraces, histLayout("Mes/Año", "Casos por tipo"));
  }

  function syncIntelFilterState() {
    intelDashboardState.filters.dateFrom = document.getElementById("intel-filter-date-from")?.value || "";
    intelDashboardState.filters.dateTo = document.getElementById("intel-filter-date-to")?.value || "";
    intelDashboardState.filters.departamento = document.getElementById("intel-filter-departamento")?.value || "";
    intelDashboardState.filters.municipio = document.getElementById("intel-filter-municipio")?.value || "";
    intelDashboardState.filters.tipo = document.getElementById("intel-filter-tipo")?.value || "";
    intelDashboardState.filters.estado = document.getElementById("intel-filter-estado")?.value || "";
    intelDashboardState.filters.prioridad = document.getElementById("intel-filter-prioridad")?.value || "";
    intelDashboardState.filters.group = document.getElementById("intel-filter-group")?.value || "daily";
  }

  function bindIntelDashboardEvents() {
    intelFilterIds.forEach(id => {
      const node = document.getElementById(id);
      if (!node || node.dataset.intelBound === "1") return;
      node.dataset.intelBound = "1";
      node.addEventListener("change", () => {
        syncIntelFilterState();
        renderIntelDashboardCharts(intelDashboardState.rawCases);
      });
    });

    const resetBtn = document.getElementById("intel-filter-reset");
    if (resetBtn && resetBtn.dataset.intelBound !== "1") {
      resetBtn.dataset.intelBound = "1";
      resetBtn.addEventListener("click", () => {
        intelDashboardState.filters = {
          dateFrom: "",
          dateTo: "",
          departamento: "",
          municipio: "",
          tipo: "",
          estado: "",
          prioridad: "",
          group: "daily",
        };
        intelFilterIds.forEach(id => {
          const node = document.getElementById(id);
          if (node) node.value = node.tagName === "SELECT" && id === "intel-filter-group" ? "daily" : "";
        });
        renderIntelDashboardCharts(intelDashboardState.rawCases);
      });
    }
  }

  async function fetchIntelDashboard() {
    const loading = document.getElementById("intel-dashboard-loading");
    const kpisEl = document.getElementById("intel-kpis");
    if (!kpisEl) return;

    bindIntelDashboardEvents();

    if (intelDashboardState.loaded) {
      renderIntelDashboardCharts(intelDashboardState.rawCases);
      if (loading) loading.style.display = "none";
      return;
    }

    if (intelDashboardState.loading) return;
    intelDashboardState.loading = true;
    if (loading) {
      loading.style.display = "flex";
      loading.innerHTML = '<span class="intel-status-bullet"></span><span>Consultando bandeja de casos y calculando hallazgos...</span>';
    }

    try {
      const response = await fetch("/api/dataset/casos");
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      intelDashboardState.rawCases = Array.isArray(data) ? data : [];
      intelDashboardState.loaded = true;

      populateIntelFilters(intelDashboardState.rawCases);
      syncIntelFilterState();
      renderIntelDashboardCharts(intelDashboardState.rawCases);

      if (loading) loading.style.display = "none";
    } catch (err) {
      console.error("Error cargando dashboard intel:", err);
      if (loading) {
        loading.style.display = "flex";
        loading.innerHTML = '<span class="intel-status-bullet"></span><span>Error al cargar los casos. Revisa la conexión o el endpoint /api/dataset/casos.</span>';
      }
      clearIntelCharts();
      kpisEl.innerHTML = `
        <article class="dashboard-card double-bezel col-span-12">
          <div class="inner-core">
            <strong style="display:block;margin-bottom:8px;color:#ff5a1f;">No fue posible construir el dashboard</strong>
            <p class="helper-text-mono" style="margin:0;">${err.message}</p>
          </div>
        </article>
      `;
    } finally {
      intelDashboardState.loading = false;
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
