# Instalación y despliegue — NEXO-147

---

## Requisitos

- Python 3.11+
- pip
- (Opcional) Playwright para scraping de Facebook

---

## Instalación local (desarrollo)

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd DEMO_GAULA

# 2. Crear entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) Instalar navegador para scraping Facebook
playwright install chromium

# 5. Arrancar la aplicación
python app.py
```

La aplicación estará disponible en `http://localhost:5000`.

Las bases de datos se crean automáticamente en `data/` en el primer arranque.

---

## Variables de entorno

| Variable | Por defecto | Descripción |
|---|---|---|
| `SECRET_KEY` | `demo-gaula-nexo-147` | Clave de firma de sesiones Flask |
| `FLASK_ENV` | `development` | Entorno (`development` / `production`) |
| `FLASK_DEBUG` | `1` | Debug mode (solo desarrollo) |

**Producción:** cambiar siempre `SECRET_KEY` por un valor aleatorio y seguro.

```bash
# Generar clave segura
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Estructura de datos

```
DEMO_GAULA/
└── data/
    ├── nexo147.db    # Base de datos principal
    ├── intel.db      # Base de datos de inteligencia
    └── osint.db      # Base de datos OSINT
```

Los archivos `.db` están en `.gitignore` y no se versionan. Se recrean automáticamente si no existen.

---

## Usuarios iniciales (seed)

Al arrancar por primera vez con las bases de datos vacías, el sistema inserta automáticamente los usuarios demo:

| Username | Contraseña | Rol |
|---|---|---|
| `admin` | `Admin147*` | admin |
| `director` | `Director147*` | director |
| `analista` | `Analista147*` | analista |
| `operador` | `Operador147*` | operador |

---

## Despliegue en producción

### Con gunicorn (Linux/macOS)

```bash
# Instalar gunicorn (ya está en requirements.txt)
pip install gunicorn

# Arrancar con 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Con timeout y logging
gunicorn -w 4 -b 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    app:app
```

### Con Nginx como proxy inverso

```nginx
server {
    listen 80;
    server_name nexo147.ejemplo.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /ruta/al/proyecto/static/;
        expires 30d;
    }
}
```

### Como servicio systemd (Linux)

```ini
# /etc/systemd/system/nexo147.service
[Unit]
Description=NEXO-147 Flask App
After=network.target

[Service]
User=www-data
WorkingDirectory=/ruta/al/proyecto
Environment="SECRET_KEY=clave-segura-aqui"
ExecStart=/ruta/al/proyecto/.venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable nexo147
sudo systemctl start nexo147
```

---

## Docker (opcional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV SECRET_KEY=cambiar-en-produccion
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
docker build -t nexo147 .
docker run -p 5000:5000 -v $(pwd)/data:/app/data nexo147
```

---

## Verificación del despliegue

```bash
# Health check
curl http://localhost:5000/health

# Respuesta esperada
{"status": "ok", "timestamp": "...", "version": "1.0.0"}
```

---

## Logs

La aplicación usa el sistema de logging de Flask/Werkzeug. En desarrollo, los logs se imprimen en la consola. En producción con gunicorn, usar las opciones `--access-logfile` y `--error-logfile`.

---

## Actualización

```bash
# 1. Obtener cambios
git pull origin main

# 2. Actualizar dependencias si cambiaron
pip install -r requirements.txt

# 3. Reiniciar el servicio
sudo systemctl restart nexo147  # o el proceso gunicorn
```

Las migraciones de base de datos no están implementadas — el sistema recrea tablas faltantes al arrancar (`db.create_all()`). Para cambios destructivos de esquema en producción, hacer backup de los `.db` primero.

---

## Backup de bases de datos

```bash
# Backup manual
cp data/nexo147.db backups/nexo147_$(date +%Y%m%d).db
cp data/intel.db backups/intel_$(date +%Y%m%d).db
cp data/osint.db backups/osint_$(date +%Y%m%d).db

# SQLite permite backup en caliente con .backup
sqlite3 data/nexo147.db ".backup backups/nexo147_live.db"
```
