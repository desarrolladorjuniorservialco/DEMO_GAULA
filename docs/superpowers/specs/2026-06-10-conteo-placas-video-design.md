# Diseño: Conteo de placas en video de alto movimiento

**Fecha:** 2026-06-10
**Estado:** Aprobado
**Módulo:** `modules/placas` (sub-módulo `video/`)

## Problema

El flujo actual de análisis de video captura frames en el navegador cada ~250 ms y los envía a
`POST /placas/analizar-frame`, que ejecuta el pipeline pesado de imágenes (`engine.reconocer_placa`:
4 variantes de imagen completa + hasta 24 OCRs de recortes → 1–3 s por frame en CPU). Con vehículos
en circulación que cruzan la escena en 1–2 segundos, la tasa efectiva de análisis (~0.3–1 fps) hace
que la mayoría de vehículos pase sin ser analizada. Además:

- `yolov8n.pt` es el modelo COCO genérico: detecta carros, no placas, y `detectar_frame` no filtra
  clases — el OCR recibía el vehículo completo.
- El conteo deduplica por string exacto: una lectura errónea (`A8C123` vs `ABC123`) cuenta doble.
- El OCR se hacía sobre el primer frame del track (típicamente el más lejano y borroso).
- Existe un pipeline server-side (`video/pipeline.py` + ByteTrack) que quedó abandonado; el
  frontend se congelaba al llegar el job a 100% ("se traba al 100%").

## Decisiones tomadas (con el usuario)

1. **Prioridad: conteo preciso server-side.** El servidor decodifica todos los frames a su ritmo;
   el video se reproduce localmente en paralelo y los resultados llegan en vivo por SSE.
2. **Modelo:** se descarga una sola vez un YOLOv8 fine-tuned de placas (~6 MB) que queda local.
3. **Conteo:** dos métricas — N vehículos detectados (por tracking, aunque la placa no se lea) y
   M placas leídas. Vehículos ilegibles se listan como "SIN LECTURA" con timestamp.

## Restricciones

- Hardware: CPU solamente (sin CUDA). `ultralytics 8.4.64` y `supervision 0.28.0` ya instalados.
- Placas colombianas: formatos `LLLNNN` (carro), `LLLNNL` / `LLLNN` (moto) — lógica ya existente
  en `engine.extraer_placas_de_texto`.
- La página de análisis de imágenes (`/placas/`) no se toca.

## Arquitectura

```
[Navegador]                         [Servidor Flask]
seleccionar video ──► reproductor local (objectURL), inmediato
"Iniciar análisis" ─► POST /video/upload ──► job + thread daemon
                                             │
                                             ▼
                            cv2.VideoCapture lee TODOS los frames
                                             │
                            YOLO placas (1 de cada 2 frames, 640px)
                                             │
                            ByteTrack: track_id persistente por placa
                                             │
                            Buffer por track: mejores K recortes
                            (score = área × nitidez Laplaciana)
                                             │
                            OCR (EasyOCR, pool 2 hilos) sobre top-3
                            recortes del track → votación por mayoría
                                             │
SSE /video/<id>/stream ◄── progreso + eventos incrementales
tabla en vivo: placa · tipo · conf · ts · [ir]
barra: "N vehículos · M placas leídas · X%"
```

## Componentes

### `video/detector.py` (modificar)
- Modelo de placas fine-tuned descargado a `models/placas-yolov8n.pt`; ruta configurable con
  env var `PLACAS_YOLO_MODEL`. Fuente: modelo YOLOv8n de detección de placas publicado en
  HuggingFace (descarga única en build/setup, no en runtime de request).
- Fallback: si el archivo no existe, usar `yolov8n.pt` COCO filtrando clases vehículo
  {car, motorcycle, bus, truck} y localizando la placa con la máscara amarilla HSV de
  `engine._mask_amarilla` dentro del bbox del vehículo.
- `detectar_frame` recibe umbral de confianza 0.30 (placas pequeñas en movimiento).

### `video/tracker.py` (modificar levemente)
- ByteTrack se mantiene. Se añade noción de **track confirmado**: un track cuenta como vehículo
  solo tras aparecer en ≥3 actualizaciones de detección (elimina falsos positivos de 1 frame).

### `video/best_frames.py` (nuevo)
- `TrackCropBuffer`: por cada track_id guarda los K=5 mejores recortes de placa.
- Score de calidad = `área_bbox × var(Laplaciano(gray))` (tamaño × nitidez). Recortes con
  altura < 12 px se descartan.
- Al cerrar el track (desaparece por > 1.5 s o termina el video) entrega los top-3 recortes.

### `video/plate_votes.py` (nuevo)
- `PlateVoter`: recibe lecturas OCR (texto, confianza) de los recortes de un track.
- Voto por mayoría ponderado por confianza; el texto debe validar contra los formatos
  colombianos (`extraer_placas_de_texto`). Resultado: placa final o `None` (SIN LECTURA).
- Deduplicación entre tracks: si dos tracks confirmados votan la misma placa con solapamiento
  temporal < 2 s, se fusionan (mismo vehículo re-trackeado).

### `video/pipeline.py` (reescribir parcialmente)
- `YOLO_EVERY_N_FRAMES = 2` (antes 5). `MAX_YOLO_DIM = 640` se mantiene.
- El OCR ya no ocurre al primer frame del track: ocurre al **cierre** del track (o cada 2 s para
  tracks largos, para dar feedback temprano), sobre los mejores recortes del buffer.
- OCR sobre recorte de placa: upscale ×3 + EasyOCR con allowlist — se elimina el doble pase con
  variantes (innecesario sobre un recorte limpio de placa).
- El job acumula `eventos` (lista append-only): `{tipo: "vehiculo"|"placa"|"sin_lectura", ...}`
  con índice incremental para que el SSE envíe solo lo nuevo.
- Contadores en `job.summary()`: `vehiculos`, `placas_leidas`, `sin_lectura`, `progreso`.

### `video/schemas.py` y `job_store.py` (extender)
- `VideoJob` gana `eventos: list`, `vehiculos: int`, `placas_leidas: int`, `sin_lectura: int`.
- TTL/limpieza de jobs existente se conserva.

### `routes.py` (modificar)
- `/video/<id>/stream` (SSE): además del summary, emite eventos nuevos desde el último índice
  enviado (`?since=N` o cursor interno del generador). Frecuencia 0.5 s.
- `/analizar-frame` se conserva (lo usa potencialmente la página de imágenes/cámara) pero la
  página de video deja de usarlo.

### Frontend: `templates/placas/video.html` + `static/js/placas-video.js` (reescribir)
- Seleccionar video → reproductor inmediato (objectURL) + botón "Iniciar análisis".
- Iniciar → sube el archivo (con progreso de upload), abre SSE, muestra barra de progreso real
  del servidor y contadores `N vehículos · M placas leídas`.
- Cada evento `placa` agrega fila: placa · tipo · confianza · timestamp · botón "ir" (salta el
  reproductor local al segundo de la detección). Eventos `sin_lectura` agregan fila gris
  "SIN LECTURA" con timestamp.
- Estado `done`: la barra llega a 100%, el SSE se cierra limpiamente, resumen final visible
  (corrige el bug de congelamiento al 100%).
- Estado `error`: banner con el mensaje del job.

## Manejo de errores

- Video ilegible / códec no soportado → job `error` con mensaje claro.
- Modelo de placas ausente → fallback COCO + máscara amarilla, y advertencia en el summary
  (`modelo: "fallback"`) visible en la UI.
- SSE interrumpido (recarga de página) → `GET /video/<id>/results` devuelve el estado completo;
  el frontend puede reconectar al stream.
- OCR que lanza excepción en un recorte → se descarta ese recorte, el voto sigue con los demás.

## Pruebas

- Unitarias (sin ML): `PlateVoter` (mayoría, ponderación, fusión de tracks, formatos
  colombianos), `TrackCropBuffer` (scoring, top-K), contadores de eventos del job.
- Integración manual: video real de tráfico — verificar que vehículos rápidos generan track +
  fila, que lecturas inconsistentes convergen por votación, y que el estado `done` no congela
  la UI.

## Fuera de alcance

- GPU / aceleración CUDA.
- Streaming de cámaras en vivo (RTSP).
- Reconocimiento del tipo de vehículo más allá de CARRO/MOTO por formato de placa.
- Re-entrenamiento de modelos.
