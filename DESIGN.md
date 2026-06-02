---
name: NEXO-147
description: Plataforma demo para recepción, clasificación y seguimiento operativo de reportes GAULA — Línea 147
colors:
  operational-cyan: "#2596be"
  command-signal: "#41d2ff"
  cyan-deep: "#176f8d"
  status-green: "#6fca52"
  status-green-bright: "#74e04b"
  command-black: "#07111f"
  ops-navy: "#0d1b2e"
  clear-signal: "#eefbff"
  ops-mist: "#b7d2dc"
  critical-red: "#ff5a5a"
typography:
  display:
    fontFamily: "Montserrat, sans-serif"
    fontSize: "clamp(44px, 5vw, 76px)"
    fontWeight: 900
    lineHeight: 0.98
    letterSpacing: "-2px"
  headline:
    fontFamily: "Montserrat, sans-serif"
    fontSize: "clamp(32px, 4vw, 52px)"
    fontWeight: 900
    lineHeight: 1.08
  title:
    fontFamily: "Montserrat, sans-serif"
    fontSize: "20px"
    fontWeight: 900
    lineHeight: 1.3
  body:
    fontFamily: "Montserrat, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "Montserrat, sans-serif"
    fontSize: "12px"
    fontWeight: 800
    letterSpacing: "0.8px"
rounded:
  pill: "999px"
  xl: "44px"
  lg: "34px"
  md: "26px"
  sm: "18px"
  icon: "18px"
spacing:
  xs: "8px"
  sm: "16px"
  md: "24px"
  lg: "44px"
  xl: "76px"
  section: "90px"
components:
  button-primary:
    backgroundColor: "{colors.operational-cyan}"
    textColor: "{colors.clear-signal}"
    rounded: "{rounded.pill}"
    padding: "17px 30px"
  button-primary-hover:
    backgroundColor: "{colors.command-signal}"
    textColor: "{colors.clear-signal}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.clear-signal}"
    rounded: "{rounded.pill}"
    padding: "17px 30px"
  tag-badge:
    backgroundColor: "{colors.operational-cyan}"
    textColor: "{colors.clear-signal}"
    rounded: "{rounded.pill}"
    padding: "9px 15px"
  input-field:
    backgroundColor: "{colors.command-black}"
    textColor: "{colors.clear-signal}"
    rounded: "{rounded.sm}"
    padding: "17px 18px"
  kpi-card:
    backgroundColor: "{colors.ops-navy}"
    textColor: "{colors.clear-signal}"
    rounded: "{rounded.md}"
    padding: "24px"
---

# Design System: NEXO-147

## 1. Overview

**Creative North Star: "El Centro de Operaciones"**

NEXO-147 vive en una sala de mando. La interfaz es oscura por necesidad operativa: bajo nivel de luz ambiental, largas jornadas, monitores compartidos. El fondo negro profundo (`#07111f`) no es estética — es ergonomía institucional. El cian operativo (`#2596be`) y el verde de estado (`#6fca52`) son los únicos puntos de color de alto contraste porque en una sala de mando, el color es señal, no decoración.

El sistema rechaza explícitamente la densidad torpe de los sistemas gubernamentales heredados: campos grises apilados, tipografía sin jerarquía, formularios que parecen impresos escaneados. NEXO-147 debe sentirse como herramienta de profesionales de seguridad, no como sistema de la década del 2000.

La profundidad visual se construye con capas de vidrio tintado (`backdrop-filter: blur`), sombras difusas amplias, y gradientes radiales sutiles — nunca con bordes sólidos ni sombras duras. El sistema es cohesivo y deliberado: cada superficie emite la misma señal de autoridad institucional moderna.

**Key Characteristics:**
- Fondo negro profundo como base permanente — no hay tema claro
- Cian y verde como únicos colores funcionales; todo lo demás es neutro
- Tipografía Montserrat en pesos extremos (900) para máxima legibilidad en pantallas oscuras
- Glassmorfismo estructural, no decorativo — las superficies de vidrio organizan el contenido
- Animaciones de estado, nunca decorativas — el radar gira, las órbitas rotan, los pulsos indican actividad real

## 2. Colors: La Paleta de Mando

Los colores de NEXO-147 son señales, no estética. Cada tono tiene un rol operativo único.

### Primary
- **Cian Operativo** (`#2596be`): Color de acción primaria. Botones CTA, bordes de énfasis, glow en elementos interactivos. Es el color que dice "este es el camino".
- **Señal de Mando** (`#41d2ff`): Variante más brillante del cian, reservada para el dashboard y elementos de estado activo de alta prominencia. Más eléctrica, más urgente.

### Secondary
- **Verde Estado** (`#6fca52` / `#74e04b`): Color de datos positivos, KPIs, confirmaciones, valores en tiempo real. Verde = sistema operando correctamente. Nunca usado como decoración.

### Tertiary
- **Rojo Crítico** (`#ff5a5a`): Exclusivo para alertas, casos críticos, estados de error. Aparece solo cuando algo requiere atención inmediata.

### Neutral
- **Negro de Comando** (`#07111f`): Background del cuerpo. El más oscuro. Fondo permanente del sistema.
- **Azul Operaciones** (`#0d1b2e`): Superficie secundaria. Cards, formularios, panels. Ligeramente más claro que el fondo.
- **Señal Clara** (`#eefbff`): Texto principal sobre fondo oscuro. Alto contraste garantizado.
- **Niebla Ops** (`#b7d2dc`): Texto secundario, labels, metadata. Legible pero subordinado.
- **Cian Profundo** (`#176f8d`): Variante oscura del primario. Hover states, borders profundos.

### Named Rules
**La Regla del Color como Señal.** El color cian y el verde son señales operativas. Si no hay acción que tomar ni estado que comunicar, no hay color. Fondos, separadores y contenido estático son siempre neutrales.

**La Regla del Rojo Escaso.** El rojo crítico aparece en ≤5% de la pantalla en cualquier momento. Su poder viene de su rareza. Un dashboard lleno de rojo deja de comunicar urgencia.

## 3. Typography

**Display / Body Font:** Montserrat (con fallback sans-serif genérico)
**Fuente única** — NEXO-147 usa Montserrat en todos los niveles. La jerarquía se logra con variación agresiva de peso (400 a 900) y escala de tamaño, no con familias diferentes.

**Character:** Montserrat en peso 900 tiene autoridad institucional sin rigidez burocrática. Su geometría limpia es legible en pantallas oscuras de baja resolución y en displays de alta densidad por igual. Los pesos medios (600-700) trabajan como body text sin esfuerzo.

### Hierarchy
- **Display** (900, clamp 44-76px, line-height 0.98): Solo para el nombre del producto y titulares del hero. Letra-espaciado -2px. No más de 6 palabras.
- **Headline** (900, clamp 32-52px, line-height 1.08): Títulos de sección principales. Máximo 2 niveles por página.
- **Title** (900, 20-21px, line-height 1.3): Encabezados de cards, secciones de formulario, paneles del dashboard.
- **Body** (400-700, 14-18px, line-height 1.65-1.75): Texto descriptivo, contenido de formularios. Máximo 65-75ch de ancho.
- **Label** (800-900, 12-13px, 0.7-1.4px tracking, UPPERCASE): Tags, badges, encabezados de tabla, metadatos de campo.

### Named Rules
**La Regla del Peso Extremo.** En pantallas oscuras, el texto delgado desaparece. NEXO-147 no usa pesos menores a 600 en elementos interactivos ni en encabezados. El peso 900 es la norma, no la excepción.

## 4. Elevation

NEXO-147 usa un sistema de elevación **atmosférica**: las superficies no se levantan con sombras duras sino con sombras difusas amplias y tintado por capas. La profundidad es espacial, no material.

Tres capas bien definidas:
1. **Background** (`#07111f`): El suelo. Sin elevación.
2. **Surface** (`#0d1b2e` + glassmorfismo): Cards, panels, formularios. Elevados con backdrop-blur y fondo semitransparente.
3. **Overlay**: Headers flotantes, cards de alert. La capa más alta, con sombras de hasta 100px de dispersión.

### Shadow Vocabulary
- **Sombra difusa de card** (`0 24px 60-70px rgba(0,0,0,.26-.35)`): Sombra estándar de superficie. Produce sensación de flotación sin borde.
- **Sombra de capa alta** (`0 34px 100px rgba(0,0,0,.42)`): Modales, headers fijos, elementos over content.
- **Glow operativo** (`0 0 24-70px rgba(37,150,190,.38-.70)`): Reservado para elementos activos, botones primarios en hover, núcleos de animación. Indica estado, no profundidad.
- **Glow verde** (`0 0 22-45px rgba(111,202,82,.55-.80)`): Usado en puntos de mapa, dots activos, indicadores de señal.

### Named Rules
**La Regla del Glow como Estado.** El resplandor (glow) indica actividad o acción disponible, nunca decoración en reposo. Un elemento con glow permanente en reposo pierde su capacidad de señalar estado activo.

## 5. Components

### Buttons
**Forma:** Totalmente redondeados (`border-radius: 999px`). La píldora es la forma universal de acción en NEXO-147.

- **Primary** (`#2596be` → `#48cbe8` gradiente lineal 135°, texto blanco, padding 17px 30px): Para la acción principal de cada pantalla. Box-shadow con glow cian en reposo; en hover, translateY(-4px) + sombra amplificada.
- **Ghost** (fondo rgba(255,255,255,.06), border cian, texto claro): Para acciones secundarias. En hover, fondo verde suave.
- **Estados críticos:** Ningún botón debe aparecer sin estado hover visible. El glow es la señal de interactividad.

### Tags / Badges
Píldora con fondo rgba(37,150,190,.15), border cian suave, texto UPPERCASE 12px peso 900. Usados como clasificadores de contexto — "Demo institucional privada", "Centro de mando demo". Solo en mayúsculas completas porque son etiquetas de categoría, no frases.

### Cards / Containers
- **Corner Style:** 26-34px (`.dashboard-card`, `.kpi-card`), 42-44px (secciones hero, hero panel). Las secciones más grandes tienen radios más grandes.
- **Background:** Glassmorfismo — `rgba(255,255,255,.08-.10)` + `backdrop-filter: blur(14-18px)` + gradiente radial sutil.
- **Shadow:** Difusa, 0 24-34px 60-100px rgba(0,0,0,.26-.42).
- **Border:** 1px solid rgba(37,150,190,.24-.34). El borde es la delimitación, no la sombra.
- **Internal Padding:** 22-30px en cards de dashboard; 28px en service cards; 42-46px en login card.

### Inputs / Fields
- **Style:** Fondo `rgba(4,13,25,.74)`, border 1px rgba(37,150,190,.30), border-radius 18px, padding 17px 18px.
- **Focus:** Border-color cambia a verde estado (`#6fca52`) + box-shadow glow verde (`0 0 0 4px rgba(111,202,82,.17)`).
- **Placeholder:** `rgba(238,251,255,.55)` — suficientemente visible para orientar, lo suficientemente sutil para no confundir con valor real.
- **Select:** Fondo `#061827` en options para mantener el tema oscuro.

### Navigation
- **Style:** Links de píldora, padding 11px 14px, texto muted 13px peso 800. Sin subrayado ni indicadores visuales pasivos.
- **Hover:** Fondo `rgba(37,150,190,.15)` + glow cian. El hover es la única señal de interactividad.
- **Active:** No hay estado active implementado — pendiente de mejora.
- **Mobile:** Collapse a flex-wrap centrado a partir de 1050px. Los links reducen a 12px.

### KPI Cards (componente firma)
Cards de métrica operativa con gradiente radial top-right en cian o rojo (para casos críticos), borde cian, sombra difusa. El número es blanco 34px peso 900; el label es muted 12px uppercase. Esta es la unidad visual más repetida en el dashboard.

### Orbit / Radar (componentes visuales)
Elementos decorativos-funcionales que comunican el tema operativo: anillos rotantes concéntricos, radares con sweep, puntos de mapa con pulse. No son puramente decorativos — señalan que el sistema está "activo" y "monitoreando". Deben mantener `prefers-reduced-motion` consideration.

## 6. Do's and Don'ts

### Do:
- **Do** usar `#07111f` como único background de body. Nunca sustituir con beige, arena, crema u otro neutro cálido.
- **Do** reservar el color cian (`#2596be` / `#41d2ff`) para acciones primarias y estados activos exclusivamente.
- **Do** usar peso 900 en todos los headings y elementos de navegación. El peso 400 es solo para body text y descripciones.
- **Do** aplicar `backdrop-filter: blur(14-18px)` en todas las cards y panels flotantes para mantener coherencia de elevación.
- **Do** usar el verde estado (`#6fca52`) para KPIs positivos, confirmaciones y focus states de formulario.
- **Do** separar el contenido de Admin y Operador visualmente. El operador ve solo el formulario; el admin ve el sistema completo. La diferencia de roles debe ser obvia sin texto explicativo.
- **Do** mantener el glow como señal de estado activo o interactividad — nunca en elementos en reposo sin propósito.

### Don't:
- **Don't** usar sistemas gubernamentales legacy como referencia: sin campos grises apilados, sin tablas planas sin jerarquía, sin tipografía de peso regular en elementos de control.
- **Don't** agregar colores adicionales más allá del vocabulario definido. Cian, verde y rojo son los únicos colores funcionales. Todo lo demás es neutro.
- **Don't** usar `border-left` mayor a 1px como acento de color en cards o elementos de lista.
- **Don't** aplicar `background-clip: text` con gradientes para texto decorativo.
- **Don't** poner texto gris muted sobre fondos de color tintado sin verificar contraste. Sobre fondos con tinte cian, usar tono de cian oscuro o blanco — nunca el gris muted genérico.
- **Don't** usar el rojo crítico fuera de estados de error, alerta máxima o casos críticos. Un formulario estándar no tiene rojo.
- **Don't** animar propiedades de layout (width, height, top, left) sin necesidad operativa. Las animaciones de NEXO-147 usan transform y opacity.
- **Don't** mostrar el dashboard (sección admin) a usuarios con rol operador. La separación de roles es funcional, no solo visual.
