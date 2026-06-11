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
