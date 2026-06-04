# OSINT Graph Visualization — Rediseño Completo

**Fecha:** 2026-06-04
**Estado:** Aprobado
**Alcance:** Frontend únicamente — backend Flask/SQLite sin cambios

---

## Objetivo

Transformar la visualización de grafo OSINT actual (Cytoscape.js + COSE layout) en una herramienta de análisis visual de inteligencia de nivel profesional, con estética cercana a VOSviewer/Linkurious/GraphXR. Prioridad: descubrimiento de patrones, identificación de comunidades, visualización de entidades centrales y exploración fluida.

---

## Decisiones de diseño confirmadas

| Decisión | Elección |
|---|---|
| Motor de visualización | Sigma.js v3 + Graphology |
| Build tooling | Vite (subcarpeta `frontend/`) |
| Color de nodos | Color = comunidad (Louvain) |
| Tipo de entidad | Comunicado por forma del nodo |
| Layout | ForceAtlas2 (graphology-layout-forceatlas2) |
| Expansión de nodo | Visual únicamente (sin nuevas llamadas al backend) |
| Métrica de centralidad | Degree (default) + Betweenness (selector en toolbar) |

---

## Arquitectura

### Estructura de archivos

```
DEMO_GAULA/
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── osint-graph.js       # entry point; expone window.OsintGraph.init()
│       ├── graph-layout.js      # ForceAtlas2 + Louvain clustering
│       ├── graph-renderer.js    # Sigma.js config, node renderers, estilos
│       └── graph-panel.js       # Panel lateral de detalle de entidad
│
└── static/js/
    └── osint-graph.bundle.js    # Output de Vite; commiteado al repo
```

### Flujo de build

```bash
cd frontend && npm run build
# escribe a ../static/js/osint-graph.bundle.js
```

Se recomienda commitear el bundle al repositorio para que Flask lo sirva sin necesitar Node.js en producción. Si se usa CI, puede excluirse con `.gitignore` y regenerarse en cada build de pipeline.

### Integración en Flask

`console.html` carga el bundle como script estático normal:

```html
<script src="{{ url_for('static', filename='js/osint-graph.bundle.js') }}" defer></script>
```

El bundle expone `window.OsintGraph` con los métodos:
- `init(containerId: string)` — monta Sigma.js en el contenedor; se llama **una sola vez** al cargar la página (DOMContentLoaded o equivalente)
- `load(data: {nodes, links, findings, stats})` — carga un nuevo grafo; se llama cada vez que el usuario pulsa "CARGAR GRAFO"
- `reset()` — limpia el canvas sin destruir la instancia Sigma
- `setMetric(metric: 'degree' | 'betweenness')` — recalcula tamaños de nodos en vivo

La función `osintLoadGraph()` en `console.html` pasa a llamar `OsintGraph.load(data)` en lugar de construir el grafo Cytoscape internamente.

### Dependencias

| Paquete | Versión | Propósito |
|---|---|---|
| `sigma` | ^3.x | Renderer WebGL |
| `graphology` | ^0.26 | Estructura de datos de grafo |
| `graphology-communities-louvain` | ^2.x | Detección de comunidades |
| `graphology-metrics` | ^2.x | Degree y betweenness centrality |
| `graphology-layout-forceatlas2` | ^0.10 | Layout físico tipo VOSviewer |

**Sin cambios al backend.** El endpoint `/osint/analytics/graph` devuelve el mismo JSON `{nodes, links, findings, stats}` de siempre.

---

## Lenguaje visual

### Fondo

`#0B1220`. Sin círculos decorativos, sin halos gigantes. Canvas limpio.

### Clustering y color

Louvain detecta comunidades en el grafo cargado. Paleta de 8 colores fija:

| ID | Color | Hex |
|---|---|---|
| C0 | Azul acero | `#4E91D9` |
| C1 | Naranja inteligencia | `#E8734A` |
| C2 | Verde OSINT | `#5DC896` |
| C3 | Violeta | `#B87FD4` |
| C4 | Ámbar alerta | `#E8C84A` |
| C5 | Cian | `#4DC4C4` |
| C6 | Rosa señal | `#E06B8B` |
| C7 | Gris azulado | `#8FA8C8` |

El **nodo objetivo** (`is_target: true`) recibe siempre un anillo dorado `#C8A84B`, independientemente de su comunidad.

### Tamaño de nodos

Escala logarítmica. Metric por defecto: degree centrality.

```js
const size = node.is_target
  ? 42
  : 6 + 30 * Math.log(degree + 1) / Math.log(maxDegree + 1)
```

Rango: 6px (periférico) → 36px (central) → 42px (objetivo).

El usuario puede cambiar a betweenness centrality desde la toolbar. El grafo recalcula tamaños sin recargar datos.

### Forma de nodos por tipo de entidad

| Tipo | Forma |
|---|---|
| person | circle |
| alias | square |
| email | diamond |
| organization | pentagon (custom renderer) |
| domain | square |
| ip | diamond |
| repository | circle (tamaño reducido) |
| social_profile | star 5 puntas (custom renderer) |
| location | triangle |
| platform | circle (borde punteado) |
| url | circle (mínimo) |

Las formas custom (`pentagon`, `star`) se registran como `NodeProgramClass` en Sigma.js v3.

### Etiquetas

| Condición | Etiquetas visibles |
|---|---|
| zoom < 0.35 | Solo nodo objetivo |
| zoom 0.35–0.60 | Objetivo + degree ≥ 4 |
| zoom 0.60–0.90 | Objetivo + degree ≥ 2 |
| zoom > 0.90 | Todos los nodos |

Tamaño: `fontSize = 8 + size * 0.28`. Fuente: `"Inter", "Open Sans", sans-serif`.

### Aristas

- Opacidad base: `0.12`
- Grosor: `0.5 + confidence * 1.5`
- Color: `#2a3a4a` (gris neutro)
- Curvas bezier, sin flechas en reposo
- Sin etiquetas en reposo; la etiqueta de relación aparece solo en hover

### Layout — ForceAtlas2

```js
{
  iterations: 500,
  settings: {
    gravity: 1,
    scalingRatio: 10,
    strongGravityMode: false,
    barnesHutOptimize: true,
    linLogMode: true,
    outboundAttractionDistribution: true,
  }
}
```

Corre en Web Worker (soporte nativo en Sigma.js v3 + graphology-layout-forceatlas2). El canvas muestra la animación de convergencia en tiempo real.

---

## Modelo de interacción

### Hover sobre nodo
- Nodo + vecinos directos: opacidad `1.0`
- Aristas conectadas: opacidad `0.7`, etiqueta de relación visible
- Resto del grafo: opacidad `0.08`
- Transición de salida: `150ms`
- Cursor: `pointer`

### Click (selección)
- Abre panel lateral con ficha completa del nodo
- Nodo seleccionado: anillo blanco `#ffffff` + glow
- Vecinos directos: opacidad `1.0`
- Resto: opacidad `0.15`
- Click en fondo del canvas: deselecciona, restaura grafo

### Doble click (expansión visual)
- Subgrafo del nodo (nodo + vecinos + aristas entre ellos) al primer plano
- Resto del grafo: opacidad `0.05`
- Botón "← Grafo completo" en toolbar restaura el estado normal
- Sin llamadas adicionales al backend

### Zoom y pan
- Zoom con scroll: `wheelSensitivity: 0.3`, rango `[0.05, 8]`
- Pan con drag sobre fondo
- Botón "⊞ Ajustar" en toolbar: `camera.reset()`

---

## Panel lateral — ficha de entidad

Reemplaza el `.og-detail` actual. Estructura visual:

```
┌─────────────────────────────┐
│  [banda de color comunidad] │
│  [icono SVG tipo]  LABEL    │
│  ● Comunidad #2             │
├─────────────────────────────┤
│  Riesgo    [ALTO ████]      │
│  Confianza  ████████░  88%  │
│  Fuente     github_api      │
│  Detectado  2025-06-04      │
├─────────────────────────────┤
│  ATRIBUTOS                  │
│  email    vic@example.com   │
│  org      Servialco S.A.    │
├─────────────────────────────┤
│  RELACIONES  (3)            │
│  → alias_en_x   @vic_tw    │
│  → usa_correo   vic@…      │
│  ← activo_en    GitHub     │
└─────────────────────────────┘
```

- Banda de color = color de comunidad del nodo
- Iconos SVG inline, uno por tipo de entidad (11 SVGs)
- Sin tablas HTML — `div` flex con separadores
- Las relaciones listadas son clicables: la cámara hace pan+zoom al nodo vecino y su ficha se abre en el panel lateral

---

## Leyenda de comunidades

Reemplaza la leyenda actual de tipos. Muestra comunidades detectadas por Louvain:

```
● Comunidad 1  (8 entidades)
● Comunidad 2  (5 entidades)
● Comunidad 3  (3 entidades)
```

Click en item de leyenda resalta esa comunidad en el grafo.

---

## Toolbar

```
[input objetivo] [CARGAR] [LIMPIAR] [⊞ Ajustar] | Métrica: [degree ▾]
```

El selector de métrica (`degree` / `betweenness`) recalcula tamaños de nodos en vivo.

---

## Hallazgos automáticos (Findings)

El backend ya genera `data.findings` con `{nivel, titulo, descripcion, icon}`. El frontend los renderiza debajo del canvas como tarjetas:
- Borde izquierdo coloreado por nivel (Crítico/Alto/Medio/Bajo/Info)
- Icono + título en `#e0eaf8`
- Descripción en `#6b8aaa`

Sin cambios al backend.

---

## Performance

- ForceAtlas2 en Web Worker — no bloquea UI
- `barnesHutOptimize: true` para grafos >200 nodos
- Level-of-detail en etiquetas según zoom (label culling nativo de Sigma.js)
- Sigma.js v3 WebGL renderer: fluido con 2000+ nodos

---

## Lo que NO cambia

- Backend Flask, SQLite, `graph_builder.py`, todos los endpoints
- Las funciones `osintFetchSocial()`, `osintFetchOpendata()` en `console.html`
- La estructura de tabs OSINT (Redes Sociales / Datos Abiertos / Grafo)
- El HTML del contenedor `#osint-tab-graph` excepto quitar el `<style>` inline de Cytoscape
- Los findings del backend

---

## Lo que SÍ cambia

- Todo el bloque JS de Cytoscape dentro de `osintLoadGraph()` → reemplazado por `OsintGraph.load(data)`
- El bloque `<style>` inline del tab Grafo → simplificado (solo estructura, sin estilos Cytoscape)
- Se elimina la dependencia CDN de Cytoscape.js de `base.html` o `console.html`
- Se agrega `<script>` del bundle Vite en `console.html`
- Se agrega `frontend/` al repo con su `package.json`
