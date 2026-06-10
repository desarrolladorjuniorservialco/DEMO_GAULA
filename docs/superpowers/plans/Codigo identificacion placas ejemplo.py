
#  MOTOR VISUAL DE RECONOCIMIENTO DE PLACAS (EasyOCR)

!pip install easyocr opencv-python-headless -q

import cv2, re, base64
import numpy as np
import easyocr, torch
from IPython.display import display, HTML

print("⏳ Cargando motor de reconocimiento EasyOCR...")
reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
print(f"✅ Motor listo (GPU: {torch.cuda.is_available()})")

ALLOW   = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
LETRAS  = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
DIGITOS = set("0123456789")

# ── Parámetros HSV del amarillo de la placa colombiana ──────
HSV_AMARILLO_LO = (15, 70, 110)
HSV_AMARILLO_HI = (40, 255, 255)

A2N = {'O':'0','Q':'0','D':'0','I':'1','L':'1','Z':'2','A':'4','S':'5','G':'6','T':'7','B':'8'}
N2A = {'0':'O','1':'I','2':'Z','4':'A','5':'S','6':'G','7':'T','8':'B'}
FORMATOS = [("LLLNNN", "CARRO"), ("LLLNNL", "MOTO"), ("LLLNN", "MOTO")]


def _forzar(c, tipo):
    if tipo == 'L':
        return N2A.get(c, c) if c in DIGITOS else c
    return A2N.get(c, c) if c in LETRAS else c


def _intentar_formato(ventana, patron):
    if len(ventana) != len(patron):
        return None
    cand = "".join(_forzar(ch, t) for ch, t in zip(ventana, patron))
    for ch, t in zip(cand, patron):
        if t == 'L' and ch not in LETRAS:  return None
        if t == 'N' and ch not in DIGITOS: return None
    return cand


def extraer_placas_de_texto(texto):
    s = re.sub(r'[^A-Z0-9]', '', texto.upper())
    encontradas = []
    for patron, tipo in FORMATOS:
        L = len(patron)
        for i in range(0, max(1, len(s) - L + 1)):
            ventana = s[i:i + L]
            if len(ventana) < L:
                continue
            cand = _intentar_formato(ventana, patron)
            if cand:
                encontradas.append((cand, tipo, len(s) == L))
    return encontradas


def _poly2rect(poly):
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def _construir_variantes(img_bgr):
    vs   = [cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)]
    gris = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gris)
    vs.append(clahe)
    vs.append(cv2.bilateralFilter(gris, 11, 17, 17))
    vs.append(cv2.filter2D(clahe, -1, np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])))
    return vs


def _mask_amarilla(img_bgr):
    hsv  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(HSV_AMARILLO_LO), np.array(HSV_AMARILLO_HI))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5)))
    return mask


def _regiones_desde_mask(mask):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w * h > 500 and 1.5 < w / max(h, 1) < 8 and w > 40:
            out.append((x, y, x + w, y + h))
    return out


def reconocer_placa(img_bgr):
    h, w = img_bgr.shape[:2]
    esc  = 1200 / max(h, w) if max(h, w) < 1200 else 1.0
    base = cv2.resize(img_bgr, None, fx=esc, fy=esc,
                      interpolation=cv2.INTER_CUBIC) if esc > 1 else img_bgr.copy()

    candidatos = {}
    def registrar(placa, tipo, conf, bbox, exacto):
        score = conf * 100 + len(placa) * 6 + (12 if exacto else 0) + (6 if tipo == "CARRO" else 0)
        if placa not in candidatos or score > candidatos[placa]["score"]:
            candidatos[placa] = {"score": score, "tipo": tipo, "bbox": bbox, "conf": conf}

    # ── PASE A: imagen completa, varias variantes ──
    todas = []
    for v in _construir_variantes(base):
        try:
            todas.extend(reader.readtext(v, allowlist=ALLOW, detail=1, paragraph=False))
        except Exception:
            pass

    ocr_diag = []
    concat = ""
    for poly, text, conf in sorted(todas, key=lambda d: (_poly2rect(d[0])[1] // 25,
                                                         _poly2rect(d[0])[0])):
        bx = _poly2rect(poly)
        s  = re.sub(r'[^A-Z0-9]', '', text.upper())
        es_placa = bool(extraer_placas_de_texto(text))
        ocr_diag.append((bx, s if s else text, float(conf), es_placa))
        for placa, tipo, exacto in extraer_placas_de_texto(text):
            registrar(placa, tipo, conf, bx, exacto)
        concat += s
    for placa, tipo, _ in extraer_placas_de_texto(concat):
        registrar(placa, tipo, 0.45, (0, 0, base.shape[1], base.shape[0]), False)

    # ── Diagnóstico de color amarillo ──
    mask      = _mask_amarilla(base)
    amarillas = _regiones_desde_mask(mask)

    # ── PASE B: recortes en alta resolución ──
    regiones = [_poly2rect(p) for p, _, _ in todas] + amarillas
    for (x1, y1, x2, y2) in regiones[:12]:
        pad = 8
        cx1, cy1 = max(0, x1 - pad), max(0, y1 - pad)
        cx2, cy2 = min(base.shape[1], x2 + pad), min(base.shape[0], y2 + pad)
        crop = base[cy1:cy2, cx1:cx2]
        if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 16:
            continue
        up   = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        gris = cv2.createCLAHE(3.0, (8, 8)).apply(cv2.cvtColor(up, cv2.COLOR_BGR2GRAY))
        for var in (up, gris):
            try:
                dets = reader.readtext(var, allowlist=ALLOW, detail=1, paragraph=False)
            except Exception:
                dets = []
            sub = ""
            for _, text2, conf2 in dets:
                s2 = re.sub(r'[^A-Z0-9]', '', text2.upper())
                for placa, tipo, exacto in extraer_placas_de_texto(text2):
                    registrar(placa, tipo, conf2 + 0.05, (cx1, cy1, cx2, cy2), exacto)
                sub += s2
            for placa, tipo, _ in extraer_placas_de_texto(sub):
                registrar(placa, tipo, 0.5, (cx1, cy1, cx2, cy2), False)

    diag = {"mask": mask, "amarillas": amarillas, "ocr": ocr_diag}

    if not candidatos:
        return {"placa": None, "base": base, "alternativas": [], "diag": diag, "bbox": None}

    orden = sorted(candidatos.items(), key=lambda kv: kv[1]["score"], reverse=True)
    mejor, info = orden[0]
    return {
        "placa": mejor, "tipo": info["tipo"], "conf": info["conf"], "bbox": info["bbox"],
        "base": base, "diag": diag,
        "alternativas": [(p, d["tipo"], round(d["conf"], 2)) for p, d in orden[1:6]],
    }


def _img_a_b64(img_bgr, max_w=560):
    h, w = img_bgr.shape[:2]
    if w > max_w:
        img_bgr = cv2.resize(img_bgr, (max_w, int(h * max_w / w)))
    _, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return base64.b64encode(buf).decode()

print("✅ Motor visual de placas cargado")

#   MOTOR VISUAL — VER CÓMO RECONOCE PASO A PASO

from google.colab import files
from IPython.display import display, HTML, clear_output

# ─── Constructores de paneles visuales ──────────────────────
def _panel_amarillo(base, mask, amarillas):
    m3 = np.zeros_like(base)
    m3[mask > 0] = (0, 255, 255)
    img = cv2.addWeighted(base, 0.45, m3, 0.55, 0)
    for (x1, y1, x2, y2) in amarillas:
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 2)
    return img

def _panel_ocr(base, ocr):
    img = base.copy()
    for (x1, y1, x2, y2), txt, conf, es_placa in ocr:
        col = (0, 255, 0) if conf > 0.6 else (0, 200, 255) if conf > 0.35 else (90, 90, 255)
        if es_placa:
            col = (0, 255, 0)
        cv2.rectangle(img, (x1, y1), (x2, y2), col, 2 if not es_placa else 3)
        cv2.putText(img, f"{int(conf*100)}%", (x1, max(16, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2, cv2.LINE_AA)
    return img

def _panel_final(base, bbox, placa):
    img = base.copy()
    if bbox:
        x1, y1, x2, y2 = bbox
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.putText(img, placa or "", (x1, max(22, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)
    return img


display(HTML("""
<div style="font-family:'Courier New',monospace;background:#070d1a;
            border:2px solid #00ffe7;border-radius:14px;padding:22px;
            text-align:center;max-width:640px;margin:8px auto;
            box-shadow:0 0 30px #00ffe725">
  <div style="font-size:1.4em;color:#00ffe7;letter-spacing:5px;font-weight:bold;
              text-shadow:0 0 18px #00ffe7">◈ MOTOR VISUAL DE PLACAS ◈</div>
  <div style="color:#4a8fa8;font-size:.78em;letter-spacing:3px;margin-top:6px">
    DETECCIÓN · COLOR HSV · OCR · PORCENTAJES
  </div>
</div>"""))

subidos = files.upload()

for nombre, contenido in subidos.items():
    arr = np.frombuffer(contenido, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    clear_output(wait=True)
    if img is None:
        display(HTML('<div style="color:#ff4d6d;font-family:monospace">⚠ Imagen ilegible.</div>'))
        continue

    display(HTML('<div style="color:#00ffe7;font-family:monospace;padding:10px">⏳ Procesando motor visual...</div>'))
    r = reconocer_placa(img)
    clear_output(wait=True)

    base = r["base"]; d = r["diag"]
    p1 = _img_a_b64(base)
    p2 = _img_a_b64(_panel_amarillo(base, d["mask"], d["amarillas"]))
    p3 = _img_a_b64(_panel_ocr(base, d["ocr"]))
    p4 = _img_a_b64(_panel_final(base, r["bbox"], r.get("placa")))

    # Barras de confianza de cada lectura (dedup por texto, mayor conf)
    vistos = {}
    for bx, txt, conf, es_placa in d["ocr"]:
        if not txt:
            continue
        if txt not in vistos or conf > vistos[txt][0]:
            vistos[txt] = (conf, es_placa)
    barras = ""
    for txt, (conf, es_placa) in sorted(vistos.items(), key=lambda x: x[1][0], reverse=True)[:8]:
        col = "#00ff80" if es_placa else "#00ffe7" if conf > 0.5 else "#ff8800"
        tag = ' <span style="color:#00ff80">◀ PLACA</span>' if es_placa else ""
        barras += f"""
        <div style="margin:5px 0">
          <div style="display:flex;justify-content:space-between;font-size:.78em;color:#cde">
            <span>{txt}{tag}</span><span style="color:{col}">{int(conf*100)}%</span>
          </div>
          <div style="background:#0d1b2a;border-radius:4px;height:7px;overflow:hidden">
            <div style="width:{int(conf*100)}%;height:100%;background:{col}"></div>
          </div>
        </div>"""

    placa_html = (f"""<div style="font-size:2.6em;font-weight:900;color:#fff;letter-spacing:8px;
                       text-shadow:0 0 14px #ffe500">{r['placa']}</div>
                  <div style="color:#9ad;font-size:.75em">{r['tipo']} · confianza {int(r['conf']*100)}%</div>"""
                  if r["placa"] else
                  '<div style="color:#ff4d6d;font-size:1.1em">⚠ Sin placa válida</div>')

    paneles = [
        ("1 · IMAGEN ORIGINAL", p1, "#4a8fa8"),
        (f"2 · COLOR AMARILLO HSV  ·  H{HSV_AMARILLO_LO[0]}-{HSV_AMARILLO_HI[0]} S{HSV_AMARILLO_LO[1]}+ V{HSV_AMARILLO_LO[2]}+", p2, "#ffe500"),
        ("3 · LECTURAS OCR + %", p3, "#00ffe7"),
        ("4 · RECONOCIMIENTO FINAL", p4, "#00ff80"),
    ]
    grid = ""
    for i, (lbl, b64, col) in enumerate(paneles):
        grid += f"""
        <div style="animation:fadein .6s ease both;animation-delay:{i*0.45}s">
          <div style="color:{col};font-size:.66em;letter-spacing:2px;margin-bottom:5px">{lbl}</div>
          <img src="data:image/jpeg;base64,{b64}"
               style="width:100%;border-radius:8px;border:1px solid {col}55"/>
        </div>"""

    display(HTML(f"""
    <style>@keyframes fadein{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}</style>
    <div style="font-family:'Courier New',monospace;background:#070d1a;border:1px solid #1a3a5c;
                border-radius:14px;padding:20px;max-width:860px;margin:8px auto">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">{grid}</div>

      <div style="background:linear-gradient(135deg,#1a2a00,#2d4d00);border:2px solid #ffe500;
                  border-radius:10px;padding:14px;margin:18px auto 8px;max-width:360px;text-align:center;
                  box-shadow:0 0 24px #ffe50040;animation:fadein .6s ease both;animation-delay:1.9s">
        <div style="color:#ffe500;font-size:.68em;letter-spacing:3px">PLACA EXTRAÍDA</div>
        {placa_html}
      </div>

      <div style="margin-top:12px;animation:fadein .6s ease both;animation-delay:2.1s">
        <div style="color:#4a8fa8;font-size:.66em;letter-spacing:2px;margin-bottom:6px">
          ▸ PORCENTAJES DE CONFIANZA POR LECTURA
        </div>
        {barras or '<div style="color:#557;font-size:.8em">Sin lecturas.</div>'}
      </div>

      <div style="color:#1a3a5c;font-size:.62em;letter-spacing:3px;margin-top:14px;text-align:center">
        MOTOR: EasyOCR (CRNN) + HSV · {nombre}
      </div>
    </div>"""))