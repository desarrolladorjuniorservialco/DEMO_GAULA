---
name: NEXO-147
description: Plataforma demo para recepción, clasificación y seguimiento operativo de reportes GAULA — Línea 147
colors:
  primary-green: "#2f6b4f"
  primary-green-light: "#4f8a68"
  olive: "#5d6f52"
  military-gold: "#b59a5a"
  military-gold-warm: "#c2a35a"
  steel-dark: "#0f1419"
  panel-dark: "#121820"
  surface: "#1e2835"
  surface-hover: "#253242"
  text-primary: "#f2f4f5"
  text-secondary: "#b0bcc7"
  text-muted: "#7d8a95"
  state-danger: "#a64f4f"
  state-info: "#5a7d99"
typography:
  display:
    fontFamily: "Inter, IBM Plex Sans, sans-serif"
    fontSize: "28px"
    fontWeight: 800
    lineHeight: 1.08
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Inter, IBM Plex Sans, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.1
  title:
    fontFamily: "Inter, IBM Plex Sans, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "Inter, IBM Plex Sans, sans-serif"
    fontSize: "13-14px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "IBM Plex Mono, Courier New, monospace"
    fontSize: "10-11px"
    fontWeight: 700
    letterSpacing: "0.5-1px"
    textTransform: "uppercase"
rounded:
  outer: "8px"
  inner: "6px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "20px"
  lg: "32px"
  xl: "48px"
components:
  button-primary:
    backgroundColor: "#2f6b4f"
    textColor: "#e8f0ec"
    borderRadius: "6px"
    padding: "12px 20px"
  button-primary-hover:
    backgroundColor: "#3d7d5e"
    boxShadow: "0 4px 16px rgba(47,107,79,0.22)"
  button-secondary:
    backgroundColor: "rgba(255,255,255,0.03)"
    textColor: "#f2f4f5"
    border: "1px solid rgba(255,255,255,0.08)"
    borderRadius: "6px"
  nav-item-active:
    borderLeft: "3px solid #4f8a68"
    background: "rgba(47,107,79,0.12)"
    textColor: "#f2f4f5"
  input-field:
    backgroundColor: "rgba(0,0,0,0.22)"
    border: "1px solid rgba(255,255,255,0.07)"
    borderRadius: "6px"
    padding: "12px 14px"
    focusBorder: "rgba(79,138,104,0.20)"
    focusShadow: "0 0 0 3px rgba(47,107,79,0.14)"
  kpi-card:
    backgroundColor: "#1e2835"
    valueColor: "#4f8a68"
    alertValueColor: "#b59a5a"
    borderRadius: "8px"
    padding: "20px 24px"
  badge-status-ok:
    background: "rgba(79,138,104,0.12)"
    color: "#4f8a68"
    border: "1px solid rgba(79,138,104,0.22)"
  badge-status-warning:
    background: "rgba(194,163,90,0.12)"
    color: "#c2a35a"
    border: "1px solid rgba(194,163,90,0.22)"
  badge-status-danger:
    background: "rgba(166,79,79,0.12)"
    color: "#c07070"
    border: "1px solid rgba(166,79,79,0.22)"
---

# Design System: NEXO-147 — Institutional Military Theme

## 1. Overview

**Creative North Star: "Centro de Comando Estratégico"**

NEXO-147 opera como un sistema de inteligencia gubernamental. La interfaz transmite autoridad institucional, precisión operativa y sobriedad profesional — características de plataformas C4ISR, centros nacionales de monitoreo y sistemas GIS de seguridad.

El fondo negro acero (`#0f1419`) no es estética: es ergonomía operativa para salas de mando con iluminación controlada. El verde institucional (`#4f8a68`) y el dorado militar (`#b59a5a`) son los únicos colores funcionales porque en un centro de operaciones, el color es señal de estado, no decoración.

**Key Characteristics:**
- Fondos en acero oscuro profundo — sin tema claro, sin gradientes llamativos
- Verde institucional como color primario de acción y estado activo
- Dorado militar para advertencias y estados de criticidad secundaria
- Tipografía Inter (sans institucional) + IBM Plex Mono (datos / labels)
- Sin neón, sin glows, sin efectos CRT, sin animaciones decorativas
- Textura topográfica de marca de agua a opacidad 0.03 (cartografía militar)
- Animaciones funcionales solamente: indicadores de estado, radar de criticidad

## 2. Colors: Paleta Táctica Institucional

Cada tono tiene un rol operativo único. El color que no comunica estado o jerarquía no debe aparecer.

### Fondos — Capas de acero
- **Fondo base** (`#0f1419`): El sustrato. Profundo, sin temperatura de color dominante.
- **Panel** (`#121820`): Sidebar, topbar, statusbar. Ligeramente más claro que el fondo.
- **Superficie** (`#1e2835`): Cards, formularios, panels de contenido.
- **Hover** (`#253242`): Estado interactivo de superficies.

### Verde Institucional (acción primaria)
- **Verde primario** (`#2f6b4f`): Background de botón primario, elementos de acción más prominentes.
- **Verde claro** (`#4f8a68`): Texto de acción, KPI values positivos, estado activo en nav, bordes de énfasis.
- **Verde soft** (`rgba(47,107,79,0.12)`): Fondos de badges, hover de nav activo.
- **Verde borde** (`rgba(79,138,104,0.20)`): Bordes de elementos con énfasis verde.

### Dorado Militar (advertencia, criticidad)
- **Dorado** (`#b59a5a`): Alertas KPI, valores de criticidad, el color que dice "atención pero no urgencia máxima".
- **Dorado cálido** (`#c2a35a`): Estado amber en badges y barras de progreso.

### Estados Operacionales
- **Danger** (`#a64f4f`): Exclusivo para alertas de máxima urgencia, dots de error.
- **Info** (`#5a7d99`): Azul acero para información contextual.

### Texto
- **Primary** (`#f2f4f5`): Texto de alto contraste sobre fondos oscuros.
- **Secondary** (`#b0bcc7`): Texto descriptivo, valores en tables.
- **Muted** (`#7d8a95`): Labels, metadata, texto subordinado.

### Reglas de Color
**La Regla del Verde como Señal.** El verde institucional aparece en: botones de acción primaria, indicador de nav activo, KPI positivos, focus de formularios, badges de estado OK. Fuera de estos contextos, no hay verde.

**La Regla del Dorado Escaso.** El dorado aparece en: alertas de criticidad media, KPI de advertencia, badges warning. Nunca como decoración.

**La Regla del Rojo Mínimo.** El rojo (`#a64f4f`) aparece en ≤5% de la pantalla. Su impacto viene de su rareza.

## 3. Typography

**Tipografía principal:** Inter (con fallback IBM Plex Sans)
**Tipografía mono:** IBM Plex Mono (con fallback Courier New)

Inter es la tipografía de sistemas de inteligencia y herramientas gubernamentales modernas: legible, neutral, con autoridad institucional sin rigidez burocrática. IBM Plex Mono refuerza el carácter operativo en labels, timestamps, y datos numéricos.

### Hierarchy
- **Display** (700-800, 28px, line-height 1.08): Títulos de sección principales.
- **Title** (700, 18-22px, line-height 1.1-1.3): Encabezados de cards y paneles.
- **Body** (400, 13-14px, line-height 1.55): Contenido operativo.
- **Label Mono** (IBM Plex Mono, 700, 10-11px, uppercase, letter-spacing 0.5-1px): Categorías, timestamps, KPI labels, encabezados de tabla.

### Reglas
**Sin pesos inferiores a 500 en elementos interactivos.** La legibilidad en pantallas oscuras lo exige.
**Inter para interfaces, IBM Plex Mono solo para datos.** No mezclar en el mismo elemento.

## 4. Elevation

Sistema de capas por sustrato oscuro:

1. **Background** (`#0f1419`): Suelo. Sin elevación.
2. **Panel** (`#121820`): Sidebar, topbar, statusbar. Borde `rgba(255,255,255,0.05)`.
3. **Surface** (`#1e2835`): Cards y panels. Shadow `0 8px 32px rgba(0,0,0,0.28)`.
4. **Overlay**: Modales, elementos flotantes. Shadow `0 24px 64px rgba(0,0,0,0.45)`.

### Shadow Vocabulary
- **Card shadow**: `0 8px 32px rgba(0,0,0,0.28)` — flotación suave, no material.
- **Login shadow**: `0 24px 64px rgba(0,0,0,0.45)` — superficie principal.
- **Button hover shadow**: `0 4px 16px rgba(47,107,79,0.22)` — feedback de acción.
- **Sin glows de neón.** El resplandor neon no existe en este sistema.

## 5. Components

### Botones
- **Primary**: Fondo `#2f6b4f`, texto `#e8f0ec`, borde `rgba(79,138,104,0.3)`. Hover: `#3d7d5e` + sombra suave. Sin gradientes, sin glows.
- **Secondary**: Fondo `rgba(255,255,255,0.03)`, borde `rgba(255,255,255,0.08)`. Hover: fondo ligeramente más opaco.
- **Todos los botones**: `border-radius: 6px`. Sin píldoras consumer, sin cuadrados burocrátcos.

### Nav Items
- **Default**: Texto muted, sin borde.
- **Active**: `border-left: 3px solid #4f8a68` + `background: rgba(47,107,79,0.12)` + texto primary. El indicador de línea vertical es la señal de localización en el sistema.
- **Hover**: Fondo `rgba(255,255,255,0.04)`, texto primary.

### Cards / Panels
- Background: `#1e2835`
- Border: `1px solid rgba(255,255,255,0.05)`
- Shadow: `0 8px 32px rgba(0,0,0,0.28)`
- Radius: `8px` (outer), `6px` (inner)
- Padding: `24px`

### Formularios
- Input background: `rgba(0,0,0,0.22)`, border `rgba(255,255,255,0.07)`
- Focus: border `rgba(79,138,104,0.20)` + shadow `0 0 0 3px rgba(47,107,79,0.14)`
- Label: IBM Plex Mono, 700, 11px, uppercase, color muted

### KPI Cards
- Valor: IBM Plex Mono, 700, 32px, color `#4f8a68` (verde institucional)
- Valor crítico: color `#b59a5a` (dorado militar)
- Label: IBM Plex Mono, 11px, uppercase, color muted
- Sin gradientes de acento, sin backgrounds de color

### Badges de Estado
- OK: verde soft `rgba(79,138,104,0.12)` + borde `rgba(79,138,104,0.22)` + texto `#4f8a68`
- Warning: dorado soft + texto `#c2a35a`
- Neutral: `rgba(255,255,255,0.05)` + texto muted
- Info: sin estilo especial, solo texto muted

### Radar / Mapa
- Círculos radar: `rgba(79,138,104,0.14)` — sutiles, no brillantes
- Sweep: `conic-gradient rgba(47,107,79,0.12)` — rotación lenta y funcional
- Dots radar: `#a64f4f` (rojo de amenaza) — señal real
- Grid de mapa: `rgba(79,138,104,0.04)` — cuadrícula cartográfica casi invisible

## 6. Motion

- **Duración**: 200-300ms en transiciones de estado. Sin coreografías.
- **Easing**: `cubic-bezier(0.16, 1, 0.3, 1)` para paneles; `ease` para hover.
- **Animaciones funcionales permitidas**: radar sweep (indica monitoreo activo), pulse de status indicator (sistema operativo), blip del radar (amenazas detectadas), fadeIn de panels.
- **Animaciones prohibidas**: orbes animados, neón pulsante, efectos CRT, scanlines, bounce/elastic.
- **Reduced motion**: Todas las animaciones tienen `@media (prefers-reduced-motion: reduce)`.

## 7. Texture

Textura topográfica (`body::before`):
- SVG de elipses concéntricas + líneas cartesianas, color `#4f8a68`
- `background-size: 280px 280px`
- `opacity: 0.03` — nunca visible directamente, solo perceptible en fondos sólidos grandes
- Inspirada en: cartografía militar, capas SIG, mapas de elevación, coordenadas de navegación

## 8. Do's and Don'ts

### Do:
- Usar `#0f1419` como único background de body.
- Reservar el verde institucional para acciones primarias, nav activo, KPI positivos y focus.
- Usar IBM Plex Mono para labels, timestamps y datos numéricos.
- Mantener sombras estructurales (darkness-based), no de color.
- Separar Admin y Operador visualmente. La diferencia de rol debe ser obvia sin texto.
- Usar `border-left: 3px solid #4f8a68` exclusivamente para el indicador de nav activo.

### Don't:
- Usar neón, glows de color brillante, efectos CRT, scanlines o bordes de neón.
- Agregar colores más allá del vocabulario definido. Verde, dorado y rojo son los únicos funcionales.
- Usar gradientes de color en texto.
- Animar propiedades de layout (width, height, top, left).
- Usar `border-radius` mayor a 8px en panels — los ángulos institucionales no son pills consumer.
- Usar Montserrat u otras tipografías display en labels y datos — solo Inter/IBM Plex Mono.
- Mostrar el dashboard admin a usuarios con rol operador.
