# Reconocimiento de Placas Vehiculares — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir el Blueprint `/placas/` al Flask app DEMO_GAULA con upload AJAX de imagen, pipeline EasyOCR y 4 paneles diagnósticos, con graceful fallback cuando las libs ML no están instaladas.

**Architecture:** Blueprint `placas_bp` registrado en `modules/__init__.py`, con dos endpoints (`GET /placas/`, `POST /placas/analizar`). El engine importa EasyOCR/cv2 lazily con `try/except ImportError`; el singleton del reader se inicializa una vez por proceso. La UI usa `fetch()` para enviar la imagen y renderiza los resultados en el DOM sin recargar la página.

**Tech Stack:** Python 3.12, Flask 3.1.3, EasyOCR ≥1.7, OpenCV ≥4.9, PyTorch ≥2.0, numpy ≥1.24, Jinja2, vanilla JS (fetch API).

---

## File Map

| Acción | Archivo | Responsabilidad |
|--------|---------|-----------------|
| CREATE | `modules/placas/__init__.py` | Blueprint `placas_bp` |
| CREATE | `modules/placas/engine.py` | Pipeline EasyOCR + fallback |
| CREATE | `modules/placas/routes.py` | GET `/placas/` y POST `/placas/analizar` |
| MODIFY | `modules/__init__.py` | Registrar `placas_bp` |
| MODIFY | `templates/base.html` | Enlace "Placas" en nav |
| CREATE | `templates/placas/index.html` | UI drop-zone + paneles |
| MODIFY | `requirements.txt` | Agregar deps ML |
| CREATE | `tests/test_placas_routes.py` | Tests de rutas y engine |

---

## Task 1: Blueprint stub + dependencias

**Files:**
- Create: `modules/placas/__init__.py`
- Modify: `requirements.txt`

- [ ] **Step 1.1: Crear el Blueprint stub**

Crear el archivo `modules/placas/__init__.py` con exactamente este contenido:

```python
# modules/placas/__init__.py
from flask import Blueprint

placas_bp = Blueprint("placas", __name__)

from modules.placas import routes  # noqa: F401, E402
```

- [ ] **Step 1.2: Agregar dependencias ML a requirements.txt**

Agregar al final de `requirements.txt`:

```
easyocr>=1.7.0
opencv-python>=4.9.0
torch>=2.0.0
numpy>=1.24.0
```

> Nota: estas dependencias son opcionales para el resto del app. El graceful fallback del engine garantiza que el app arranca aunque no estén instaladas.

- [ ] **Step 1.3: Crear routes.py vacío temporal**

Crear `modules/placas/routes.py` con solo un comentario (se reemplaza en Task 3):

```python
# modules/placas/routes.py  — placeholder, se implementa en Task 3
```

- [ ] **Step 1.4: Verificar que el Blueprint es importable**

Ejecutar desde la raíz del proyecto:

```bash
python -c "from modules.placas import placas_bp; print(placas_bp.name)"
```

Salida esperada: `placas`

- [ ] **Step 1.5: Commit**

```bash
git add modules/placas/__init__.py modules/placas/routes.py requirements.txt
git commit -m "feat(placas): blueprint stub y dependencias ML"
```

---

## Task 2: Engine — utilidades puras + fallback (TDD)

**Files:**
- Create: `modules/placas/engine.py`
- Create: `tests/test_placas_routes.py` (sección engine)

- [ ] **Step 2.1: Escribir los tests del engine (parte pura)**

Crear `tests/test_placas_routes.py`:

```python
# tests/test_placas_routes.py
import io
from unittest.mock import patch


# ── Helpers ──────────────────────────────────────────────────────────────────

def _auth_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analista"
        sess["role"] = "analista"
        sess["name"] = "Analista Test"
    return client


def _minimal_png() -> bytes:
    """PNG de 1×1 pixel válido (base64 decodificado)."""
    import base64
    return base64.b64decode(
        b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+"
        b"M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )


# ── Tests del engine (sin deps ML) ───────────────────────────────────────────

def test_extraer_placas_carro_valido():
    from modules.placas.engine import extraer_placas_de_texto
    resultados = extraer_placas_de_texto("ABC123")
    assert any(p == "ABC123" for p, _, _ in resultados)


def test_extraer_placas_moto_valido():
    from modules.placas.engine import extraer_placas_de_texto
    resultados = extraer_placas_de_texto("XYZ12D")
    assert any(p == "XYZ12D" for p, _, _ in resultados)


def test_extraer_placas_texto_invalido():
    from modules.placas.engine import extraer_placas_de_texto
    assert extraer_placas_de_texto("HOLA MUNDO") == []


def test_extraer_placas_correccion_ocr():
    """'0' en posición de letra debe corregirse a 'O'."""
    from modules.placas.engine import extraer_placas_de_texto
    resultados = extraer_placas_de_texto("0BC123")
    placas = [p for p, _, _ in resultados]
    assert "OBC123" in placas


def test_reconocer_placa_sin_deps():
    """Sin EasyOCR instalado, devuelve {ok:False, missing_deps:True}."""
    from modules.placas import engine
    with patch.object(engine, "_check_deps", return_value=False):
        resultado = engine.reconocer_placa(b"cualquier_bytes")
    assert resultado["ok"] is False
    assert resultado["missing_deps"] is True
    assert "pip install" in resultado["install_cmd"]
```

- [ ] **Step 2.2: Ejecutar los tests — deben fallar**

```bash
pytest tests/test_placas_routes.py -v
```

Salida esperada: todos los tests **FAIL** con `ImportError` o `ModuleNotFoundError` porque `engine.py` aún no existe.

- [ ] **Step 2.3: Implementar engine.py**

Crear `modules/placas/engine.py`:

```python
# modules/placas/engine.py
from __future__ import annotations
import re
import base64
import logging

import numpy as np

_log = logging.getLogger(__name__)

_READER = None
_DEPS_OK: bool | None = None
_MISSING_CMD = "pip install easyocr opencv-python torch"

ALLOW = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
LETRAS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
DIGITOS = set("0123456789")

HSV_AMARILLO_LO = (15, 70, 110)
HSV_AMARILLO_HI = (40, 255, 255)

A2N = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1",
       "Z": "2", "A": "4", "S": "5", "G": "6", "T": "7", "B": "8"}
N2A = {"0": "O", "1": "I", "2": "Z", "4": "A",
       "5": "S", "6": "G", "7": "T", "8": "B"}
FORMATOS = [("LLLNNN", "CARRO"), ("LLLNNL", "MOTO"), ("LLLNN", "MOTO")]


# ── Comprobación de dependencias ──────────────────────────────────────────────

def _check_deps() -> bool:
    global _DEPS_OK
    if _DEPS_OK is None:
        try:
            import cv2  # noqa: F401
            import easyocr  # noqa: F401
            import torch  # noqa: F401
            _DEPS_OK = True
        except ImportError:
            _DEPS_OK = False
    return _DEPS_OK


def _get_reader():
    global _READER
    if _READER is None:
        import easyocr
        import torch
        _READER = easyocr.Reader(["en"], gpu=torch.cuda.is_available())
    return _READER


# ── Lógica pura de placas colombianas ────────────────────────────────────────

def _forzar(c: str, tipo: str) -> str:
    if tipo == "L":
        return N2A.get(c, c) if c in DIGITOS else c
    return A2N.get(c, c) if c in LETRAS else c


def _intentar_formato(ventana: str, patron: str) -> str | None:
    if len(ventana) != len(patron):
        return None
    cand = "".join(_forzar(ch, t) for ch, t in zip(ventana, patron))
    for ch, t in zip(cand, patron):
        if t == "L" and ch not in LETRAS:
            return None
        if t == "N" and ch not in DIGITOS:
            return None
    return cand


def extraer_placas_de_texto(texto: str) -> list[tuple[str, str, bool]]:
    """Extrae candidatos a placa colombiana del texto. Puro Python, sin deps ML."""
    s = re.sub(r"[^A-Z0-9]", "", texto.upper())
    encontradas: list[tuple[str, str, bool]] = []
    for patron, tipo in FORMATOS:
        L = len(patron)
        for i in range(max(1, len(s) - L + 1)):
            ventana = s[i : i + L]
            if len(ventana) < L:
                continue
            cand = _intentar_formato(ventana, patron)
            if cand:
                encontradas.append((cand, tipo, len(s) == L))
    return encontradas


# ── Utilidades de imagen (requieren cv2) ─────────────────────────────────────

def _poly2rect(poly: list) -> tuple[int, int, int, int]:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def _construir_variantes(img_bgr):
    import cv2
    vs = [cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)]
    gris = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gris)
    vs.append(clahe)
    vs.append(cv2.bilateralFilter(gris, 11, 17, 17))
    vs.append(cv2.filter2D(clahe, -1, np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])))
    return vs


def _mask_amarilla(img_bgr):
    import cv2
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(HSV_AMARILLO_LO), np.array(HSV_AMARILLO_HI))
    return cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5))
    )


def _regiones_desde_mask(mask) -> list[tuple[int, int, int, int]]:
    import cv2
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w * h > 500 and 1.5 < w / max(h, 1) < 8 and w > 40:
            out.append((x, y, x + w, y + h))
    return out


def _img_a_b64(img_bgr, max_w: int = 560) -> str:
    import cv2
    h, w = img_bgr.shape[:2]
    if w > max_w:
        img_bgr = cv2.resize(img_bgr, (max_w, int(h * max_w / w)))
    _, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return base64.b64encode(buf).decode()


def _panel_amarillo(base, mask, amarillas):
    import cv2
    m3 = np.zeros_like(base)
    m3[mask > 0] = (0, 255, 255)
    img = cv2.addWeighted(base, 0.45, m3, 0.55, 0)
    for x1, y1, x2, y2 in amarillas:
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 2)
    return img


def _panel_ocr(base, ocr_diag):
    import cv2
    img = base.copy()
    for (x1, y1, x2, y2), txt, conf, es_placa in ocr_diag:
        col = (0, 255, 0) if conf > 0.6 else (0, 200, 255) if conf > 0.35 else (90, 90, 255)
        if es_placa:
            col = (0, 255, 0)
        cv2.rectangle(img, (x1, y1), (x2, y2), col, 3 if es_placa else 2)
        cv2.putText(img, f"{int(conf * 100)}%", (x1, max(16, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2, cv2.LINE_AA)
    return img


def _panel_final(base, bbox, placa: str | None):
    import cv2
    img = base.copy()
    if bbox:
        x1, y1, x2, y2 = bbox
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.putText(img, placa or "", (x1, max(22, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)
    return img


# ── Pipeline principal ────────────────────────────────────────────────────────

def _reconocer_con_ocr(img_bgr) -> dict:
    import cv2
    reader = _get_reader()
    h, w = img_bgr.shape[:2]
    esc = 1200 / max(h, w) if max(h, w) < 1200 else 1.0
    base = (cv2.resize(img_bgr, None, fx=esc, fy=esc, interpolation=cv2.INTER_CUBIC)
            if esc > 1 else img_bgr.copy())

    candidatos: dict = {}

    def registrar(placa, tipo, conf, bbox, exacto):
        score = (conf * 100 + len(placa) * 6
                 + (12 if exacto else 0) + (6 if tipo == "CARRO" else 0))
        if placa not in candidatos or score > candidatos[placa]["score"]:
            candidatos[placa] = {"score": score, "tipo": tipo, "bbox": bbox, "conf": conf}

    # PASE A: imagen completa × 4 variantes
    todas = []
    for v in _construir_variantes(base):
        try:
            todas.extend(reader.readtext(v, allowlist=ALLOW, detail=1, paragraph=False))
        except Exception:
            pass

    ocr_diag = []
    concat = ""
    for poly, text, conf in sorted(
        todas, key=lambda d: (_poly2rect(d[0])[1] // 25, _poly2rect(d[0])[0])
    ):
        bx = _poly2rect(poly)
        s = re.sub(r"[^A-Z0-9]", "", text.upper())
        es_placa = bool(extraer_placas_de_texto(text))
        ocr_diag.append((bx, s if s else text, float(conf), es_placa))
        for placa, tipo, exacto in extraer_placas_de_texto(text):
            registrar(placa, tipo, conf, bx, exacto)
        concat += s
    for placa, tipo, _ in extraer_placas_de_texto(concat):
        registrar(placa, tipo, 0.45, (0, 0, base.shape[1], base.shape[0]), False)

    # Diagnóstico de color amarillo
    mask = _mask_amarilla(base)
    amarillas = _regiones_desde_mask(mask)

    # PASE B: recortes en alta resolución
    regiones = [_poly2rect(p) for p, _, _ in todas] + amarillas
    for x1, y1, x2, y2 in regiones[:12]:
        pad = 8
        cx1, cy1 = max(0, x1 - pad), max(0, y1 - pad)
        cx2, cy2 = min(base.shape[1], x2 + pad), min(base.shape[0], y2 + pad)
        crop = base[cy1:cy2, cx1:cx2]
        if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 16:
            continue
        up = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        gris = cv2.createCLAHE(3.0, (8, 8)).apply(
            cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
        )
        for var in (up, gris):
            try:
                dets = reader.readtext(var, allowlist=ALLOW, detail=1, paragraph=False)
            except Exception:
                dets = []
            sub = ""
            for _, text2, conf2 in dets:
                s2 = re.sub(r"[^A-Z0-9]", "", text2.upper())
                for placa, tipo, exacto in extraer_placas_de_texto(text2):
                    registrar(placa, tipo, conf2 + 0.05, (cx1, cy1, cx2, cy2), exacto)
                sub += s2
            for placa, tipo, _ in extraer_placas_de_texto(sub):
                registrar(placa, tipo, 0.5, (cx1, cy1, cx2, cy2), False)

    # Construir paneles base64
    p1 = _img_a_b64(base)
    p2 = _img_a_b64(_panel_amarillo(base, mask, amarillas))
    p3 = _img_a_b64(_panel_ocr(base, ocr_diag))

    if not candidatos:
        p4 = _img_a_b64(_panel_final(base, None, None))
        return {"ok": True, "placa": None, "paneles": [p1, p2, p3, p4], "alternativas": []}

    orden = sorted(candidatos.items(), key=lambda kv: kv[1]["score"], reverse=True)
    mejor, info = orden[0]
    p4 = _img_a_b64(_panel_final(base, info["bbox"], mejor))

    return {
        "ok": True,
        "placa": mejor,
        "tipo": info["tipo"],
        "confianza": round(float(info["conf"]), 2),
        "paneles": [p1, p2, p3, p4],
        "alternativas": [
            [p, d["tipo"], round(float(d["conf"]), 2)] for p, d in orden[1:6]
        ],
    }


def reconocer_placa(img_bytes: bytes) -> dict:
    """Punto de entrada público. Recibe bytes raw de la imagen."""
    if not _check_deps():
        return {"ok": False, "missing_deps": True, "install_cmd": _MISSING_CMD}
    try:
        import cv2
        arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return {"ok": False, "error": "Imagen ilegible"}
        return _reconocer_con_ocr(img)
    except Exception:
        _log.exception("Error en reconocer_placa")
        return {"ok": False, "error": "Error interno"}
```

- [ ] **Step 2.4: Ejecutar los tests — deben pasar**

```bash
pytest tests/test_placas_routes.py::test_extraer_placas_carro_valido \
       tests/test_placas_routes.py::test_extraer_placas_moto_valido \
       tests/test_placas_routes.py::test_extraer_placas_texto_invalido \
       tests/test_placas_routes.py::test_extraer_placas_correccion_ocr \
       tests/test_placas_routes.py::test_reconocer_placa_sin_deps \
       -v
```

Salida esperada: 5 tests **PASSED**.

- [ ] **Step 2.5: Commit**

```bash
git add modules/placas/engine.py tests/test_placas_routes.py
git commit -m "feat(placas): engine EasyOCR con fallback + tests de lógica pura"
```

---

## Task 3: Routes + registro + navegación (TDD)

**Files:**
- Modify: `modules/placas/routes.py` (reemplaza el placeholder vacío)
- Modify: `modules/__init__.py` (líneas 35–62)
- Modify: `templates/base.html` (líneas 29–48)
- Modify: `tests/test_placas_routes.py` (agregar sección de rutas)

- [ ] **Step 3.1: Agregar los tests de rutas a test_placas_routes.py**

Agregar al final de `tests/test_placas_routes.py`:

```python
# ── Tests de rutas ────────────────────────────────────────────────────────────

def test_placas_index_redirige_sin_login(app):
    client = app.test_client()
    resp = client.get("/placas/")
    assert resp.status_code == 302


def test_placas_index_renderiza_con_login(app):
    client = _auth_client(app)
    resp = client.get("/placas/")
    assert resp.status_code == 200
    assert b"placa" in resp.data.lower() or b"Placa" in resp.data


def test_analizar_sin_archivo_retorna_400(app):
    client = _auth_client(app)
    resp = client.post("/placas/analizar")
    assert resp.status_code == 400


def test_analizar_mime_no_imagen_retorna_400(app):
    client = _auth_client(app)
    data = {"imagen": (io.BytesIO(b"contenido"), "archivo.txt", "text/plain")}
    resp = client.post("/placas/analizar", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_analizar_sin_deps_retorna_json_missing_deps(app):
    from modules.placas import engine
    client = _auth_client(app)
    with patch.object(engine, "_check_deps", return_value=False):
        data = {"imagen": (io.BytesIO(_minimal_png()), "test.png", "image/png")}
        resp = client.post("/placas/analizar", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is False
    assert body["missing_deps"] is True


def test_analizar_redirige_sin_login(app):
    client = app.test_client()
    data = {"imagen": (io.BytesIO(_minimal_png()), "test.png", "image/png")}
    resp = client.post("/placas/analizar", data=data, content_type="multipart/form-data")
    assert resp.status_code == 302
```

- [ ] **Step 3.2: Ejecutar — deben fallar con 404**

```bash
pytest tests/test_placas_routes.py -k "index or analizar" -v
```

Salida esperada: todos **FAIL** con `AssertionError` porque `/placas/` devuelve 404 (blueprint no registrado aún).

- [ ] **Step 3.3: Implementar routes.py**

Reemplazar el contenido de `modules/placas/routes.py`:

```python
# modules/placas/routes.py
from flask import jsonify, render_template, request

from modules.auth.decorators import login_required
from modules.placas import engine, placas_bp


@placas_bp.route("/")
@login_required
def index():
    return render_template("placas/index.html")


@placas_bp.route("/analizar", methods=["POST"])
@login_required
def analizar():
    if "imagen" not in request.files:
        return jsonify({"ok": False, "error": "No se envió archivo"}), 400

    archivo = request.files["imagen"]
    if not archivo.mimetype.startswith("image/"):
        return jsonify({"ok": False, "error": "El archivo no es una imagen"}), 400

    resultado = engine.reconocer_placa(archivo.read())
    return jsonify(resultado)
```

- [ ] **Step 3.4: Registrar el blueprint en modules/__init__.py**

En `modules/__init__.py`, agregar al bloque de imports de `_register_blueprints` (después de `from modules.chatbot import chatbot_bp`):

```python
    from modules.placas import placas_bp
```

Y agregar al bloque de `register_blueprint` (después de `app.register_blueprint(chatbot_bp)`):

```python
    app.register_blueprint(placas_bp, url_prefix="/placas")
```

- [ ] **Step 3.5: Agregar enlace "Placas" en templates/base.html**

En `templates/base.html`, dentro del bloque `<nav>`, agregar el enlace en **ambas** ramas del `{% if %}`/`{% else %}`, justo antes de cada `<a href="{{ url_for('auth.logout') }}">Cerrar sesión</a>`:

```html
            <a href="{{ url_for('placas.index') }}">Placas</a>
```

- [ ] **Step 3.6: Crear template placeholder mínimo**

Crear `templates/placas/index.html` con solo:

```html
{% extends "base.html" %}
{% block contenido %}
<h1>Reconocimiento de Placas</h1>
{% endblock %}
```

> El template completo se reemplaza en Task 4.

- [ ] **Step 3.7: Ejecutar todos los tests**

```bash
pytest tests/test_placas_routes.py -v
```

Salida esperada: todos los 11 tests **PASSED**.

- [ ] **Step 3.8: Commit**

```bash
git add modules/placas/routes.py modules/__init__.py templates/base.html templates/placas/index.html tests/test_placas_routes.py
git commit -m "feat(placas): rutas, registro de blueprint y enlace de navegación"
```

---

## Task 4: Template completo

**Files:**
- Modify: `templates/placas/index.html` (reemplaza el placeholder)

- [ ] **Step 4.1: Reemplazar el template con la UI completa**

Reemplazar `templates/placas/index.html` con:

```html
{% extends "base.html" %}
{% block contenido %}
<section class="placas-container">

  <!-- Encabezado -->
  <div class="placas-header">
    <h2 class="placas-title">RECONOCIMIENTO DE PLACAS</h2>
    <p class="placas-subtitle">Motor visual EasyOCR · Detección HSV · Colombia</p>
  </div>

  <!-- Drop-zone -->
  <div class="placas-upload-area" id="drop-zone">
    <div class="placas-drop-inner" id="drop-inner">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
      </svg>
      <p>Arrastra una imagen aquí o <label for="imagen-input" class="placas-browse-link">selecciona un archivo</label></p>
      <p class="placas-hint">JPG, PNG — máximo 10 MB</p>
    </div>
    <img id="preview-img" class="placas-preview" style="display:none;" alt="Vista previa">
    <input type="file" id="imagen-input" accept="image/*" style="display:none;">
  </div>

  <!-- Botón -->
  <button id="btn-analizar" class="placas-btn" disabled>Analizar</button>

  <!-- Spinner -->
  <div id="spinner" class="placas-spinner" style="display:none;">
    <div class="placas-spinner-ring"></div>
    <span>Procesando imagen...</span>
  </div>

  <!-- Banner: dependencias faltantes -->
  <div id="banner-deps" class="placas-banner placas-banner--warn" style="display:none;">
    <strong>Dependencias ML no instaladas.</strong>
    Ejecuta en el servidor:
    <code id="install-cmd"></code>
  </div>

  <!-- Banner: error genérico -->
  <div id="banner-error" class="placas-banner placas-banner--error" style="display:none;">
    <span id="error-msg"></span>
  </div>

  <!-- Resultados -->
  <div id="resultados" style="display:none;">

    <!-- Placa extraída -->
    <div class="placas-resultado-box">
      <div class="placas-resultado-label">PLACA EXTRAÍDA</div>
      <div class="placas-resultado-texto" id="placa-texto">—</div>
      <div class="placas-resultado-meta" id="placa-meta"></div>
    </div>

    <!-- Grid 2×2 paneles -->
    <div class="placas-grid">
      <div class="placas-panel">
        <div class="placas-panel-label">1 · IMAGEN ORIGINAL</div>
        <img id="panel-1" class="placas-panel-img" alt="Imagen original">
      </div>
      <div class="placas-panel">
        <div class="placas-panel-label">2 · COLOR AMARILLO HSV</div>
        <img id="panel-2" class="placas-panel-img" alt="Máscara amarilla HSV">
      </div>
      <div class="placas-panel">
        <div class="placas-panel-label">3 · LECTURAS OCR + %</div>
        <img id="panel-3" class="placas-panel-img" alt="Lecturas OCR">
      </div>
      <div class="placas-panel">
        <div class="placas-panel-label">4 · RECONOCIMIENTO FINAL</div>
        <img id="panel-4" class="placas-panel-img" alt="Resultado final">
      </div>
    </div>

    <!-- Alternativas -->
    <div id="alternativas-section" style="display:none;">
      <div class="placas-alt-label">CANDIDATOS ALTERNATIVOS</div>
      <ul id="alternativas-lista" class="placas-alt-lista"></ul>
    </div>

  </div>

</section>

<style>
.placas-container { max-width: 860px; margin: 2rem auto; padding: 0 1rem; font-family: 'IBM Plex Mono', monospace; }
.placas-header { text-align: center; margin-bottom: 1.5rem; }
.placas-title { font-size: 1.2rem; letter-spacing: 4px; color: var(--color-accent, #c8a84b); margin: 0; }
.placas-subtitle { font-size: 0.72rem; letter-spacing: 2px; color: #6b7280; margin: 0.3rem 0 0; }

.placas-upload-area {
  border: 2px dashed var(--color-accent, #c8a84b);
  border-radius: 10px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s;
}
.placas-upload-area.drag-over { border-color: #fff; background: rgba(200,168,75,0.05); }
.placas-drop-inner { color: #9ca3af; font-size: 0.85rem; }
.placas-browse-link { color: var(--color-accent, #c8a84b); cursor: pointer; text-decoration: underline; }
.placas-hint { font-size: 0.72rem; color: #4b5563; margin-top: 0.4rem; }
.placas-preview { max-width: 100%; max-height: 280px; border-radius: 6px; margin-top: 0.8rem; }

.placas-btn {
  display: block;
  margin: 1rem auto 0;
  padding: 0.6rem 2.5rem;
  background: var(--color-accent, #c8a84b);
  color: #0d1117;
  border: none;
  border-radius: 6px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 2px;
  cursor: pointer;
  transition: opacity 0.2s;
}
.placas-btn:disabled { opacity: 0.35; cursor: not-allowed; }

.placas-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  margin-top: 1.2rem;
  color: #9ca3af;
  font-size: 0.8rem;
}
.placas-spinner-ring {
  width: 24px; height: 24px;
  border: 3px solid #1f2937;
  border-top-color: var(--color-accent, #c8a84b);
  border-radius: 50%;
  animation: placas-spin 0.8s linear infinite;
}
@keyframes placas-spin { to { transform: rotate(360deg); } }

.placas-banner {
  margin-top: 1rem;
  padding: 0.8rem 1rem;
  border-radius: 6px;
  font-size: 0.8rem;
}
.placas-banner--warn { background: #1c1506; border: 1px solid #854d0e; color: #fde68a; }
.placas-banner--warn code { display: block; margin-top: 0.4rem; color: #fff; background: #0d1117; padding: 0.3rem 0.6rem; border-radius: 4px; }
.placas-banner--error { background: #1a0a0a; border: 1px solid #7f1d1d; color: #fca5a5; }

.placas-resultado-box {
  text-align: center;
  margin: 1.5rem auto;
  padding: 1rem 2rem;
  border: 2px solid var(--color-accent, #c8a84b);
  border-radius: 10px;
  max-width: 360px;
  background: linear-gradient(135deg, #1a1500, #2d2500);
}
.placas-resultado-label { font-size: 0.68rem; letter-spacing: 3px; color: var(--color-accent, #c8a84b); }
.placas-resultado-texto { font-size: 2.4rem; font-weight: 900; letter-spacing: 8px; color: #fff; margin: 0.3rem 0; }
.placas-resultado-meta { font-size: 0.72rem; color: #9ca3af; }

.placas-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 1rem; }
.placas-panel-label { font-size: 0.62rem; letter-spacing: 2px; color: #4b5563; margin-bottom: 5px; }
.placas-panel-img { width: 100%; border-radius: 6px; border: 1px solid #1f2937; }

.placas-alt-label { font-size: 0.66rem; letter-spacing: 2px; color: #4b5563; margin: 1rem 0 0.4rem; }
.placas-alt-lista { list-style: none; padding: 0; margin: 0; }
.placas-alt-lista li { font-size: 0.78rem; color: #9ca3af; padding: 0.2rem 0; border-bottom: 1px solid #1f2937; }

@media (max-width: 600px) { .placas-grid { grid-template-columns: 1fr; } }
</style>

<script>
(function () {
  const dropZone    = document.getElementById("drop-zone");
  const input       = document.getElementById("imagen-input");
  const preview     = document.getElementById("preview-img");
  const dropInner   = document.getElementById("drop-inner");
  const btnAnalizar = document.getElementById("btn-analizar");
  const spinner     = document.getElementById("spinner");
  const bannerDeps  = document.getElementById("banner-deps");
  const bannerErr   = document.getElementById("banner-error");
  const resultados  = document.getElementById("resultados");
  const placaTexto  = document.getElementById("placa-texto");
  const placaMeta   = document.getElementById("placa-meta");
  const altSec      = document.getElementById("alternativas-section");
  const altLista    = document.getElementById("alternativas-lista");

  let archivoSeleccionado = null;

  function mostrarPreview(file) {
    archivoSeleccionado = file;
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
    dropInner.style.display = "none";
    btnAnalizar.disabled = false;
  }

  function resetearResultados() {
    bannerDeps.style.display = "none";
    bannerErr.style.display  = "none";
    resultados.style.display = "none";
    altSec.style.display     = "none";
    altLista.innerHTML       = "";
  }

  dropZone.addEventListener("click", () => input.click());

  input.addEventListener("change", () => {
    if (input.files[0]) mostrarPreview(input.files[0]);
  });

  dropZone.addEventListener("dragover",  (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
  dropZone.addEventListener("dragleave", ()  => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith("image/")) mostrarPreview(f);
  });

  btnAnalizar.addEventListener("click", async () => {
    if (!archivoSeleccionado) return;
    resetearResultados();
    spinner.style.display = "flex";
    btnAnalizar.disabled = true;

    const formData = new FormData();
    formData.append("imagen", archivoSeleccionado);

    try {
      const resp = await fetch("{{ url_for('placas.analizar') }}", {
        method: "POST", body: formData,
      });
      const data = await resp.json();

      spinner.style.display = "none";
      btnAnalizar.disabled = false;

      if (!data.ok) {
        if (data.missing_deps) {
          document.getElementById("install-cmd").textContent = data.install_cmd;
          bannerDeps.style.display = "block";
        } else {
          document.getElementById("error-msg").textContent = data.error || "Error desconocido";
          bannerErr.style.display = "block";
        }
        return;
      }

      ["panel-1","panel-2","panel-3","panel-4"].forEach((id, i) => {
        const el = document.getElementById(id);
        if (el && data.paneles && data.paneles[i])
          el.src = "data:image/jpeg;base64," + data.paneles[i];
      });

      placaTexto.textContent = data.placa || "Sin placa válida";
      placaMeta.textContent  = data.placa
        ? (data.tipo || "") + " · confianza " + Math.round((data.confianza || 0) * 100) + "%"
        : "No se detectó una placa colombiana";

      if (data.alternativas && data.alternativas.length > 0) {
        data.alternativas.forEach(([p, tipo, conf]) => {
          const li = document.createElement("li");
          li.textContent = p + " — " + tipo + " (" + Math.round(conf * 100) + "%)";
          altLista.appendChild(li);
        });
        altSec.style.display = "block";
      }

      resultados.style.display = "block";

    } catch (err) {
      spinner.style.display = "none";
      btnAnalizar.disabled = false;
      document.getElementById("error-msg").textContent = "Error de red: " + err.message;
      bannerErr.style.display = "block";
    }
  });
})();
</script>
{% endblock %}
```

- [ ] **Step 4.2: Ejecutar todos los tests**

```bash
pytest tests/test_placas_routes.py -v
```

Salida esperada: todos **PASSED**.

- [ ] **Step 4.3: Smoke test manual**

Iniciar el servidor:
```bash
python app.py
```

Abrir `http://localhost:5000`, iniciar sesión con `analista` / `Analista147*`, hacer clic en **Placas** en el menú y verificar:
- La drop-zone aparece con el ícono de upload
- Drag & drop y click-para-seleccionar funcionan
- Al seleccionar una imagen aparece el preview y se habilita el botón "Analizar"
- El spinner aparece al hacer clic en Analizar
- Si las libs ML no están instaladas, aparece el banner amarillo con el comando `pip install easyocr opencv-python torch`

- [ ] **Step 4.4: Commit final**

```bash
git add templates/placas/index.html
git commit -m "feat(placas): template completo con drop-zone, AJAX y 4 paneles diagnósticos"
```

---

## Nota: límite de tamaño de archivos

Verificar si `modules/config.py` ya define `MAX_CONTENT_LENGTH`. Si no existe, agregar:

```python
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
```

Flask devuelve automáticamente HTTP 413 cuando se supera este límite.

---

## Self-Review

**Cobertura del spec:**
- ✅ Upload de imagen → engine.reconocer_placa() → JSON
- ✅ 4 paneles diagnósticos en base64
- ✅ AJAX sin recarga (fetch + spinner)
- ✅ Graceful fallback si ML no instalado (banner + install_cmd)
- ✅ `@login_required` en ambos endpoints
- ✅ Validación MIME (400 si no es imagen)
- ✅ Singleton del reader
- ✅ Registro en `_register_blueprints` + enlace en `base.html`
- ✅ Estilo consistente con tema institucional (IBM Plex Mono, color-accent)
- ✅ Tests de rutas + lógica pura

**Tipo/firma consistencia:**
- `reconocer_placa(img_bytes: bytes) -> dict` — usada igual en engine.py y routes.py ✅
- `extraer_placas_de_texto(texto: str) -> list[tuple[str, str, bool]]` — usada en tests ✅
- `_check_deps()` — patcheada con `patch.object(engine, "_check_deps", ...)` en tests ✅
- Campo `paneles` en JSON es `list[str]` de 4 elementos — el JS los indexa por posición ✅

**Sin placeholders:** todas las secciones tienen código completo ✅
