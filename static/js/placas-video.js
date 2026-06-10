// static/js/placas-video.js
// Canvas overlay + sincronización con video HTML5 para reconocimiento de placas
(function () {
  "use strict";

  // ── Estado ──────────────────────────────────────────────────────────────────
  let timeline = [];       // [{ts_ms, frame, detecciones:[...]}]
  let jobId = null;
  let eventSource = null;
  let videoFile = null;
  const trackColors = {};  // track_id -> color CSS

  // ── DOM ─────────────────────────────────────────────────────────────────────
  const dropZone     = document.getElementById("drop-zone");
  const videoInput   = document.getElementById("video-input");
  const dropInner    = document.getElementById("drop-inner");
  const dropFileName = document.getElementById("drop-file-name");
  const btnAnalizar  = document.getElementById("btn-analizar");
  const progressWrap = document.getElementById("pv-progress-wrap");
  const progressBar  = document.getElementById("progress-bar");
  const statusLabel  = document.getElementById("status-label");
  const statusPct    = document.getElementById("status-pct");
  const bannerError  = document.getElementById("banner-error");
  const playerWrap   = document.getElementById("pv-player-wrap");
  const videoEl      = document.getElementById("placas-video");
  const canvas       = document.getElementById("placas-canvas");
  const ctx          = canvas.getContext("2d");
  const resultsPanel = document.getElementById("pv-results-panel");
  const placasList   = document.getElementById("placas-list");

  // ── Helpers de color ─────────────────────────────────────────────────────────
  function colorParaTrack(trackId) {
    if (!trackColors[trackId]) {
      const hue = (trackId * 47) % 360;
      trackColors[trackId] = `hsl(${hue}, 90%, 55%)`;
    }
    return trackColors[trackId];
  }

  // ── Búsqueda binaria en timeline ──────────────────────────────────────────────
  function buscarFrame(ts_ms) {
    if (!timeline.length) return null;
    let lo = 0, hi = timeline.length - 1, best = timeline[0];
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (Math.abs(timeline[mid].ts_ms - ts_ms) < Math.abs(best.ts_ms - ts_ms)) {
        best = timeline[mid];
      }
      if (timeline[mid].ts_ms < ts_ms) lo = mid + 1;
      else hi = mid - 1;
    }
    return best;
  }

  // ── Canvas: dimensiones y dibujo ──────────────────────────────────────────────
  function syncCanvasSize() {
    const rect = videoEl.getBoundingClientRect();
    canvas.width  = rect.width;
    canvas.height = rect.height;
  }

  function dibujarOverlay() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!timeline.length) return;

    const ts_ms = Math.round(videoEl.currentTime * 1000);
    const frame = buscarFrame(ts_ms);
    if (!frame || Math.abs(frame.ts_ms - ts_ms) > 500) return;

    const W = canvas.width, H = canvas.height;

    for (const det of frame.detecciones) {
      const [x1n, y1n, x2n, y2n] = det.bbox;
      const x = x1n * W, y = y1n * H;
      const w = (x2n - x1n) * W, h = (y2n - y1n) * H;
      const color = colorParaTrack(det.track_id);

      ctx.strokeStyle = color;
      ctx.lineWidth = det.nuevo ? 3 : 2;
      ctx.strokeRect(x, y, w, h);

      const label = det.placa || ("T-" + det.track_id);
      ctx.font = "bold 12px 'IBM Plex Mono', monospace";
      const tw = ctx.measureText(label).width + 10;
      ctx.fillStyle = color;
      const ly = y - 22 < 0 ? y + h + 2 : y - 2;
      ctx.fillRect(x, ly - 18, tw, 20);
      ctx.fillStyle = "#000";
      ctx.fillText(label, x + 5, ly - 3);
    }
  }

  // ── Drop zone ─────────────────────────────────────────────────────────────────
  dropZone.addEventListener("click", (e) => {
    if (e.target.closest("label")) return;
    videoInput.click();
  });

  videoInput.addEventListener("change", () => {
    const f = videoInput.files[0];
    if (f) seleccionarArchivo(f);
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
    const MAX = 200 * 1024 * 1024;
    if (file.size > MAX) {
      mostrarError("El video supera el límite de 200 MB");
      return;
    }
    videoFile = file;
    dropInner.style.display = "none";
    dropFileName.textContent = file.name + " (" + (file.size / 1024 / 1024).toFixed(1) + " MB)";
    dropFileName.style.display = "block";
    btnAnalizar.disabled = false;
    ocultarError();
  }

  // ── Upload y análisis ─────────────────────────────────────────────────────────
  btnAnalizar.addEventListener("click", async () => {
    if (!videoFile) return;
    btnAnalizar.disabled = true;
    ocultarError();
    resetTimeline();

    const fd = new FormData();
    fd.append("video", videoFile);

    progressWrap.style.display = "block";
    setStatus("Subiendo video…", 0);

    let res, data;
    try {
      res  = await fetch("/placas/video/upload", { method: "POST", body: fd });
      data = await res.json();
    } catch (err) {
      mostrarError("Error de red: " + err.message);
      btnAnalizar.disabled = false;
      return;
    }

    if (!data.ok) {
      mostrarError(data.error || "Error desconocido");
      btnAnalizar.disabled = false;
      return;
    }

    jobId = data.job_id;

    videoEl.src = URL.createObjectURL(videoFile);
    playerWrap.style.display = "block";
    syncCanvasSize();

    suscribirSSE(jobId);
  });

  function suscribirSSE(jid) {
    if (eventSource) eventSource.close();
    eventSource = new EventSource(`/placas/video/${jid}/stream`);

    eventSource.onmessage = (e) => {
      const st  = JSON.parse(e.data);
      const pct = Math.round(st.progreso * 100);
      setStatus(
        st.estado === "processing" ? "Analizando frames…" :
        st.estado === "done"       ? "Análisis completo" :
        st.estado === "error"      ? "Error en análisis" : st.estado,
        pct
      );
      if (st.estado === "done")  { eventSource.close(); cargarResultados(jid); }
      if (st.estado === "error") {
        eventSource.close();
        mostrarError(st.error || "Error en el pipeline");
        btnAnalizar.disabled = false;
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      pollStatus(jid);
    };
  }

  async function pollStatus(jid) {
    while (true) {
      await new Promise(r => setTimeout(r, 2000));
      try {
        const r  = await fetch(`/placas/video/${jid}/status`);
        const st = await r.json();
        if (!st.ok) break;
        setStatus("Analizando…", Math.round(st.progreso * 100));
        if (st.estado === "done")  { cargarResultados(jid); break; }
        if (st.estado === "error") { mostrarError(st.error || "Error"); break; }
      } catch (_) { break; }
    }
  }

  async function cargarResultados(jid) {
    try {
      const r    = await fetch(`/placas/video/${jid}/results`);
      const data = await r.json();
      if (!data.ok) return;
      timeline = data.timeline;
      mostrarPlacasDetectadas(data.timeline);
    } catch (err) {
      mostrarError("Error cargando resultados: " + err.message);
    }
  }

  function mostrarPlacasDetectadas(tl) {
    const encontradas = new Map();
    for (const frame of tl) {
      for (const det of frame.detecciones) {
        if (det.placa && !encontradas.has(det.placa)) {
          encontradas.set(det.placa, { tipo: det.tipo, ts_ms: frame.ts_ms });
        }
      }
    }

    placasList.innerHTML = "";
    for (const [placa, info] of encontradas) {
      const seg = (info.ts_ms / 1000).toFixed(1);
      const li  = document.createElement("li");
      li.innerHTML =
        `<span class="pv-placa-tag">${placa}</span>` +
        `<span class="pv-placa-tipo">${info.tipo || ""}</span>` +
        `<span class="pv-placa-ts">${seg}s</span>` +
        `<button class="pv-placa-btn" data-ts="${info.ts_ms}">&#9654; ir</button>`;
      placasList.appendChild(li);
    }

    if (encontradas.size > 0) {
      resultsPanel.style.display = "block";
    }

    placasList.querySelectorAll(".pv-placa-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        videoEl.currentTime = parseInt(btn.dataset.ts, 10) / 1000;
        videoEl.play();
        videoEl.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    });
  }

  // ── Sincronización video → Canvas ─────────────────────────────────────────────
  videoEl.addEventListener("timeupdate", dibujarOverlay);
  videoEl.addEventListener("seeked",     dibujarOverlay);
  videoEl.addEventListener("play",       dibujarOverlay);
  window.addEventListener("resize", () => { syncCanvasSize(); dibujarOverlay(); });

  // ── Helpers UI ────────────────────────────────────────────────────────────────
  function setStatus(msg, pct) {
    statusLabel.textContent = msg;
    statusPct.textContent   = pct + "%";
    progressBar.style.width = pct + "%";
  }

  function mostrarError(msg) {
    document.getElementById("error-msg").textContent = msg;
    bannerError.style.display = "block";
  }

  function ocultarError() {
    bannerError.style.display = "none";
  }

  function resetTimeline() {
    timeline = [];
    placasList.innerHTML = "";
    resultsPanel.style.display = "none";
    Object.keys(trackColors).forEach(k => delete trackColors[k]);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  // ── Limpieza al salir ─────────────────────────────────────────────────────────
  window.addEventListener("beforeunload", () => {
    if (jobId) {
      navigator.sendBeacon(`/placas/video/${jobId}`, new Blob(
        [JSON.stringify({ _method: "DELETE" })],
        { type: "application/json" }
      ));
    }
  });

})();
