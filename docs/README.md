# Documentación NEXO-147

Sistema de recepción, clasificación y seguimiento operativo de reportes de la Línea 147 — plataforma del GAULA (Grupo de Acción Unificada para la Libertad Personal).

---

## Índice de documentos

| Documento | Descripción |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Estructura del proyecto, blueprints y flujo de la aplicación |
| [DATABASE.md](DATABASE.md) | Esquema completo de las tres bases de datos SQLite |
| [MODELS.md](MODELS.md) | Modelos SQLAlchemy y sus relaciones |
| [API.md](API.md) | Referencia completa de endpoints REST |
| [AUTH.md](AUTH.md) | Autenticación, roles y decoradores |
| [OSINT.md](OSINT.md) | Módulo OSINT: fuentes, plugins y scraping |
| [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) | Sistema de diseño (paleta, tipografía, componentes) |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Instalación, configuración y despliegue |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Guía de desarrollo, tests y convenciones |

---

## Resumen del sistema

**NEXO-147** es una plataforma web Flask que permite a operadores del GAULA registrar llamadas y reportes recibidos por la Línea 147, mientras que administradores y directores cuentan con un dashboard operacional en tiempo real para monitoreo de casos e inteligencia.

### Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Flask 3.1.3 |
| ORM | Flask-SQLAlchemy 3.1.1 + SQLAlchemy 2.0.50 |
| Base de datos | SQLite (3 archivos: nexo147, intel, osint) |
| Autenticación | Werkzeug password hashing + Flask sessions |
| Frontend | HTML5 + CSS3 + Vanilla JS + DataTables 1.13.7 |
| Tipografía | Montserrat (Google Fonts) |
| Tests | pytest 8.3.5 |
| Servidor prod | gunicorn 21.2.0 |

### Usuarios demo

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `Admin147*` | Administrador |
| `director` | `Director147*` | Director GAULA |
| `analista` | `Analista147*` | Analista Operacional |
| `operador` | `Operador147*` | Operador Línea 147 |
