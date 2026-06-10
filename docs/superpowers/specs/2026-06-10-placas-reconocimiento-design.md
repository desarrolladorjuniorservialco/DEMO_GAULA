# Diseño — Módulo de Reconocimiento de Placas Vehiculares

**Fecha:** 2026-06-10  
**Proyecto:** DEMO_GAULA  
**Rama:** desarrollador1  
**Estado:** Aprobado

---

## 1. Objetivo

Añadir una nueva ventana dentro del Flask app existente que permita subir una imagen y obtener la placa vehicular extraída mediante EasyOCR, mostrando 4 paneles de diagnóstico visual.

---

## 2. Alcance (v1)

**Incluido:**
- Upload de imagen desde el navegador
- Procesamiento con EasyOCR + OpenCV (código de referencia adaptado)
- Respuesta JSON con 4 paneles diagnósticos en base64
- Renderizado AJAX sin recarga de página
- Spinner de carga durante el procesamiento
- Graceful fallback si las dependencias ML no están instaladas

**Excluido (futuras versiones):**
- Persistencia en base de datos
- Historial de consultas
- Integración con SIMIT/RUES al detectar placa
- Procesamiento de video
- Múltiples cámaras

---

## 3. Arquitectura

### 3.1 Estructura de archivos

```
modules/
└── placas/
    ├── __init__.py        # Blueprint "placas_bp"
    ├── routes.py          # GET /placas/  |  POST /placas/analizar
    └── engine.py          # Wrapper EasyOCR con lazy load y fallback

templates/
└── placas/
    └── index.html         # Drop-zone + spinner + 4 paneles + resultado
```

### 3.2 Registro del Blueprint

En `modules/__init__.py`, dentro de `_register_blueprints()`:

```python
from modules.placas import placas_bp
app.register_blueprint(placas_bp, url_prefix="/placas")
```

### 3.3 Enlace de navegación

Se añade "Placas" al menú principal en `templates/base.html` junto a los otros módulos.

---

## 4. Componentes

### 4.1 `engine.py`

- Importa `easyocr`, `cv2`, `torch`, `numpy` dentro de `_get_reader()` con `try/except ImportError`
- Singleton del `easyocr.Reader` — se inicializa una sola vez por proceso para no recargar modelos
- Función pública: `reconocer_placa(img_bytes: bytes) -> dict`
  - Decodifica los bytes con `cv2.imdecode`
  - Ejecuta el pipeline completo del código de referencia (PASE A + PASE B + diagnóstico HSV)
  - Devuelve:
    ```json
    {
      "ok": true,
      "placa": "ABC123",
      "tipo": "CARRO",
      "confianza": 0.94,
      "alternativas": [["XYZ789", "MOTO", 0.61]],
      "paneles": ["<b64_original>", "<b64_amarillo>", "<b64_ocr>", "<b64_final>"]
    }
    ```
- Si faltan dependencias:
  ```json
  {
    "ok": false,
    "missing_deps": true,
    "install_cmd": "pip install easyocr opencv-python torch"
  }
  ```
- Si la imagen no es decodificable:
  ```json
  { "ok": false, "error": "Imagen ilegible" }
  ```
- Si no se detecta placa:
  ```json
  { "ok": true, "placa": null, "paneles": ["<b64×4>"] }
  ```

### 4.2 `routes.py`

```
GET  /placas/           → render_template("placas/index.html")  [login_required]
POST /placas/analizar   → JSON response                         [login_required]
```

**POST `/placas/analizar`:**
- Acepta `multipart/form-data` con campo `imagen`
- Valida MIME type (`image/*`) → `400` si no es imagen
- Límite de tamaño: 10 MB (Flask `MAX_CONTENT_LENGTH`)
- Lee los bytes del archivo y llama `engine.reconocer_placa(bytes)`
- Devuelve JSON directamente

### 4.3 `templates/placas/index.html`

Extiende `base.html`. Secciones:

1. **Drop-zone** — área de arrastre con preview de la imagen seleccionada
2. **Botón "Analizar"** — dispara el `fetch` al endpoint
3. **Spinner overlay** — visible mientras `fetch` está en vuelo
4. **Banner de error de dependencias** — visible si `missing_deps: true`, muestra el comando `pip install`
5. **Grid 2×2 de paneles** — renderizado cuando llega respuesta exitosa:
   - Panel 1: Imagen original
   - Panel 2: Máscara de color amarillo HSV
   - Panel 3: Lecturas OCR con porcentajes
   - Panel 4: Reconocimiento final con bbox
6. **Caja de resultado** — placa extraída en texto grande, tipo de vehículo y confianza
7. **Lista de alternativas** — hasta 5 candidatos alternativos

---

## 5. Flujo de datos

```
Usuario sube imagen
       │
       ▼
fetch POST /placas/analizar
       │
       ▼
routes.py valida MIME + tamaño
       │
       ▼
engine.py: _get_reader() [singleton EasyOCR]
       │
       ▼
cv2.imdecode(bytes)
       │
       ▼
reconocer_placa(img_bgr):
  ├── PASE A: imagen completa × 4 variantes → EasyOCR → candidatos
  ├── Diagnóstico HSV amarillo → regiones de placa
  └── PASE B: recortes ×3 upscale → EasyOCR → candidatos refinados
       │
       ▼
_construir_paneles() → 4 imágenes como base64 JPEG
       │
       ▼
JSON response
       │
       ▼
JS renderiza paneles + resultado
```

---

## 6. Manejo de errores

| Situación | Respuesta |
|-----------|-----------|
| Dependencias ML ausentes | `{ok:false, missing_deps:true, install_cmd:"..."}` → banner en UI |
| Archivo no es imagen | HTTP 400 |
| Archivo > 10 MB | HTTP 413 |
| Imagen ilegible por OpenCV | `{ok:false, error:"Imagen ilegible"}` |
| Sin placa detectada | `{ok:true, placa:null}` → mensaje "Sin placa válida detectada" |
| Excepción inesperada en engine | `{ok:false, error:"Error interno"}` + log en servidor |

---

## 7. Dependencias a añadir en `requirements.txt`

```
easyocr>=1.7.0
opencv-python>=4.9.0
torch>=2.0.0
numpy>=1.24.0
```

> Estas son opcionales para el funcionamiento del resto del app — el fallback garantiza que DEMO_GAULA arranca aunque no estén instaladas.

---

## 8. Diseño visual

- Extiende `base.html` para heredar navegación, login y estilos globales
- Paleta consistente con el tema institucional/gobierno del proyecto
- Los 4 paneles diagnósticos replican visualmente el diseño del código de referencia
- La caja de resultado usa tipografía grande con espaciado de caracteres (estilo placa)

---

## 9. Criterios de éxito

- La ruta `/placas/` carga sin errores cuando las libs ML no están instaladas
- Al subir una imagen con placa colombiana válida, se devuelve la placa correcta
- Los 4 paneles diagnósticos se muestran correctamente en el grid
- El spinner aparece durante el procesamiento y desaparece al recibir respuesta
- El módulo no rompe ningún otro Blueprint del app
