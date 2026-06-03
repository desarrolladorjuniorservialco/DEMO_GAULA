# NEXO-147

Plataforma demostrativa para la recepción, clasificación y seguimiento operativo de reportes de la Línea 147 — sistema de atención a víctimas de extorsión y secuestro del GAULA (Grupo de Acción Unificada para la Libertad Personal).

---

## Descripción

NEXO-147 es un sistema de gestión de reportes diseñado para unidades GAULA en Colombia. Permite a los operadores registrar llamadas entrantes de la línea 147 de forma estructurada, mientras que administradores y directores visualizan el estado operativo en tiempo real mediante un dashboard centralizado.

El sistema opera bajo principios de diseño de sala de mando: alta legibilidad en ambientes de baja luminosidad, jerarquía visual clara por rol y resistencia a la degradación técnica.

> **Nota:** Este proyecto es una demostración funcional. No está destinado a producción sin auditoría de seguridad adicional.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3 + Flask 3.1.3 |
| ORM | Flask-SQLAlchemy 3.1.1 |
| Base de datos | SQLite (`data/nexo147.db`) |
| Autenticación | Werkzeug (hashing de contraseñas) |
| Plantillas | Jinja2 |
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Tablas | DataTables 1.13.7 + jQuery 3.7.1 |
| Tipografía | Montserrat (Google Fonts) |

---

## Requisitos previos

- Python 3.9 o superior
- pip

---

## Instalación

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd DEMO_GAULA

# Crear y activar entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
python app.py
```

La aplicación queda disponible en `http://localhost:5000`.

La base de datos SQLite y los usuarios demo se crean automáticamente en el primer arranque.

---

## Usuarios de demostración

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `Admin147*` | Administrador |
| `director` | `Director147*` | Director |
| `analista` | `Analista147*` | Analista |
| `operador` | `Operador147*` | Operador |

---

## Roles y permisos

| Capacidad | Admin | Director | Analista | Operador |
|---|:---:|:---:|:---:|:---:|
| Registrar reporte | ✓ | — | — | ✓ |
| Ver reportes | ✓ | ✓ | ✓ | — |
| Actualizar estado de reporte | ✓ | — | ✓ | — |
| Acceder al dashboard | ✓ | ✓ | — | — |
| Gestionar usuarios | ✓ | — | — | — |

---

## Estructura del proyecto

```
DEMO_GAULA/
├── app.py                  # Aplicación Flask principal (rutas, modelos, lógica)
├── requirements.txt        # Dependencias Python
├── PRODUCT.md              # Descripción de producto
├── DESIGN.md               # Sistema de diseño NEXO-147
│
├── templates/              # Plantillas Jinja2
│   ├── base.html           # Layout base
│   ├── login.html          # Pantalla de acceso
│   ├── index.html          # Formulario de registro de reporte
│   ├── dashboard.html      # Dashboard operativo
│   ├── brechas_seguridad.html  # Verificación de brechas (API externa)
│   └── footer.html
│
├── static/
│   ├── styles_pc.css       # Estilos escritorio
│   ├── styles_media.css    # Estilos responsive
│   ├── scripts.js          # Lógica de formulario / AJAX
│   ├── tablas.js           # Configuración de DataTables
│   └── assets/             # Imágenes y brochure
│
├── data/
│   └── nexo147.db          # Base de datos SQLite (generada en runtime)
│
└── docs/
    └── DATABASE.md         # Documentación del esquema de base de datos
```

---

## Endpoints principales

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| `GET/POST` | `/login` | Autenticación | Público |
| `GET` | `/logout` | Cierre de sesión | Autenticado |
| `GET` | `/` | Home (formulario según rol) | Autenticado |
| `POST` | `/registrar-reporte` | Registrar nuevo reporte | Operador / Admin |
| `GET` | `/dashboard` | Dashboard de reportes | Admin / Director |
| `GET` | `/api_externa` | Consulta de brechas (HaveIBeenPwned) | Admin |
| `GET` | `/health` | Estado de la aplicación | Público |

---

## Modelo de datos

### Tabla `usuarios`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | Identificador interno |
| `username` | VARCHAR(50) UNIQUE | Usuario de login |
| `password_hash` | VARCHAR(256) | Contraseña hasheada (Werkzeug) |
| `nombre` | VARCHAR(100) | Nombre visible |
| `rol` | VARCHAR(20) | `admin`, `director`, `analista`, `operador` |
| `activo` | BOOLEAN | Permite deshabilitar cuentas |

### Tabla `reportes`

| Sección | Campos |
|---|---|
| Metadatos | `id`, `id_reporte` (UUID), `fecha_registro`, `estado`, `usuario_registro` |
| Clasificación | `tipo_reporte`, `prioridad`, `unidad_gaula`, `canal_recepcion` |
| Reportante | `nombre_reportante`, `documento_reportante`, `telefono_reportante`, `ubicacion` |
| Caso | `descripcion`, `numero_extorsivo`, `alias_sospechoso`, `medio_pago`, `valor_exigido`, `evidencia`, `observaciones` |

---

## Sistema de diseño

NEXO-147 usa una paleta institucional optimizada para pantallas de sala de mando:

| Rol del color | Valor | Uso |
|---|---|---|
| Negro de Comando | `#07111f` | Fondo principal |
| Azul Operaciones | `#0d1b2e` | Superficies secundarias |
| Cian Operativo | `#2596be` | Acciones primarias |
| Comando Signal | `#41d2ff` | Elementos activos |
| Verde Estado | `#6fca52` | Confirmaciones / KPIs positivos |
| Rojo Crítico | `#ff5a5a` | Alertas (máx. 5% de pantalla) |
| Señal Clara | `#eefbff` | Texto principal |

Tipografía única: **Montserrat** con jerarquía por peso (400–900).

Consulta [DESIGN.md](DESIGN.md) para el sistema de diseño completo.

---

## Seguridad

- Contraseñas almacenadas con hash usando Werkzeug (`generate_password_hash` / `check_password_hash`).
- Caché deshabilitado globalmente (`no-store, no-cache, must-revalidate`).
- Decoradores de control de acceso por rol (`@login_required`, `@admin_required`, etc.).
- La base de datos SQLite está excluida del repositorio via `.gitignore`.

---

## Licencia

Proyecto demostrativo — uso educativo e institucional.
