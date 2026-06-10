# modules/placas/engine.py
from __future__ import annotations
import re
import base64
import logging

import numpy as np

_log = logging.getLogger(__name__)

_READER = None
_DEPS_OK: bool | None = None
_MISSING_CMD = "pip install easyocr opencv-python-headless torch"

ALLOW = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
LETRAS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
DIGITOS = set("0123456789")

HSV_AMARILLO_LO = (15, 70, 110)
HSV_AMARILLO_HI = (40, 255, 255)

A2N = {"O": "0", "Q": "0", "I": "1", "L": "1",
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
