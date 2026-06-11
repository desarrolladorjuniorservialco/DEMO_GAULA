# Conteo de Placas en Video de Alto Movimiento — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Conteo preciso de vehículos y placas en videos de tráfico procesando todos los frames server-side, con YOLO de placas + ByteTrack + votación OCR y resultados en vivo vía SSE.

**Architecture:** El navegador sube el video y lo reproduce localmente; un thread del servidor decodifica todos los frames, detecta placas (modelo YOLOv8 fine-tuned, fallback COCO+máscara amarilla), las sigue con ByteTrack, acumula los mejores recortes por track y resuelve la placa final por votación entre los 3 mejores. Eventos incrementales (`vehiculo`/`placa`/`sin_lectura`) viajan por el SSE existente.

**Tech Stack:** Flask, OpenCV, ultralytics (YOLOv8), supervision (ByteTrack), EasyOCR, SSE, pytest.

**Spec:** `docs/superpowers/specs/2026-06-10-conteo-placas-video-design.md`

**Contexto para el implementador:**
- CPU solamente (sin CUDA). `ultralytics` y `supervision` ya instalados.
- Formatos de placa colombiana y validación: `modules/placas/engine.py` → `extraer_placas_de_texto(texto)` devuelve `list[(placa, tipo, exacto)]` donde `tipo ∈ {"CARRO","MOTO"}` y `exacto=True` si el texto completo era exactamente la placa.
- Tests corren con `python -m pytest tests/ -v` desde la raíz del repo (conftest ya inserta el path).
- Convención de commits del repo: `feat(placas): …` / `fix(placas): …` en español.

---

## Estructura de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `modules/placas/video/plate_votes.py` | Crear | `PlateVoter` (votación OCR por track) y `ConteoVideo` (contadores + eventos + fusión de duplicados) |
| `modules/placas/video/best_frames.py` | Crear | `TrackCropBuffer` (mejores K recortes por track, score área×nitidez) |
| `modules/placas/video/tracker.py` | Modificar | Añadir `ContadorHits` (confirmación de track tras ≥3 hits) |
| `modules/placas/video/detector.py` | Reescribir | Modo "placas" (modelo fine-tuned) / "fallback" (COCO+máscara amarilla) |
| `modules/placas/video/schemas.py` | Modificar | `VideoJob` gana `eventos`, contadores y `modelo_detector` |
| `modules/placas/video/pipeline.py` | Reescribir | Loop principal: detección cada 2 frames, buffer, cierre de tracks, OCR+voto |
| `modules/placas/video/ocr_cache.py` | Eliminar | Reemplazado por `PlateVoter` + `TrackCropBuffer` |
| `modules/placas/routes.py` | Modificar | SSE emite eventos incrementales (cursor) cada 0.5 s |
| `scripts/descargar_modelo_placas.py` | Crear | Descarga única del modelo YOLOv8 de placas a `models/` |
| `static/js/placas-video.js` | Reescribir | Upload con progreso + EventSource + tabla incremental |
| `templates/placas/video.html` | Modificar | Contadores, fila SIN LECTURA, quitar canvas overlay |
| `tests/test_placas_video.py` | Crear | Tests unitarios + integración del pipeline con mocks |

---

### Task 1: PlateVoter — votación de lecturas OCR por track

**Files:**
- Create: `modules/placas/video/plate_votes.py`
- Test: `tests/test_placas_video.py`

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_placas_video.py`:

```python
# tests/test_placas_video.py
"""Tests del pipeline de conteo de placas en video (sin dependencias ML pesadas)."""


# ── PlateVoter ────────────────────────────────────────────────────────────────

def test_voter_mayoria_simple():
    from modules.placas.video.plate_votes import PlateVoter
    v = PlateVoter()
    v.agregar_lectura(1, "ABC123", 0.9)
    v.agregar_lectura(1, "ABC123", 0.8)
    v.agregar_lectura(1, "A8C123", 0.7)  # misread: '8' en posición de letra → B
    placa, tipo, conf = v.resolver(1)
    assert placa == "ABC123"
    assert tipo == "CARRO"
    assert conf == 1.0  # todas las lecturas convergen a la misma placa


def test_voter_pondera_por_confianza():
    from modules.placas.video.plate_votes import PlateVoter
    v = PlateVoter()
    v.agregar_lectura(1, "XYZ789", 0.95)
    v.agregar_lectura(1, "XYZ789", 0.90)
    v.agregar_lectura(1, "XYZ780", 0.10)
    placa, _, conf = v.resolver(1)
    assert placa == "XYZ789"
    assert 0.0 < conf < 1.0


def test_voter_ignora_texto_invalido():
    from modules.placas.video.plate_votes import PlateVoter
    v = PlateVoter()
    assert v.agregar_lectura(1, "HOLA", 0.9) is False
    assert v.agregar_lectura(1, "", 0.9) is False
    assert v.agregar_lectura(1, None, 0.9) is False
    assert v.resolver(1) == (None, None, 0.0)


def test_voter_track_sin_lecturas():
    from modules.placas.video.plate_votes import PlateVoter
    assert PlateVoter().resolver(99) == (None, None, 0.0)


def test_voter_detecta_tipo_moto():
    from modules.placas.video.plate_votes import PlateVoter
    v = PlateVoter()
    v.agregar_lectura(2, "XYZ12D", 0.8)
    placa, tipo, _ = v.resolver(2)
    assert placa == "XYZ12D"
    assert tipo == "MOTO"
```

- [ ] **Step 2: Verificar que fallan**

Run: `python -m pytest tests/test_placas_video.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'modules.placas.video.plate_votes'`

- [ ] **Step 3: Implementación mínima**

Crear `modules/placas/video/plate_votes.py`:

```python
# modules/placas/video/plate_votes.py
from __future__ import annotations

import threading

from modules.placas.engine import extraer_placas_de_texto


class PlateVoter:
    """Acumula lecturas OCR por track y resuelve la placa final por mayoría ponderada.

    Cada lectura se valida contra los formatos de placa colombiana; el peso del
    voto es la confianza OCR (+0.15 si el texto era exactamente la placa).
    """

    def __init__(self) -> None:
        self._votos: dict[int, dict[str, float]] = {}   # track_id -> {placa: peso}
        self._tipos: dict[str, str] = {}                 # placa -> "CARRO" | "MOTO"
        self._lock = threading.Lock()

    def agregar_lectura(self, track_id: int, texto: str | None, confianza: float) -> bool:
        """Registra una lectura OCR. Devuelve True si contenía una placa válida."""
        if not texto:
            return False
        candidatos = extraer_placas_de_texto(texto)
        if not candidatos:
            return False
        placa, tipo, exacto = candidatos[0]
        peso = max(0.05, float(confianza)) + (0.15 if exacto else 0.0)
        with self._lock:
            votos = self._votos.setdefault(track_id, {})
            votos[placa] = votos.get(placa, 0.0) + peso
            self._tipos.setdefault(placa, tipo)
        return True

    def resolver(self, track_id: int) -> tuple[str | None, str | None, float]:
        """Devuelve (placa, tipo, confianza_normalizada) o (None, None, 0.0)."""
        with self._lock:
            votos = self._votos.get(track_id)
            if not votos:
                return None, None, 0.0
            placa = max(votos, key=votos.get)
            total = sum(votos.values())
            return placa, self._tipos.get(placa), round(votos[placa] / total, 2)
```

- [ ] **Step 4: Verificar que pasan**

Run: `python -m pytest tests/test_placas_video.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add modules/placas/video/plate_votes.py tests/test_placas_video.py
git commit -m "feat(placas): PlateVoter con votacion ponderada por track"
```

---

### Task 2: ConteoVideo — contadores, eventos y fusión de duplicados

**Files:**
- Modify: `modules/placas/video/plate_votes.py` (añadir clase)
- Test: `tests/test_placas_video.py` (añadir tests)

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_placas_video.py`:

```python
# ── ConteoVideo ───────────────────────────────────────────────────────────────

def test_conteo_confirma_vehiculo():
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo()
    ev = c.confirmar_vehiculo(track_id=1, ts_s=3.5)
    assert c.vehiculos == 1
    assert ev["tipo"] == "vehiculo"
    assert ev["ts_s"] == 3.5
    assert c.eventos == [ev]


def test_conteo_cierra_track_con_placa():
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo()
    c.confirmar_vehiculo(1, 1.0)
    ev = c.cerrar_track(1, "ABC123", "CARRO", 0.9, primer_ts=1.0, ultimo_ts=3.0)
    assert c.placas_leidas == 1
    assert ev["tipo"] == "placa"
    assert ev["placa"] == "ABC123"
    assert ev["tipo_vehiculo"] == "CARRO"


def test_conteo_sin_lectura():
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo()
    c.confirmar_vehiculo(1, 1.0)
    ev = c.cerrar_track(1, None, None, 0.0, primer_ts=1.0, ultimo_ts=2.0)
    assert c.sin_lectura == 1
    assert ev["tipo"] == "sin_lectura"


def test_conteo_fusiona_retrack_misma_placa():
    """Mismo vehículo re-trackeado (gap < 2 s): no cuenta doble."""
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo(gap_fusion_s=2.0)
    c.confirmar_vehiculo(1, 1.0)
    c.cerrar_track(1, "ABC123", "CARRO", 0.9, primer_ts=1.0, ultimo_ts=4.0)
    c.confirmar_vehiculo(2, 4.5)          # reaparece a los 0.5 s
    ev = c.cerrar_track(2, "ABC123", "CARRO", 0.8, primer_ts=4.5, ultimo_ts=6.0)
    assert ev is None                      # fusionado, sin evento nuevo
    assert c.vehiculos == 1                # el segundo vehículo se descuenta
    assert c.placas_leidas == 1


def test_conteo_misma_placa_lejos_en_el_tiempo_cuenta_dos_veces():
    """Si la placa reaparece tras un gap grande, son dos pasadas reales."""
    from modules.placas.video.plate_votes import ConteoVideo
    c = ConteoVideo(gap_fusion_s=2.0)
    c.confirmar_vehiculo(1, 1.0)
    c.cerrar_track(1, "ABC123", "CARRO", 0.9, primer_ts=1.0, ultimo_ts=3.0)
    c.confirmar_vehiculo(2, 30.0)
    ev = c.cerrar_track(2, "ABC123", "CARRO", 0.8, primer_ts=30.0, ultimo_ts=33.0)
    assert ev is not None
    assert c.vehiculos == 2
    assert c.placas_leidas == 2
```

- [ ] **Step 2: Verificar que fallan**

Run: `python -m pytest tests/test_placas_video.py -v -k conteo`
Expected: FAIL con `ImportError: cannot import name 'ConteoVideo'`

- [ ] **Step 3: Implementación**

Añadir al final de `modules/placas/video/plate_votes.py`:

```python
class ConteoVideo:
    """Contadores y eventos del conteo; fusiona tracks duplicados de la misma placa.

    Eventos (dicts append-only, consumidos incrementalmente por el SSE):
      {"tipo": "vehiculo",    "track_id": int, "ts_s": float}
      {"tipo": "placa",       "track_id": int, "placa": str,
       "tipo_vehiculo": str|None, "confianza": float, "ts_s": float}
      {"tipo": "sin_lectura", "track_id": int, "ts_s": float}
    """

    def __init__(self, gap_fusion_s: float = 2.0) -> None:
        self._gap = gap_fusion_s
        self._lock = threading.Lock()
        self.eventos: list[dict] = []
        self.vehiculos = 0
        self.placas_leidas = 0
        self.sin_lectura = 0
        # placa -> (primer_ts, ultimo_ts) de tracks ya cerrados con esa placa
        self._placas_vistas: dict[str, tuple[float, float]] = {}

    def confirmar_vehiculo(self, track_id: int, ts_s: float) -> dict:
        with self._lock:
            self.vehiculos += 1
            ev = {"tipo": "vehiculo", "track_id": track_id, "ts_s": round(ts_s, 2)}
            self.eventos.append(ev)
            return ev

    def cerrar_track(
        self,
        track_id: int,
        placa: str | None,
        tipo: str | None,
        confianza: float,
        primer_ts: float,
        ultimo_ts: float,
    ) -> dict | None:
        """Resultado final de un track confirmado. Devuelve el evento emitido,
        o None si se fusionó con un track previo de la misma placa."""
        with self._lock:
            if placa is None:
                self.sin_lectura += 1
                ev = {"tipo": "sin_lectura", "track_id": track_id,
                      "ts_s": round(primer_ts, 2)}
                self.eventos.append(ev)
                return ev

            previo = self._placas_vistas.get(placa)
            if previo and primer_ts - previo[1] < self._gap:
                # Mismo vehículo re-trackeado: descontar y no emitir evento
                self.vehiculos -= 1
                self._placas_vistas[placa] = (previo[0], max(previo[1], ultimo_ts))
                return None

            self._placas_vistas[placa] = (primer_ts, ultimo_ts)
            self.placas_leidas += 1
            ev = {"tipo": "placa", "track_id": track_id, "placa": placa,
                  "tipo_vehiculo": tipo, "confianza": round(float(confianza), 2),
                  "ts_s": round(primer_ts, 2)}
            self.eventos.append(ev)
            return ev
```

- [ ] **Step 4: Verificar que pasan**

Run: `python -m pytest tests/test_placas_video.py -v`
Expected: 10 PASS

- [ ] **Step 5: Commit**

```bash
git add modules/placas/video/plate_votes.py tests/test_placas_video.py
git commit -m "feat(placas): ConteoVideo con eventos y fusion de tracks duplicados"
```

---

### Task 3: TrackCropBuffer — mejores recortes por track

**Files:**
- Create: `modules/placas/video/best_frames.py`
- Test: `tests/test_placas_video.py` (añadir tests)

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_placas_video.py`:

```python
# ── TrackCropBuffer ───────────────────────────────────────────────────────────

def _crop_nitido(h=40, w=120):
    """Recorte sintético con alta varianza Laplaciana (ruido)."""
    import numpy as np
    rng = np.random.default_rng(42)
    return rng.integers(0, 255, size=(h, w, 3), dtype=np.uint8)


def _crop_borroso(h=40, w=120):
    """Recorte sintético plano (varianza Laplaciana ~0)."""
    import numpy as np
    return np.full((h, w, 3), 128, dtype=np.uint8)


def test_buffer_descarta_recortes_muy_pequenos():
    from modules.placas.video.best_frames import TrackCropBuffer
    buf = TrackCropBuffer()
    buf.agregar(1, _crop_nitido(h=8))          # alto < 12 px
    assert buf.mejores(1) == []


def test_buffer_prefiere_nitido_sobre_borroso():
    from modules.placas.video.best_frames import TrackCropBuffer
    buf = TrackCropBuffer(k=2)
    buf.agregar(1, _crop_borroso())
    buf.agregar(1, _crop_nitido())
    mejores = buf.mejores(1, n=1)
    assert len(mejores) == 1
    assert mejores[0].std() > 5   # el mejor debe ser el nítido


def test_buffer_limita_a_k():
    from modules.placas.video.best_frames import TrackCropBuffer
    buf = TrackCropBuffer(k=3)
    for _ in range(10):
        buf.agregar(1, _crop_nitido())
    assert len(buf.mejores(1, n=99)) == 3


def test_buffer_descartar_libera_memoria():
    from modules.placas.video.best_frames import TrackCropBuffer
    buf = TrackCropBuffer()
    buf.agregar(1, _crop_nitido())
    buf.descartar(1)
    assert buf.mejores(1) == []
```

- [ ] **Step 2: Verificar que fallan**

Run: `python -m pytest tests/test_placas_video.py -v -k buffer`
Expected: FAIL con `ModuleNotFoundError: No module named 'modules.placas.video.best_frames'`

- [ ] **Step 3: Implementación**

Crear `modules/placas/video/best_frames.py`:

```python
# modules/placas/video/best_frames.py
from __future__ import annotations

import cv2
import numpy as np

K_MEJORES_DEFAULT = 5
MIN_ALTO_PX = 12


def puntuar_recorte(crop_bgr: np.ndarray) -> float:
    """Score de calidad = área × varianza del Laplaciano (tamaño × nitidez).

    Recortes con alto < MIN_ALTO_PX devuelven 0.0 (ilegibles para OCR).
    """
    if crop_bgr is None or crop_bgr.size == 0:
        return 0.0
    h, w = crop_bgr.shape[:2]
    if h < MIN_ALTO_PX:
        return 0.0
    gris = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY) if crop_bgr.ndim == 3 else crop_bgr
    nitidez = float(cv2.Laplacian(gris, cv2.CV_64F).var())
    return float(h * w) * max(nitidez, 1.0)


class TrackCropBuffer:
    """Por cada track_id conserva los K mejores recortes de placa vistos."""

    def __init__(self, k: int = K_MEJORES_DEFAULT) -> None:
        self._k = k
        self._crops: dict[int, list[tuple[float, np.ndarray]]] = {}

    def agregar(self, track_id: int, crop_bgr: np.ndarray) -> None:
        score = puntuar_recorte(crop_bgr)
        if score <= 0.0:
            return
        lista = self._crops.setdefault(track_id, [])
        lista.append((score, crop_bgr.copy()))
        lista.sort(key=lambda t: t[0], reverse=True)
        del lista[self._k:]

    def mejores(self, track_id: int, n: int = 3) -> list[np.ndarray]:
        return [c for _, c in self._crops.get(track_id, [])[:n]]

    def descartar(self, track_id: int) -> None:
        self._crops.pop(track_id, None)
```

- [ ] **Step 4: Verificar que pasan**

Run: `python -m pytest tests/test_placas_video.py -v`
Expected: 14 PASS

- [ ] **Step 5: Commit**

```bash
git add modules/placas/video/best_frames.py tests/test_placas_video.py
git commit -m "feat(placas): TrackCropBuffer con score area x nitidez Laplaciana"
```

---

### Task 4: ContadorHits — confirmación de tracks en el tracker

**Files:**
- Modify: `modules/placas/video/tracker.py`
- Test: `tests/test_placas_video.py` (añadir tests)

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_placas_video.py`:

```python
# ── ContadorHits ──────────────────────────────────────────────────────────────

def test_hits_confirma_tras_minimo():
    from modules.placas.video.tracker import ContadorHits
    h = ContadorHits(min_hits=3)
    h.registrar([7])
    h.registrar([7])
    assert h.es_confirmado(7) is False
    h.registrar([7])
    assert h.es_confirmado(7) is True


def test_hits_tracks_independientes():
    from modules.placas.video.tracker import ContadorHits
    h = ContadorHits(min_hits=2)
    h.registrar([1, 2])
    h.registrar([1])
    assert h.es_confirmado(1) is True
    assert h.es_confirmado(2) is False
    assert h.es_confirmado(99) is False
```

- [ ] **Step 2: Verificar que fallan**

Run: `python -m pytest tests/test_placas_video.py -v -k hits`
Expected: FAIL con `ImportError: cannot import name 'ContadorHits'`

- [ ] **Step 3: Implementación**

En `modules/placas/video/tracker.py`, añadir después de la clase `TrackedObject`:

```python
MIN_HITS_CONFIRMACION = 3


class ContadorHits:
    """Cuenta apariciones por track_id; un track se confirma tras min_hits."""

    def __init__(self, min_hits: int = MIN_HITS_CONFIRMACION) -> None:
        self._min = min_hits
        self._hits: dict[int, int] = {}

    def registrar(self, track_ids: list[int]) -> None:
        for tid in track_ids:
            self._hits[tid] = self._hits.get(tid, 0) + 1

    def es_confirmado(self, track_id: int) -> bool:
        return self._hits.get(track_id, 0) >= self._min
```

Y en `PlacaTracker.__init__`, añadir como primera línea del cuerpo:

```python
        self.hits = ContadorHits()
```

En `PlacaTracker.update`, justo antes del `return out` final (rama supervision):

```python
        self.hits.registrar([o.track_id for o in out])
        return out
```

(El fallback sin supervision genera IDs nuevos cada frame y nunca confirma —
aceptable: supervision está instalado; el fallback solo evita un crash.)

- [ ] **Step 4: Verificar que pasan**

Run: `python -m pytest tests/test_placas_video.py -v`
Expected: 16 PASS

- [ ] **Step 5: Commit**

```bash
git add modules/placas/video/tracker.py tests/test_placas_video.py
git commit -m "feat(placas): confirmacion de tracks con ContadorHits (>=3 hits)"
```

---

### Task 5: VideoJob — eventos y contadores

**Files:**
- Modify: `modules/placas/video/schemas.py`
- Test: `tests/test_placas_video.py` (añadir tests)

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_placas_video.py`:

```python
# ── VideoJob: eventos y contadores ────────────────────────────────────────────

def test_job_summary_incluye_contadores():
    from modules.placas.video.schemas import VideoJob
    job = VideoJob(job_id="abc")
    job.vehiculos = 3
    job.placas_leidas = 2
    job.sin_lectura = 1
    job.modelo_detector = "placas"
    s = job.summary()
    assert s["vehiculos"] == 3
    assert s["placas_leidas"] == 2
    assert s["sin_lectura"] == 1
    assert s["modelo_detector"] == "placas"


def test_job_full_result_incluye_eventos():
    from modules.placas.video.schemas import VideoJob
    job = VideoJob(job_id="abc")
    job.eventos.append({"tipo": "placa", "placa": "ABC123", "ts_s": 1.0})
    fr = job.full_result()
    assert fr["eventos"][0]["placa"] == "ABC123"
```

- [ ] **Step 2: Verificar que fallan**

Run: `python -m pytest tests/test_placas_video.py -v -k job`
Expected: FAIL (`VideoJob` no tiene atributo `vehiculos` / KeyError)

- [ ] **Step 3: Implementación**

En `modules/placas/video/schemas.py`, dentro de `@dataclass class VideoJob`, añadir
después de `creado_en: float = field(default_factory=time.time)`:

```python
    eventos: list[dict] = field(default_factory=list)
    vehiculos: int = 0
    placas_leidas: int = 0
    sin_lectura: int = 0
    modelo_detector: str = ""
```

En `summary()`, añadir al dict retornado (antes de `"error"`):

```python
            "vehiculos": self.vehiculos,
            "placas_leidas": self.placas_leidas,
            "sin_lectura": self.sin_lectura,
            "modelo_detector": self.modelo_detector,
```

En `full_result()`, añadir al dict retornado:

```python
            "eventos": list(self.eventos),
```

- [ ] **Step 4: Verificar que pasan**

Run: `python -m pytest tests/test_placas_video.py tests/test_placas_routes.py -v`
Expected: todos PASS (los tests de rutas existentes no deben romperse)

- [ ] **Step 5: Commit**

```bash
git add modules/placas/video/schemas.py tests/test_placas_video.py
git commit -m "feat(placas): VideoJob con eventos, contadores y modelo_detector"
```

---

### Task 6: Detector — modelo de placas con fallback COCO + máscara amarilla

**Files:**
- Rewrite: `modules/placas/video/detector.py`
- Create: `scripts/descargar_modelo_placas.py`
- Test: `tests/test_placas_video.py` (añadir tests)

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_placas_video.py`:

```python
# ── Detector: modo placas / fallback ──────────────────────────────────────────

def test_detector_modo_fallback_sin_modelo(monkeypatch, tmp_path):
    from modules.placas.video import detector
    monkeypatch.setattr(detector, "MODELO_PLACAS", str(tmp_path / "no-existe.pt"))
    monkeypatch.setattr(detector, "_MODO", None)
    assert detector.modo() == "fallback"


def test_detector_modo_placas_con_modelo(monkeypatch, tmp_path):
    from modules.placas.video import detector
    modelo = tmp_path / "placas-yolov8n.pt"
    modelo.write_bytes(b"fake")
    monkeypatch.setattr(detector, "MODELO_PLACAS", str(modelo))
    monkeypatch.setattr(detector, "_MODO", None)
    assert detector.modo() == "placas"
```

- [ ] **Step 2: Verificar que fallan**

Run: `python -m pytest tests/test_placas_video.py -v -k detector`
Expected: FAIL con `AttributeError: module ... has no attribute 'MODELO_PLACAS'`

- [ ] **Step 3: Reescribir el detector**

Reemplazar el contenido completo de `modules/placas/video/detector.py`:

```python
# modules/placas/video/detector.py
from __future__ import annotations

import logging
import os
from typing import NamedTuple

log = logging.getLogger(__name__)

_YOLO = None
_DEPS_OK: bool | None = None
_MODO: str | None = None  # "placas" | "fallback"
MISSING_CMD = "pip install ultralytics"

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODELO_PLACAS = os.getenv(
    "PLACAS_YOLO_MODEL", os.path.join(_ROOT, "models", "placas-yolov8n.pt")
)
_MODELO_COCO = "yolov8n.pt"
_CLASES_VEHICULO = {2, 3, 5, 7}  # COCO: car, motorcycle, bus, truck


class Detection(NamedTuple):
    x1: int
    y1: int
    x2: int
    y2: int
    conf: float


def check_deps() -> bool:
    global _DEPS_OK
    if _DEPS_OK is None:
        try:
            from ultralytics import YOLO  # noqa: F401
            _DEPS_OK = True
        except ImportError:
            _DEPS_OK = False
    return _DEPS_OK


def modo() -> str:
    """"placas" si existe el modelo fine-tuned; "fallback" (COCO + máscara amarilla)."""
    global _MODO
    if _MODO is None:
        _MODO = "placas" if os.path.exists(MODELO_PLACAS) else "fallback"
        if _MODO == "fallback":
            log.warning(
                "Modelo de placas no encontrado en %s — usando fallback COCO. "
                "Ejecuta: python scripts/descargar_modelo_placas.py",
                MODELO_PLACAS,
            )
    return _MODO


def get_model():
    global _YOLO
    if _YOLO is None:
        from ultralytics import YOLO
        nombre = MODELO_PLACAS if modo() == "placas" else _MODELO_COCO
        _YOLO = YOLO(nombre)
        log.info("YOLO cargado: %s (modo %s)", nombre, modo())
    return _YOLO


def detectar_frame(frame_bgr, conf_threshold: float = 0.30) -> list[Detection]:
    """Devuelve bounding boxes de PLACAS.

    Modo "placas": el modelo detecta placas directamente.
    Modo "fallback": COCO detecta vehículos; dentro de cada bbox se localiza la
    placa con la máscara amarilla HSV; si no hay región amarilla, se devuelve el
    bbox del vehículo completo (el OCR posterior es menos preciso).
    """
    if not check_deps():
        return []
    model = get_model()
    results = model.predict(frame_bgr, conf=conf_threshold, verbose=False)
    boxes = results[0].boxes
    if modo() == "placas":
        return [
            Detection(*(int(v) for v in b.xyxy[0]), float(b.conf[0])) for b in boxes
        ]
    return _placas_fallback(frame_bgr, boxes)


def _placas_fallback(frame_bgr, boxes) -> list[Detection]:
    from modules.placas.engine import _mask_amarilla, _regiones_desde_mask

    out: list[Detection] = []
    for b in boxes:
        if int(b.cls[0]) not in _CLASES_VEHICULO:
            continue
        x1, y1, x2, y2 = (int(v) for v in b.xyxy[0])
        conf = float(b.conf[0])
        roi = frame_bgr[y1:y2, x1:x2]
        if roi.size == 0:
            continue
        regiones = _regiones_desde_mask(_mask_amarilla(roi))
        if regiones:
            rx1, ry1, rx2, ry2 = max(
                regiones, key=lambda r: (r[2] - r[0]) * (r[3] - r[1])
            )
            out.append(Detection(x1 + rx1, y1 + ry1, x1 + rx2, y1 + ry2, conf))
        else:
            out.append(Detection(x1, y1, x2, y2, conf))
    return out
```

**Nota:** verificar que `modules/placas/engine.py` expone `_mask_amarilla(bgr)` y
`_regiones_desde_mask(mask)` con regiones `(x1, y1, x2, y2)`. Si los nombres o el
formato difieren, adaptar `_placas_fallback` a los helpers reales del engine.

- [ ] **Step 4: Crear el script de descarga**

Crear `scripts/descargar_modelo_placas.py`:

```python
"""Descarga única del modelo YOLOv8 de detección de placas vehiculares.

Uso: python scripts/descargar_modelo_placas.py
Destino: models/placas-yolov8n.pt (configurable con env var PLACAS_YOLO_MODEL)
"""
import os
import sys
import urllib.request

URL = "https://huggingface.co/keremberke/yolov8n-license-plate/resolve/main/best.pt"
DEST = os.getenv(
    "PLACAS_YOLO_MODEL",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "models",
        "placas-yolov8n.pt",
    ),
)


def main() -> int:
    if os.path.exists(DEST):
        print(f"Ya existe: {DEST}")
        return 0
    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    print(f"Descargando {URL} ...")
    urllib.request.urlretrieve(URL, DEST)
    print(f"Guardado en {DEST} ({os.path.getsize(DEST) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Verificar tests y descarga del modelo**

Run: `python -m pytest tests/test_placas_video.py -v`
Expected: 20 PASS

Run: `python scripts/descargar_modelo_placas.py`
Expected: `Guardado en ...models\placas-yolov8n.pt (~6 MB)`

Run: `python -c "from ultralytics import YOLO; m = YOLO('models/placas-yolov8n.pt'); print(m.names)"`
Expected: imprime el dict de clases del modelo (una sola clase de placa, p.ej. `{0: 'license_plate'}`).
**Si la carga falla por incompatibilidad de versión de ultralytics**, buscar un modelo
YOLOv8 de placas alternativo en HuggingFace y actualizar `URL`; el resto del código
no cambia (cualquier YOLOv8 single-class de placas sirve).

- [ ] **Step 6: Añadir models/ a .gitignore y commit**

Verificar que `.gitignore` ignora los pesos (añadir si falta):

```
models/*.pt
yolov8n.pt
```

```bash
git add modules/placas/video/detector.py scripts/descargar_modelo_placas.py tests/test_placas_video.py .gitignore
git commit -m "feat(placas): detector con modelo de placas fine-tuned y fallback COCO+mascara"
```

---

### Task 7: Pipeline — loop principal con cierre de tracks y votación

**Files:**
- Rewrite: `modules/placas/video/pipeline.py`
- Delete: `modules/placas/video/ocr_cache.py`
- Test: `tests/test_placas_video.py` (test de integración con mocks)

- [ ] **Step 1: Escribir el test de integración que falla**

Añadir a `tests/test_placas_video.py`:

```python
# ── Pipeline: integración con detector y OCR mockeados ────────────────────────

def _video_sintetico(tmp_path, n_frames=30, fps=10):
    """Genera un .avi de ruido (MJPG viene incluido en opencv-python)."""
    import cv2
    import numpy as np
    path = str(tmp_path / "trafico.avi")
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), fps, (320, 240))
    rng = np.random.default_rng(7)
    for _ in range(n_frames):
        vw.write(rng.integers(0, 255, size=(240, 320, 3), dtype=np.uint8))
    vw.release()
    return path


def test_pipeline_cuenta_vehiculo_y_placa(tmp_path):
    """Un vehículo cruza el video: 1 vehículo confirmado + 1 placa votada."""
    from unittest.mock import patch
    from modules.placas.video import pipeline
    from modules.placas.video.detector import Detection
    from modules.placas.video.schemas import VideoJob

    video_path = _video_sintetico(tmp_path)
    job = VideoJob(job_id="test", video_path=video_path)

    def fake_detectar(frame, conf_threshold=0.30):
        return [Detection(60, 100, 140, 124, 0.9)]   # bbox 80×24 px estable

    with patch.object(pipeline, "yolo_ok", return_value=True), \
         patch.object(pipeline, "detectar_frame", side_effect=fake_detectar), \
         patch.object(pipeline, "_ocr_recorte", return_value=("ABC123", 0.9)):
        pipeline._procesar_video(job)

    assert job.estado == "done"
    assert job.vehiculos == 1
    assert job.placas_leidas == 1
    tipos = [e["tipo"] for e in job.eventos]
    assert "vehiculo" in tipos
    assert "placa" in tipos
    placa_ev = next(e for e in job.eventos if e["tipo"] == "placa")
    assert placa_ev["placa"] == "ABC123"


def test_pipeline_sin_lectura_cuando_ocr_falla(tmp_path):
    """Si el OCR nunca lee nada válido, el vehículo queda SIN LECTURA."""
    from unittest.mock import patch
    from modules.placas.video import pipeline
    from modules.placas.video.detector import Detection
    from modules.placas.video.schemas import VideoJob

    video_path = _video_sintetico(tmp_path)
    job = VideoJob(job_id="test2", video_path=video_path)

    def fake_detectar(frame, conf_threshold=0.30):
        return [Detection(60, 100, 140, 124, 0.9)]

    with patch.object(pipeline, "yolo_ok", return_value=True), \
         patch.object(pipeline, "detectar_frame", side_effect=fake_detectar), \
         patch.object(pipeline, "_ocr_recorte", return_value=("", 0.0)):
        pipeline._procesar_video(job)

    assert job.estado == "done"
    assert job.vehiculos == 1
    assert job.sin_lectura == 1
    assert job.placas_leidas == 0
```

- [ ] **Step 2: Verificar que fallan**

Run: `python -m pytest tests/test_placas_video.py -v -k pipeline`
Expected: FAIL con `AttributeError: ... has no attribute '_ocr_recorte'`

- [ ] **Step 3: Reescribir el pipeline**

Reemplazar el contenido completo de `modules/placas/video/pipeline.py`:

```python
# modules/placas/video/pipeline.py
from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor

import cv2

from modules.placas.engine import ALLOW, _get_reader
from . import detector
from .detector import Detection, check_deps as yolo_ok, detectar_frame
from .tracker import PlacaTracker
from .best_frames import TrackCropBuffer
from .plate_votes import PlateVoter, ConteoVideo
from .schemas import VideoJob
from .job_store import job_store

log = logging.getLogger(__name__)

# ── Configuración de rendimiento ──────────────────────────────────────────────
YOLO_EVERY_N_FRAMES = 2      # inferencia YOLO 1 de cada N frames
MAX_YOLO_DIM = 640           # resize máximo antes de YOLO
OCR_WORKERS = 2              # hilos paralelos de EasyOCR
MAX_CONCURRENT_JOBS = 2      # videos procesándose en paralelo
CIERRE_GAP_S = 1.5           # s de video sin ver el track → se cierra
OCR_PARCIAL_CADA_S = 2.0     # OCR temprano para tracks largos aún abiertos
CROP_PAD_PX = 6

_semaphore = threading.Semaphore(MAX_CONCURRENT_JOBS)
_executor = ThreadPoolExecutor(max_workers=OCR_WORKERS, thread_name_prefix="placas-ocr")


# ── OCR sobre recorte de placa ────────────────────────────────────────────────

def _ocr_recorte(crop_bgr) -> tuple[str, float]:
    """Upscale ×3 + EasyOCR con allowlist. Devuelve (texto, confianza_media)."""
    try:
        up = cv2.resize(crop_bgr, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        reader = _get_reader()
        dets = reader.readtext(up, allowlist=ALLOW, detail=1, paragraph=False)
    except Exception:
        return "", 0.0
    if not dets:
        return "", 0.0
    texto = "".join(t for _, t, _ in dets)
    conf = sum(float(c) for _, _, c in dets) / len(dets)
    return texto, conf


def _recortar(frame_bgr, x1: int, y1: int, x2: int, y2: int):
    h, w = frame_bgr.shape[:2]
    cx1, cy1 = max(0, x1 - CROP_PAD_PX), max(0, y1 - CROP_PAD_PX)
    cx2, cy2 = min(w, x2 + CROP_PAD_PX), min(h, y2 + CROP_PAD_PX)
    return frame_bgr[cy1:cy2, cx1:cx2]


def _resize_para_yolo(frame):
    h, w = frame.shape[:2]
    if max(h, w) <= MAX_YOLO_DIM:
        return frame, 1.0
    scale = MAX_YOLO_DIM / max(h, w)
    return cv2.resize(frame, (int(w * scale), int(h * scale))), scale


def _escalar_detecciones(dets: list[Detection], scale: float) -> list[Detection]:
    if scale == 1.0:
        return dets
    return [
        Detection(
            int(d.x1 / scale), int(d.y1 / scale),
            int(d.x2 / scale), int(d.y2 / scale), d.conf,
        )
        for d in dets
    ]


# ── Pipeline principal ────────────────────────────────────────────────────────

def _procesar_video(job: VideoJob) -> None:
    """Ejecutado en background thread. Modifica el job in-place."""
    cap = cv2.VideoCapture(job.video_path)
    if not cap.isOpened():
        job.estado = "error"
        job.error = "No se pudo abrir el video"
        return

    job.fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    job.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    job.duracion_s = job.total_frames / job.fps
    job.modelo_detector = detector.modo() if yolo_ok() else "sin-yolo"
    job.estado = "processing"

    tracker = PlacaTracker()
    crops = TrackCropBuffer()
    voter = PlateVoter()
    conteo = ConteoVideo()
    job.eventos = conteo.eventos  # misma lista: appends visibles para el SSE

    # track_id -> {"primer_ts", "ultimo_ts", "confirmado", "ultimo_ocr"}
    abiertos: dict[int, dict] = {}
    # OCR parciales en vuelo: alimentan el voter al completarse
    parciales: list[tuple[Future, int]] = []
    # tracks cerrados esperando sus OCRs finales: track_id -> (futures, estado)
    cierres: dict[int, tuple[list[Future], dict]] = {}

    def _drenar_parciales(wait: bool = False) -> None:
        restantes = []
        for f, tid in parciales:
            if wait or f.done():
                try:
                    texto, conf = f.result(timeout=10 if wait else 0)
                    voter.agregar_lectura(tid, texto, conf)
                except Exception as exc:
                    log.debug("OCR parcial track %d: %s", tid, exc)
            else:
                restantes.append((f, tid))
        parciales[:] = restantes

    def _iniciar_cierre(tid: int) -> None:
        est = abiertos.pop(tid)
        if not est["confirmado"]:
            crops.descartar(tid)        # track fugaz: falso positivo
            return
        futs = [_executor.submit(_ocr_recorte, c) for c in crops.mejores(tid, 3)]
        crops.descartar(tid)
        cierres[tid] = (futs, est)

    def _resolver_cierres(wait: bool = False) -> None:
        for tid in list(cierres):
            futs, est = cierres[tid]
            if not wait and not all(f.done() for f in futs):
                continue
            for f in futs:
                try:
                    texto, conf = f.result(timeout=15 if wait else 0)
                    voter.agregar_lectura(tid, texto, conf)
                except Exception as exc:
                    log.debug("OCR cierre track %d: %s", tid, exc)
            placa, tipo, conf_voto = voter.resolver(tid)
            conteo.cerrar_track(
                tid, placa, tipo, conf_voto, est["primer_ts"], est["ultimo_ts"]
            )
            del cierres[tid]

    frame_idx = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            ts_s = frame_idx / job.fps

            if frame_idx % YOLO_EVERY_N_FRAMES == 0:
                yolo_frame, scale = _resize_para_yolo(frame)
                raw = detectar_frame(yolo_frame) if yolo_ok() else []
                raw = _escalar_detecciones(raw, scale)
                tracked = tracker.update(raw, frame.shape)

                vistos = set()
                for obj in tracked:
                    vistos.add(obj.track_id)
                    est = abiertos.setdefault(
                        obj.track_id,
                        {"primer_ts": ts_s, "ultimo_ts": ts_s,
                         "confirmado": False, "ultimo_ocr": ts_s},
                    )
                    est["ultimo_ts"] = ts_s
                    crops.agregar(
                        obj.track_id, _recortar(frame, obj.x1, obj.y1, obj.x2, obj.y2)
                    )
                    if not est["confirmado"] and tracker.hits.es_confirmado(obj.track_id):
                        est["confirmado"] = True
                        conteo.confirmar_vehiculo(obj.track_id, ts_s)

                    # OCR temprano para tracks largos (feedback antes del cierre)
                    if (est["confirmado"]
                            and ts_s - est["ultimo_ocr"] >= OCR_PARCIAL_CADA_S):
                        est["ultimo_ocr"] = ts_s
                        mejores = crops.mejores(obj.track_id, 1)
                        if mejores:
                            parciales.append(
                                (_executor.submit(_ocr_recorte, mejores[0]),
                                 obj.track_id)
                            )

                # Cerrar tracks que desaparecieron hace > CIERRE_GAP_S
                for tid in [t for t, e in abiertos.items()
                            if t not in vistos and ts_s - e["ultimo_ts"] > CIERRE_GAP_S]:
                    _iniciar_cierre(tid)

            _drenar_parciales()
            _resolver_cierres()

            frame_idx += 1
            job.frames_procesados = frame_idx
            job.progreso = frame_idx / max(job.total_frames, 1)
            job.vehiculos = conteo.vehiculos
            job.placas_leidas = conteo.placas_leidas
            job.sin_lectura = conteo.sin_lectura

    finally:
        cap.release()
        for tid in list(abiertos):
            _iniciar_cierre(tid)
        _drenar_parciales(wait=True)
        _resolver_cierres(wait=True)
        job.vehiculos = conteo.vehiculos
        job.placas_leidas = conteo.placas_leidas
        job.sin_lectura = conteo.sin_lectura

    job.estado = "done"
    job.progreso = 1.0
    log.info(
        "Video job %s: %d frames, %d vehiculos, %d placas, %d sin lectura",
        job.job_id, frame_idx, job.vehiculos, job.placas_leidas, job.sin_lectura,
    )


def iniciar_procesamiento(job_id: str) -> None:
    """Lanza el pipeline en un thread daemon. Llamar desde el route tras guardar el archivo."""
    job = job_store.get(job_id)
    if not job:
        log.warning("iniciar_procesamiento: job_id %s no encontrado", job_id)
        return

    def _run() -> None:
        with _semaphore:
            try:
                _procesar_video(job)
            except Exception as exc:
                log.exception("Error fatal en job %s", job_id)
                job.estado = "error"
                job.error = str(exc)

    t = threading.Thread(target=_run, daemon=True, name=f"placas-video-{job_id[:8]}")
    t.start()
```

- [ ] **Step 4: Eliminar ocr_cache.py (código muerto)**

```bash
git rm modules/placas/video/ocr_cache.py
```

Verificar que nada más lo importa:

```bash
git grep -n "ocr_cache"
```
Expected: sin resultados en código (solo docs/ si acaso).

- [ ] **Step 5: Verificar que pasan**

Run: `python -m pytest tests/test_placas_video.py -v`
Expected: 24 PASS (los dos tests de pipeline incluidos)

Nota: el test usa ByteTrack real (supervision) — el bbox estático con conf 0.9
mantiene un track_id estable. Si `test_pipeline_cuenta_vehiculo_y_placa` falla
porque hay 2+ vehículos contados, revisar que el mock de `detectar_frame` esté
parchado sobre `pipeline.detectar_frame` (el nombre importado), no sobre
`detector.detectar_frame`.

- [ ] **Step 6: Commit**

```bash
git add modules/placas/video/pipeline.py tests/test_placas_video.py
git commit -m "feat(placas): pipeline con cierre de tracks, OCR de mejores recortes y votacion"
```

---

### Task 8: SSE con eventos incrementales

**Files:**
- Modify: `modules/placas/routes.py:119-139` (función `video_stream`)
- Test: `tests/test_placas_video.py` (añadir tests)

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_placas_video.py`:

```python
# ── Rutas: status y eventos ───────────────────────────────────────────────────

def _auth_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analista"
        sess["role"] = "analista"
        sess["name"] = "Analista Test"
    return client


def test_video_status_expone_contadores(app):
    from modules.placas.video.job_store import job_store
    job = job_store.create("")
    job.estado = "processing"
    job.vehiculos = 2
    job.placas_leidas = 1
    client = _auth_client(app)
    resp = client.get(f"/placas/video/{job.job_id}/status")
    body = resp.get_json()
    assert body["vehiculos"] == 2
    assert body["placas_leidas"] == 1
    job_store.delete(job.job_id)


def test_video_results_incluye_eventos(app):
    from modules.placas.video.job_store import job_store
    job = job_store.create("")
    job.estado = "done"
    job.eventos.append({"tipo": "placa", "placa": "ABC123", "ts_s": 2.0})
    client = _auth_client(app)
    resp = client.get(f"/placas/video/{job.job_id}/results")
    body = resp.get_json()
    assert body["eventos"][0]["placa"] == "ABC123"
    job_store.delete(job.job_id)


def test_video_stream_emite_eventos_incrementales(app):
    """El SSE incluye los eventos nuevos en cada mensaje."""
    import json as _json
    from modules.placas.video.job_store import job_store
    job = job_store.create("")
    job.estado = "done"           # un solo mensaje y cierra
    job.eventos.append({"tipo": "vehiculo", "track_id": 1, "ts_s": 0.5})
    client = _auth_client(app)
    resp = client.get(f"/placas/video/{job.job_id}/stream")
    primera_linea = resp.data.decode().split("\n")[0]
    payload = _json.loads(primera_linea.removeprefix("data: "))
    assert payload["eventos"][0]["tipo"] == "vehiculo"
    job_store.delete(job.job_id)
```

- [ ] **Step 2: Verificar que fallan**

Run: `python -m pytest tests/test_placas_video.py -v -k stream`
Expected: FAIL (`KeyError: 'eventos'` — el SSE actual solo emite summary)

(`test_video_status_expone_contadores` y `test_video_results_incluye_eventos`
ya deberían pasar gracias a Task 5 — confirmarlo.)

- [ ] **Step 3: Modificar el SSE**

En `modules/placas/routes.py`, reemplazar la función `_generate` dentro de
`video_stream` por:

```python
    def _generate():
        cursor = 0
        while True:
            nuevos = job.eventos[cursor:]
            cursor += len(nuevos)
            payload = {**job.summary(), "eventos": nuevos}
            yield f"data: {json.dumps(payload)}\n\n"
            if job.estado in ("done", "error"):
                break
            time.sleep(0.5)
```

- [ ] **Step 4: Verificar que pasan**

Run: `python -m pytest tests/test_placas_video.py tests/test_placas_routes.py -v`
Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
git add modules/placas/routes.py tests/test_placas_video.py
git commit -m "feat(placas): SSE emite eventos incrementales con cursor"
```

---

### Task 9: Frontend — upload con progreso, SSE y tabla incremental

**Files:**
- Rewrite: `static/js/placas-video.js`
- Modify: `templates/placas/video.html`

No hay tests automatizados de JS en este repo; la verificación es manual (Task 10).

- [ ] **Step 1: Reescribir el JS**

Reemplazar el contenido completo de `static/js/placas-video.js`:

```javascript
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
    countersEl.textContent = "";
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
      // El servidor cierra el stream al terminar; sólo es error si seguíamos analizando
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
```

- [ ] **Step 2: Actualizar el template**

En `templates/placas/video.html`:

**(a)** Reemplazar el bloque de progreso (líneas 77-85) por:

```html
          <!-- ── Progreso ───────────────────────────────────────────────── -->
          <div id="pv-progress-wrap" style="display:none;">
            <div class="pv-progress-bar-track">
              <div class="pv-progress-bar-fill" id="progress-bar" style="width:0%"></div>
            </div>
            <div class="pv-status-row">
              <span id="status-label" class="pv-status-label">Iniciando…</span>
              <span id="status-pct" class="pv-status-pct">0%</span>
            </div>
            <div id="pv-counters" class="pv-counters"></div>
          </div>
```

**(b)** Reemplazar el área de reproducción (líneas 92-98) — se elimina el canvas
overlay, que ya no se usa:

```html
          <!-- ── Área de reproducción ───────────────────────────────────── -->
          <div id="pv-player-wrap" style="display:none;">
            <div class="pv-player-outer">
              <video id="placas-video" class="pv-video" controls preload="metadata"></video>
            </div>
          </div>
```

**(c)** En el `<style>`, eliminar la regla `.pv-canvas { ... }` y añadir al final
(antes de `</style>`):

```css
  .pv-counters {
    margin-top: 0.5rem; font-size: 0.78rem; letter-spacing: 1px;
    color: var(--color-accent, #c8a84b); text-align: center;
  }
  .pv-placa-tag--gris {
    color: #6b7280; border-color: #374151; background: #111827;
    font-size: 0.72rem; letter-spacing: 1px;
  }
```

**(d)** Actualizar el subtítulo (línea 46):

```html
            <p class="pv-subtitle">YOLO Placas · ByteTrack · OCR con Votación · Colombia</p>
```

- [ ] **Step 3: Verificar que el suite completo sigue verde**

Run: `python -m pytest tests/ -v`
Expected: todos PASS

- [ ] **Step 4: Commit**

```bash
git add static/js/placas-video.js templates/placas/video.html
git commit -m "feat(placas): frontend de video con upload, SSE incremental y conteo en vivo"
```

---

### Task 10: Verificación end-to-end manual

**Files:** ninguno (verificación)

- [ ] **Step 1: Asegurar el modelo descargado**

Run: `python scripts/descargar_modelo_placas.py`
Expected: `Ya existe: ...` o descarga exitosa.

- [ ] **Step 2: Levantar la app**

Run: `python app.py` (verificar el entrypoint real con `ls *.py` si difiere)
Abrir `http://localhost:5000/placas/video` (login previo).

- [ ] **Step 3: Probar con un video real de tráfico**

1. Arrastrar un video de vehículos en circulación.
2. El reproductor debe aparecer de inmediato.
3. Pulsar "Iniciar análisis": fase "Subiendo video…" con % de upload, luego
   "Analizando en servidor…" con progreso real.
4. Verificar que aparecen filas con placas mientras el análisis avanza, con
   contadores `N vehículo(s) · M placa(s) leída(s)`.
5. Verificar que vehículos ilegibles aparecen como fila gris "SIN LECTURA".
6. Al llegar a 100%: mensaje "Análisis completo — …", botón "Analizar de nuevo"
   habilitado, **la página NO se congela** (bug anterior).
7. Botón "▶ ir" salta el reproductor al timestamp de la detección.
8. Probar un archivo corrupto (renombrar un .txt a .mp4): banner de error claro.

- [ ] **Step 4: Verificar logs del servidor**

En la consola del servidor debe aparecer al final:
`Video job <id>: N frames, V vehiculos, P placas, S sin lectura`
y al inicio `YOLO cargado: ...placas-yolov8n.pt (modo placas)` — si dice
`modo fallback`, el modelo no se descargó correctamente.

- [ ] **Step 5: Commit final si hubo ajustes**

```bash
git add -A
git commit -m "fix(placas): ajustes post-verificacion e2e del conteo en video"
```

---

## Self-Review (ya aplicado)

- **Cobertura del spec:** detección con modelo de placas + fallback (Task 6), tracking confirmado (Task 4), buffer de mejores recortes (Task 3), votación + fusión (Tasks 1-2), pipeline integrado (Task 7), SSE incremental (Task 8), frontend con contadores y SIN LECTURA + fix del congelamiento al 100% (Task 9), verificación manual (Task 10). `ocr_cache.py` eliminado (Task 7).
- **Tipos consistentes:** `Detection(x1,y1,x2,y2,conf)`, `_ocr_recorte → (str, float)`, `PlateVoter.resolver → (placa|None, tipo|None, float)`, `ConteoVideo.cerrar_track → dict|None`, eventos con claves `tipo`, `track_id`, `ts_s`, `placa`, `tipo_vehiculo`, `confianza` usados igual en pipeline, SSE y JS.
- **Riesgo conocido:** la URL del modelo de HuggingFace puede requerir ajuste si la carga con ultralytics falla (mitigación documentada en Task 6 Step 5). Los helpers `_mask_amarilla`/`_regiones_desde_mask` del engine deben verificarse al implementar Task 6 (nota incluida).
