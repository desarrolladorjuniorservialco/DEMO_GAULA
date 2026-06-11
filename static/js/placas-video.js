// static/js/placas-video.js
// Sube el video al servidor para análisis completo (todos los frames) y muestra
// los resultados en vivo vía SSE mientras el video se reproduce localmente.
(function () {
  "use strict";

  // ── Estado ───────────────────────────────────────────────────────────────────
  let videoFile = null;
  let jobId     = null;
  let evtSource = null;
  let analyzing = false;

  // ── DOM ──────────────────────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  const dropZone     = $("drop-zone");
  const videoInput   = $("video-input");
  const dropInner    = $("drop-inner");
  const dropFileName = $("drop-file-name");
  const btnAnalizar  = $("btn-analizar");
  const progressWrap = $("pv-progress-wrap");
  const progressBar  = $("progress-bar");
  const statusLabel  = $("status-label");
  const statusPct    = $("status-pct");
  const countersEl   = $("pv-counters");
  const bannerError  = $("banner-error");
  const playerWrap   = $("pv-player-wrap");
  const videoEl      = $("placas-video");
  const resultsPanel = $("pv-results-panel");
  const placasList   = $("placas-list");
  const emptyMsg     = $("pv-empty-msg");

  // ── Drop zone ─────────────────────────────────────────────────────────────────
  dropZone.addEventListener("click", (e) => {
    if (e.target.closest("label")) return;
    videoInput.click();
  });
  videoInput.addEventListener("change", () => {
    if (videoInput.files[0]) seleccionarArchivo(videoInput.files[0]);
  });
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith("video/")) seleccionarArchivo(f);
  });

  function seleccionarArchivo(file) {
    if (file.size > 200 * 1024 * 1024) {
      mostrarError("El video supera el límite de 200 MB");
      return;
    }
    cerrarStream();
    analyzing = false;
    videoFile = file;
    jobId = null;
    placasList.innerHTML = "";
    ocultarError();

    dropInner.style.display = "none";
    dropFileName.textContent =
      file.name + " (" + (file.size / 1024 / 1024).toFixed(1) + " MB)";
    dropFileName.style.display = "block";

    videoEl.src = URL.createObjectURL(file);
    playerWrap.style.display = "block";
    resultsPanel.style.display = "block";
    if (emptyMsg) emptyMsg.style.display = "block";

    btnAnalizar.disabled = false;
    btnAnalizar.textContent = "Iniciar análisis";
    progressWrap.style.display = "none";
    if (countersEl) countersEl.textContent = "";
  }

  // ── Análisis ─────────────────────────────────────────────────────────────────
  btnAnalizar.addEventListener("click", () => {
    if (!videoFile || analyzing) return;
    iniciarAnalisis();
  });

  function iniciarAnalisis() {
    analyzing = true;
    btnAnalizar.disabled = true;
    btnAnalizar.textContent = "Analizando…";
    progressWrap.style.display = "block";
    progressBar.style.width = "0%";
    placasList.innerHTML = "";
    if (emptyMsg) emptyMsg.style.display = "block";
    ocultarError();
    setStatus("Subiendo video…", "0%");

    const fd = new FormData();
    fd.append("video", videoFile, videoFile.name);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/placas/video/upload");
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const p = Math.round((e.loaded / e.total) * 100);
        progressBar.style.width = p + "%";
        setStatus("Subiendo video…", p + "%");
      }
    };
    xhr.onload = () => {
      let data;
      try { data = JSON.parse(xhr.responseText); }
      catch (_) { fallo("Respuesta inválida del servidor"); return; }
      if (!data.ok) { fallo(data.error || "Error al subir el video"); return; }
      jobId = data.job_id;
      progressBar.style.width = "0%";
      setStatus("Analizando en servidor…", "0%");
      videoEl.play();
      abrirStream();
    };
    xhr.onerror = () => fallo("Error de red al subir el video");
    xhr.send(fd);
  }

  function abrirStream() {
    evtSource = new EventSource("/placas/video/" + jobId + "/stream");
    evtSource.onmessage = (m) => {
      let d;
      try { d = JSON.parse(m.data); } catch (_) { return; }
      aplicarEstado(d);
    };
    evtSource.onerror = () => {
      // El servidor cierra el stream al terminar; solo es error si seguíamos analizando
      if (analyzing) {
        cerrarStream();
        consultarResultadoFinal();
      }
    };
  }

  function aplicarEstado(d) {
    const pct = Math.round((d.progreso || 0) * 100);
    progressBar.style.width = pct + "%";
    setStatus(
      d.estado === "processing" ? "Analizando en servidor…" : d.estado,
      pct + "%"
    );
    actualizarContadores(d);
    (d.eventos || []).forEach(procesarEvento);

    if (d.estado === "done")  finalizar(d);
    if (d.estado === "error") fallo(d.error || "Error en el análisis");
  }

  function actualizarContadores(d) {
    if (!countersEl) return;
    let txt = (d.vehiculos || 0) + " vehículo(s) · " +
              (d.placas_leidas || 0) + " placa(s) leída(s)";
    if (d.sin_lectura) txt += " · " + d.sin_lectura + " sin lectura";
    if (d.modelo_detector === "fallback") txt += " · ⚠ modelo genérico";
    countersEl.textContent = txt;
  }

  function procesarEvento(ev) {
    if (ev.tipo === "placa") {
      agregarFila(ev.placa, ev.tipo_vehiculo, ev.confianza, ev.ts_s, false);
    } else if (ev.tipo === "sin_lectura") {
      agregarFila("SIN LECTURA", null, null, ev.ts_s, true);
    } else {
      return; // eventos "vehiculo" solo afectan contadores
    }
    if (emptyMsg) emptyMsg.style.display = "none";
  }

  function finalizar(d) {
    analyzing = false;
    cerrarStream();
    progressBar.style.width = "100%";
    setStatus(
      "Análisis completo — " + (d.vehiculos || 0) + " vehículo(s), " +
      (d.placas_leidas || 0) + " placa(s) leída(s)",
      "100%"
    );
    btnAnalizar.disabled = false;
    btnAnalizar.textContent = "Analizar de nuevo";
  }

  function consultarResultadoFinal() {
    // Red de seguridad si el SSE se corta: pedir el estado completo una vez
    if (!jobId) return;
    fetch("/placas/video/" + jobId + "/results")
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) { fallo(d.error || "Análisis interrumpido"); return; }
        placasList.innerHTML = "";
        (d.eventos || []).forEach(procesarEvento);
        actualizarContadores(d);
        if (d.estado === "done") finalizar(d);
      })
      .catch(() => fallo("Conexión perdida con el servidor"));
  }

  // ── Tabla de resultados ───────────────────────────────────────────────────────
  function agregarFila(texto, tipo, confianza, ts, esGris) {
    const mm   = Math.floor(ts / 60);
    const ss   = String(Math.floor(ts % 60)).padStart(2, "0");
    const conf = confianza != null ? Math.round(confianza * 100) + "%" : "—";

    const li = document.createElement("li");
    li.innerHTML =
      `<span class="pv-placa-tag${esGris ? " pv-placa-tag--gris" : ""}">${texto}</span>` +
      `<span class="pv-placa-tipo">${tipo || "—"}</span>` +
      `<span class="pv-placa-conf">${conf}</span>` +
      `<span class="pv-placa-ts">${mm}:${ss}</span>` +
      `<button class="pv-placa-btn" data-ts="${ts}">&#9654; ir</button>`;

    li.querySelector(".pv-placa-btn").addEventListener("click", () => {
      videoEl.currentTime = ts;
      videoEl.play();
      videoEl.scrollIntoView({ behavior: "smooth", block: "center" });
    });

    placasList.prepend(li); // más reciente arriba
  }

  // ── Helpers UI ────────────────────────────────────────────────────────────────
  function cerrarStream() {
    if (evtSource) { evtSource.close(); evtSource = null; }
  }

  function setStatus(msg, pct) {
    statusLabel.textContent = msg;
    statusPct.textContent = pct;
  }

  function fallo(msg) {
    analyzing = false;
    cerrarStream();
    mostrarError(msg);
    btnAnalizar.disabled = false;
    btnAnalizar.textContent = "Reintentar análisis";
  }

  function mostrarError(msg) {
    document.getElementById("error-msg").textContent = msg;
    bannerError.style.display = "block";
  }

  function ocultarError() {
    bannerError.style.display = "none";
  }
})();
