# Diseño: Potenciar tab "Datos Abiertos" del módulo OSINT

**Fecha:** 2026-06-10
**Proyecto:** DEMO_GAULA (NEXO-147)
**Rama:** desarrollador1
**Estado:** Aprobado por el usuario — listo para plan de implementación

---

## 1. Objetivo

Hacer efectiva la búsqueda en el tab "Datos Abiertos" para tres tipos de término:

1. **Placa de vehículo** → infracciones de tránsito reales (SIMIT, datos.gov.co).
2. **Cédula de ciudadanía** → actividad pública legítima de la persona (RUES, comparendos con identificación, menciones web).
3. **Teléfono** → mantener el módulo de identificación que ya funciona y reutilizar su lógica de dorking para los otros tipos.

## 2. Alcance y límite legal (decisión tomada)

El usuario pidió originalmente "buscar cédulas en RNMC, Policía o Función Pública". Tras investigar las fuentes:

- Los datasets de **RNMC / medidas correctivas** en datos.gov.co son **estadísticas agregadas** (conteos por municipio/artículo) — **no contienen cédulas individuales**.
- **Función Pública / SIGEP** en datos.gov.co son **agregados por entidad** — sin cédulas de personas.
- Las consultas individuales reales (RNMC, antecedentes judiciales, Procuraduría) están **protegidas con CAPTCHA** y su automatización masiva choca con Habeas Data (Ley 1581 de 2012).

**Decisión:** la búsqueda por cédula traerá únicamente lo **legítimamente público**:
- **RUES** (actividad mercantil: matrícula, razón social, estado).
- **Comparendos** donde la identificación aparezca publicada (dataset `rfag-apa4`).
- **Menciones web** (dorking DuckDuckGo).

No se implementa scraping de RNMC/Policía/Procuraduría.

Para placas, el usuario eligió el **dataset abierto de datos.gov.co** (estable y legal) en lugar de reverse-engineering del portal fcm.org.co en tiempo real.

## 3. Arquitectura

Se mantiene el patrón existente sin cambios estructurales:

- Cada fuente es un `Connector` que hereda de `BaseConnector` y devuelve `ConnectorResult` (nunca lanza excepción; los errores van a `ConnectorResult.errors`).
- `OsintOrchestrator` ejecuta los conectores aplicables en paralelo (`max_workers`, `timeout`).
- El router `opendata/routes.py` detecta el tipo de término y selecciona qué conectores correr.
- El fragmento `templates/osint/opendata_fragment.html` renderiza cada sección de forma colapsable e independiente.

### Detección de tipo (`_detect_type`)

Orden de evaluación:

1. `phone` — coincide `^(\+57|57)?3\d{9}$` o empieza con `+`.
2. `plate` — coincide `^[A-Za-z]{3}[0-9A-Za-z]{3}$`.
3. `document` — solo dígitos, longitud 6–10.
4. `name` — contiene espacio y al menos una letra (nuevo).
5. `unknown` — cualquier otro caso.

### Matriz de orquestación

| Tipo entrada | Conectores que corren | Fuente concreta |
|---|---|---|
| `plate` | SIMIT + Dork web | dataset `72nf-y4v3` (campo `placa`) |
| `document` | SIMIT(doc) + RUES + Dork web | `rfag-apa4` (campo `identificacion`) + RUES API |
| `phone` | Phone | phonenumbers + NumVerify + DDG (sin cambios) |
| `name` | RUES + Dork web | RUES razón social |
| `unknown` | Dork web | DuckDuckGo |

## 4. Componentes

### 4.1 SimitConnector (arreglar — `modules/osint/connectors/simit.py`)

**Problema actual:** el código y la plantilla leen campos que no existen en `72nf-y4v3`
(`numero_identificacion`, `nombre`, `valor_a_pagar`, `estado`, `fecha_infraccion`, `municipio`).
Por eso hoy la búsqueda por placa devuelve filas con guiones.

**Campos reales de `72nf-y4v3`:** `vigencia`, `placa`, `fecha_multa`, `valor_multa`, `departamento`, `ciudad`, `pagado_si_no`.

**Cambios:**
- `_build_where` para placa consulta `72nf-y4v3` con `upper(placa)=upper('...')`.
- Para `document`, consultar el dataset `rfag-apa4` (tiene `identificacion` + `placa`) con `identificacion='...'`.
- El conector expone qué dataset usó y normaliza las filas a una forma estable que la plantilla pueda renderizar: `{placa, fecha, valor, lugar, estado, vigencia, identificacion?}`.
- Mantener `supported_target_types = {document, plate, unknown}`.
- Saneamiento de comillas en el `$where` (ya existe; conservar).

### 4.2 RuesConnector (nuevo — `modules/osint/connectors/rues.py`)

- `supported_target_types = {document, name}`.
- `needs_api_key = False`.
- Consulta el API público de RUES (`ruesapi.rues.org.co`) por número de documento o razón social.
- Devuelve por cada expediente: `razon_social`, `matricula`, `estado` (activa/cancelada), `camara`, `tipo`, `nit`/`identificacion`.
- Falla elegante: si el endpoint cambia, bloquea o responde no-JSON, devuelve `ConnectorResult(ok=False)` con el error en `errors`, sin romper la página.
- El endpoint exacto y los parámetros se confirman durante implementación con una llamada de verificación; el contrato del conector (entrada/salida) no depende de ese detalle.

### 4.3 Web dork helper (refactor — `modules/osint/connectors/web_dork.py`)

- Extraer la lógica DuckDuckGo que hoy vive embebida en `phone.py` a una función reutilizable: `run_dork(queries: list[str], max_results: int) -> tuple[list[dict], list[str]]` que devuelve `(resultados, errores)`.
- Maneja `RatelimitException` / `DuckDuckGoSearchException` y deduplica por URL (igual que hoy).
- `phone.py` pasa a llamar este helper en vez de tener la lógica inline.
- El router lo usa para `document`, `plate` y `name` con consultas apropiadas (la cédula/placa entre comillas + contexto "Colombia").

### 4.4 PhoneConnector (sin cambios funcionales)

- Se mantiene; solo se ajusta para delegar el dorking a `web_dork.run_dork`.

### 4.5 Router (`modules/osint/opendata/routes.py`)

- `_detect_type` ampliado con `name`.
- Selección de conectores según la matriz de orquestación.
- Agrega resultados de SIMIT, RUES, Phone y Dork en el contexto de la plantilla.
- Conserva la validación de longitud (máx. 100 caracteres) y de término vacío.
- `sources_queried` / `findings_count` recalculados para incluir RUES y dork.

### 4.6 Template (`templates/osint/opendata_fragment.html`)

- **SIMIT:** columnas corregidas a campos reales (`Placa, Fecha, Valor, Lugar, Estado/Pagado, Vigencia`); en búsqueda por cédula mostrar también `Identificación`.
- **RUES:** nueva sección con tabla de expedientes (razón social, matrícula, estado, cámara).
- **Menciones web:** sección genérica reutilizando el render de dorks que ya existe para teléfono, ahora disponible para cédula/placa/nombre.
- Mantener el estilo militar/institucional vigente y el patrón colapsable `odToggle`.

## 5. Manejo de errores

- Ningún conector lanza excepción hacia el router; todo error queda en `ConnectorResult.errors`.
- La plantilla muestra por fuente un badge: `✓ (n)` / `sin resultados` / `error`.
- Rate limit de DDG y bloqueos de RUES se muestran como aviso, no como fallo total de la página.

## 6. Configuración / dependencias

- **No requiere dependencias nuevas.** `requests`, `phonenumbers`, `duckduckgo-search` ya están en `requirements.txt`.
- SIMIT, RUES y dorking son públicos y **no requieren claves**.
- `NUMVERIFY_API_KEY` sigue siendo **opcional** (solo enriquece teléfono).

## 7. Testing

Actualizar/ampliar `tests/test_opendata_connectors.py` y `tests/test_opendata_routes.py`:

- `_detect_type`: placa, cédula, teléfono, nombre, unknown.
- `SimitConnector._build_where`: ruta placa (`72nf-y4v3`) y ruta documento (`rfag-apa4`), con saneamiento de comillas.
- `SimitConnector.fetch`: parsing de filas mockeadas → forma normalizada; caso sin resultados → `ok=False`.
- `RuesConnector.fetch`: respuesta mockeada → expedientes; respuesta no-JSON / error HTTP → `ok=False` con error capturado.
- `web_dork.run_dork`: dedup por URL y manejo de rate limit (mock de `DDGS`).
- Router: cada tipo de término dispara los conectores correctos y arma el contexto esperado (con conectores mockeados).

## 8. Criterios de éxito

1. Buscar una placa real devuelve filas de SIMIT con datos visibles (no guiones).
2. Buscar una cédula devuelve, cuando exista, expedientes RUES y/o comparendos con identificación y/o menciones web — sin errores 500.
3. La búsqueda por teléfono sigue funcionando igual que hoy.
4. Toda fuente que falle se degrada con un aviso, sin tumbar la página.
5. Los tests pasan.

## 9. Fuera de alcance (YAGNI)

- Scraping de RNMC/Policía/Procuraduría (CAPTCHA + Habeas Data).
- SIMIT en tiempo real desde fcm.org.co.
- Rama Judicial y SECOP (descartados por el usuario en esta iteración; pueden añadirse después como conectores nuevos sin cambiar la arquitectura).
- Persistencia/exportación de resultados de este tab.
