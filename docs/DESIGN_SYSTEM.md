# Sistema de diseño — NEXO-147

**North Star:** "El Centro de Operaciones" — una interfaz de centro de mando para fuerzas de seguridad institucionales.

El sistema evita la estética gubernamental clásica (formularios grises, tablas planas) en favor de un look de comando operacional oscuro, de alta información y alta confianza.

---

## Paleta de colores

| Token | Hex | Uso |
|---|---|---|
| `--color-bg` | `#07111f` | Fondo principal único |
| `--color-surface` | `#0d1b2e` | Superficies (tarjetas, paneles) |
| `--color-cyan` | `#2596be` | Acciones primarias, énfasis |
| `--color-cyan-active` | `#41d2ff` | Elementos activos/urgentes |
| `--color-green` | `#6fca52` | Estados positivos, KPIs en verde |
| `--color-green-alt` | `#74e04b` | Variante más brillante |
| `--color-red` | `#ff5a5a` | Alertas, errores (máx. 5% pantalla) |
| `--color-text` | `#eefbff` | Texto principal (alto contraste) |
| `--color-muted` | `#b7d2dc` | Texto secundario, labels |

### Reglas de color

- `#07111f` es el **único** fondo permitido — no mezclar con otros colores de fondo
- El cian **solo** se usa para acciones primarias e información operacional clave
- El rojo crítico se reserva exclusivamente para errores, alertas y estados peligrosos
- No agregar colores fuera de esta paleta
- Verificar contraste en texto sobre fondos coloreados

---

## Tipografía

**Fuente:** Montserrat (Google Fonts)  
**Pesos:** 400, 500, 600, 700, 800, 900

| Nivel | Peso | Tamaño | Line-height | Uso |
|---|---|---|---|---|
| Display | 900 | 44–76px | 0.98 | Títulos hero (máx. 6 palabras) |
| Headline | 900 | 32–52px | 1.08 | Títulos de sección |
| Title | 900 | 20px | 1.3 | Headers de tarjeta, formularios |
| Body | 400–700 | 14–18px | 1.65–1.75 | Texto descriptivo (máx. 75ch ancho) |
| Label | 800–900 | 12–13px | — | Tags, headers de tabla (UPPERCASE, tracking 0.7–1.4px) |

### Reglas tipográficas

- Peso 900 para **todos** los headings
- No usar fuentes distintas a Montserrat
- Texto body: máximo 75 caracteres por línea para legibilidad
- Labels en tabla: SIEMPRE uppercase con letter-spacing

---

## Componentes

### Botones

**Primario:**
```css
background: linear-gradient(135deg, #2596be, #48cbe8);
color: white;
border-radius: 999px;
padding: 17px 30px;
font-weight: 700;
```

**Hover:** `translateY(-4px)` + `box-shadow: 0 8px 24px rgba(37,150,190,.45)`

**Ghost:**
```css
background: rgba(255, 255, 255, 0.06);
border: 1px solid #2596be;
border-radius: 999px;
color: #eefbff;
```

**Hover ghost:** `translateY(-4px)` + glow cian

---

### Tarjetas (Cards)

```css
background: rgba(255, 255, 255, 0.08);
border: 1px solid rgba(37, 150, 190, 0.3);
border-radius: 26px;       /* o 34px para tarjetas grandes */
backdrop-filter: blur(14px);  /* o blur(18px) */
padding: 24px;             /* o 34px */
box-shadow: 0 24px 48px rgba(0, 0, 0, 0.35);
```

---

### Campos de formulario (Inputs)

```css
background: rgba(4, 13, 25, 0.74);
border: 1px solid rgba(37, 150, 190, 0.5);
border-radius: 18px;
padding: 17px 18px;
color: #eefbff;
font-family: Montserrat;
font-size: 15px;
```

**Focus:**
```css
border-color: #41d2ff;
box-shadow: 0 0 0 3px rgba(65, 210, 255, 0.15);
```

---

### Tarjetas KPI

```css
/* Tarjeta verde */
background: linear-gradient(135deg, rgba(111,202,82,.15), rgba(116,224,75,.08));
border: 1px solid rgba(111,202,82,.3);

/* Número */
font-size: 34px;
font-weight: 900;
color: white;

/* Label */
text-transform: uppercase;
font-size: 12px;
letter-spacing: 1.4px;
color: #b7d2dc;
```

---

### Tablas

```css
/* Header */
background: rgba(37, 150, 190, 0.1);
color: #2596be;
font-size: 12px;
font-weight: 800;
text-transform: uppercase;
letter-spacing: 1px;

/* Fila hover */
background: rgba(37, 150, 190, 0.05);

/* Border */
border-color: rgba(37, 150, 190, 0.1);
```

---

### Badges de estado

| Estado | Color fondo | Color texto |
|---|---|---|
| Recibido | `rgba(37,150,190,.15)` | `#41d2ff` |
| En proceso | `rgba(111,202,82,.15)` | `#74e04b` |
| Cerrado | `rgba(255,255,255,.08)` | `#b7d2dc` |
| Crítico | `rgba(255,90,90,.15)` | `#ff5a5a` |
| Alto | `rgba(255,165,0,.15)` | `#ffa500` |

---

## Animaciones

- **Transición base:** `all 0.3s cubic-bezier(0.4, 0, 0.2, 1)`
- **Hover elevation:** `translateY(-4px)` para botones e ítems interactivos
- **Fade in:** `opacity: 0 → 1` + `translateY(20px → 0)` en 0.5s

**No animar** propiedades de layout (`width`, `height`, `margin`, `padding`) — usar solo `transform` y `opacity`.

---

## Iconografía

No hay librería de iconos definida. Se prefiere:
- Unicode symbols para estados simples
- SVG inline para iconos operacionales
- Evitar Font Awesome u otras CDN de iconos que agreguen peso

---

## Reglas de diseño

### DO ✓
- Usar `#07111f` como único fondo
- Reservar cian para acciones e información clave
- Peso 900 para todos los headings
- `blur(14–18px)` en superficies flotantes
- Verde para estados de éxito y métricas positivas
- UPPERCASE + letter-spacing para labels y headers de tabla

### DON'T ✗
- Usar estética gov clásica (grises, azul corporativo plano)
- Agregar colores fuera de la paleta definida
- Usar bordes mayores a 1px
- Decorar con gradientes en texto del body
- Poner texto gris (`--color-muted`) sobre fondos con tinte sin verificar contraste
- Usar rojo crítico fuera de errores y alertas
- Animar propiedades de layout

---

## Variables CSS recomendadas

```css
:root {
    --color-bg: #07111f;
    --color-surface: #0d1b2e;
    --color-cyan: #2596be;
    --color-cyan-active: #41d2ff;
    --color-green: #6fca52;
    --color-red: #ff5a5a;
    --color-text: #eefbff;
    --color-muted: #b7d2dc;

    --radius-sm: 18px;
    --radius-md: 26px;
    --radius-lg: 34px;
    --radius-pill: 999px;

    --blur-sm: blur(14px);
    --blur-md: blur(18px);

    --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    --font: 'Montserrat', sans-serif;
}
```

---

## Archivos CSS del proyecto

| Archivo | Propósito |
|---|---|
| `static/styles_pc.css` | Layout desktop, componentes, paleta, tipografía |
| `static/styles_media.css` | Media queries (móvil, tablet) |

El template base `templates/base.html` carga ambos archivos y la fuente Montserrat desde Google Fonts.
