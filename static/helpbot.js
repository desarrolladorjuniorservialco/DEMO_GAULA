/* Guía Contextual NEXO-147 — Help widget por página y panel */
(function () {
    'use strict';

    /* Contenido por sección de panel (console.html — SPA) */
    var CONTENIDO_PANEL = {
        'panel-inicio': {
            titulo: 'Consola Central GAULA',
            puntos: [
                'Sistema de centralización y procesamiento de denuncias y operaciones del GAULA Militar a nivel nacional.',
                'Navega entre módulos usando la barra lateral izquierda.',
                'Los indicadores superiores muestran el estado operativo en tiempo real.'
            ]
        },
        'panel-formulario': {
            titulo: 'Registrar Reporte — Línea 147',
            puntos: [
                'Comunicación: tono cordial, vocalización clara y velocidad moderada; evita tecnicismos.',
                'Actitud: escucha activa, empatía y autocontrol; no discutir con el denunciante.',
                'Seguridad: valida identidad antes de compartir información; cumple políticas de protección de datos.',
                'Proceso: saludo → presentación → identificación → escucha → validación → gestión → confirmación → cierre.'
            ]
        },
        'panel-casos': {
            titulo: 'Bandeja de Casos',
            puntos: [
                'Histórico de reportes y denuncias recibidas por la Línea 147.',
                'Haz clic en "Ver ficha" para acceder al detalle completo del reporte.',
                'Filtra por estado, fecha o unidad GAULA responsable.'
            ]
        },
        'panel-entidades': {
            titulo: 'Base de Entidades',
            puntos: [
                'Acceso a información suministrada por entidades aliadas al sistema.',
                'Usa el buscador para localizar entidades por nombre o identificador.',
                'Los vínculos entre entidades se visualizan en el módulo de inteligencia.'
            ]
        },
        'panel-inteligencia': {
            titulo: 'Módulo OSINT — Inteligencia',
            puntos: [
                'Búsqueda masiva de información de individuos en bases de datos públicas.',
                'Antes de consultar: ¿qué necesito encontrar? ¿a quién o qué estoy investigando?',
                '¿Cuál es el resultado esperado? ¿Qué información es prioritaria?',
                'Los resultados se clasifican por relevancia y fuente de origen.'
            ]
        },
        'panel-hallazgos': {
            titulo: 'Hallazgos Intel',
            puntos: [
                'Procesamiento de información alojada en las bases de datos del sistema NEXO-147.',
                'Las proyecciones se generan con modelos de regresión calibrados para los escenarios planteados.',
                'Contrasta los hallazgos con la información de la Bandeja de Casos.'
            ]
        },
        'panel-datamart': {
            titulo: 'Data Mart IA',
            puntos: [
                'Procesamiento y análisis de información de operaciones del GAULA.',
                'Presentación de datos georeferenciados y métricas generales de actividad operativa.',
                'Los valores en ámbar requieren revisión por parte del analista.'
            ]
        }
    };

    /* Contenido por ruta URL (páginas standalone) */
    var CONTENIDO_RUTA = {
        '/login': {
            titulo: 'Acceso al sistema',
            puntos: [
                'Usa las credenciales asignadas por tu unidad GAULA.',
                'El rol determina las secciones disponibles tras iniciar sesión.',
                'Ante problemas de acceso, contacta al administrador.'
            ]
        },
        '/dashboard': {
            titulo: 'Panel de control operativo',
            puntos: [
                'Los KPIs muestran el estado operativo en tiempo real.',
                'Haz clic en los encabezados de tabla para ordenar y filtrar.',
                'Los valores en ámbar indican alertas que requieren atención.'
            ]
        },
        '/api_externa': {
            titulo: 'Verificación de brechas',
            puntos: [
                'Ingresa el dominio o correo a verificar en el campo de búsqueda.',
                'Los resultados indican si las credenciales han sido comprometidas.',
                'Reporta hallazgos críticos al administrador del sistema.'
            ]
        },
        '/osint/search': {
            titulo: 'Búsqueda OSINT',
            puntos: [
                'Búsqueda masiva de información de individuos en bases de datos públicas.',
                'Antes de consultar: ¿qué necesito encontrar? ¿a quién estoy investigando?',
                '¿Cuál es el resultado esperado? ¿Qué información es prioritaria?'
            ]
        },
        '/osint/history': {
            titulo: 'Historial de consultas OSINT',
            puntos: [
                'Muestra todas las búsquedas OSINT realizadas por el usuario.',
                'Haz clic en una entrada para ver los resultados completos.',
                'Filtra por fecha para acotar el rango de búsqueda.'
            ]
        },
        '/osint/watchlists': {
            titulo: 'Listas de vigilancia',
            puntos: [
                'Registra objetivos bajo monitoreo continuo del sistema.',
                'El indicador de estado muestra si hay alertas activas.',
                'Agrega nuevos objetivos desde el botón en la parte superior.'
            ]
        },
        '/osint': {
            titulo: 'Dashboard de inteligencia OSINT',
            puntos: [
                'Los nodos del grafo representan entidades vinculadas entre sí.',
                'Aplica filtros en el panel lateral para afinar el análisis.',
                'Los resultados se clasifican por relevancia y fuente de origen.'
            ]
        }
    };

    var PAGINA_DEFAULT = {
        titulo: 'Guía del sistema NEXO-147',
        puntos: [
            'Navega por los módulos usando el menú superior.',
            'Usa el asistente (ícono de chat) para consultas rápidas.',
            'Los datos se actualizan automáticamente en tiempo real.'
        ]
    };

    function obtener_panel_activo() {
        var activa = document.querySelector('.panel-section.active');
        return activa ? activa.id : null;
    }

    function obtener_contenido() {
        /* Check active panel section first (console.html SPA) */
        var panelId = obtener_panel_activo();
        if (panelId && CONTENIDO_PANEL[panelId]) return CONTENIDO_PANEL[panelId];

        /* Fall back to URL-based content */
        var ruta = window.location.pathname;
        var claves = Object.keys(CONTENIDO_RUTA).sort(function (a, b) { return b.length - a.length; });
        for (var i = 0; i < claves.length; i++) {
            var clave = claves[i];
            if (ruta === clave || (clave !== '/' && ruta.indexOf(clave) === 0)) {
                return CONTENIDO_RUTA[clave];
            }
        }
        return PAGINA_DEFAULT;
    }

    var estado = { panel: null, trigger: null, barra: null, timer: null, abierto: false };

    function construir_items(lista, puntos) {
        lista.innerHTML = '';
        puntos.forEach(function (punto) {
            var li = document.createElement('li');
            li.className = 'help-item';
            li.textContent = punto;
            lista.appendChild(li);
        });
    }

    function crear_html(contenido) {
        var contenedor = document.getElementById('chatbot-widget');
        if (!contenedor) return false;

        /* Build help panel */
        var panel = document.createElement('div');
        panel.className = 'help-panel';
        panel.id = 'help-panel';
        panel.setAttribute('role', 'complementary');
        panel.setAttribute('aria-label', 'Guía de la herramienta');
        panel.setAttribute('aria-hidden', 'true');
        panel.innerHTML =
            '<div class="help-header">' +
              '<div class="help-title-row">' +
                '<svg class="help-icon" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">' +
                  '<circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.4"/>' +
                  '<path d="M7 6.5v3M7 4.5h.01" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>' +
                '</svg>' +
                '<span class="help-title">' + contenido.titulo + '</span>' +
              '</div>' +
              '<button class="help-close-btn" id="help-close" aria-label="Cerrar guía">' +
                '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">' +
                  '<path d="M9 3L3 9M3 3l6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>' +
                '</svg>' +
              '</button>' +
            '</div>' +
            '<ul class="help-list" id="help-list"></ul>' +
            '<div class="help-progress-track"><div class="help-progress-fill" id="help-progress-fill"></div></div>';

        construir_items(panel.querySelector('#help-list'), contenido.puntos);

        /* Build help trigger */
        var trigger = document.createElement('button');
        trigger.className = 'help-trigger';
        trigger.id = 'help-trigger';
        trigger.setAttribute('aria-label', 'Abrir guía de la herramienta');
        trigger.setAttribute('aria-expanded', 'false');
        trigger.innerHTML =
            '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">' +
              '<circle cx="8" cy="8" r="6.5" stroke="currentColor" stroke-width="1.4"/>' +
              '<path d="M8 7.5v3.5M8 5.5h.01" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>' +
            '</svg>';

        /* Wrap chatbot-trigger inside a .trigger-stack */
        var cbTrigger = document.getElementById('chatbot-trigger');
        var stack = document.createElement('div');
        stack.className = 'trigger-stack';
        contenedor.insertBefore(stack, cbTrigger);
        stack.appendChild(cbTrigger);
        stack.appendChild(trigger);

        /* Insert help-panel before chatbot-panel (at top of widget) */
        var cbPanel = document.getElementById('chatbot-panel');
        if (cbPanel) {
            contenedor.insertBefore(panel, cbPanel);
        } else {
            contenedor.insertBefore(panel, contenedor.firstChild);
        }

        estado.panel   = panel;
        estado.trigger = trigger;
        estado.barra   = document.getElementById('help-progress-fill');
        return true;
    }

    function animar_items() {
        var items = estado.panel.querySelectorAll('.help-item');
        items.forEach(function (item, idx) {
            item.classList.remove('help-item--visible');
            void item.offsetWidth;
            item.style.animationDelay = (110 + idx * 55) + 'ms';
            item.classList.add('help-item--visible');
        });
    }

    function iniciar_barra(ms) {
        var b = estado.barra;
        if (!b) return;
        b.style.transition = 'none';
        b.style.width = '100%';
        void b.offsetWidth;
        b.style.transition = 'width ' + ms + 'ms linear';
        b.style.width = '0%';
    }

    function abrir() {
        if (!estado.panel || estado.abierto) return;
        estado.panel.classList.remove('help-panel--closing');
        estado.panel.classList.add('help-panel--open');
        estado.panel.setAttribute('aria-hidden', 'false');
        estado.trigger.setAttribute('aria-expanded', 'true');
        estado.abierto = true;
        animar_items();
        iniciar_barra(4000);
    }

    function cerrar() {
        if (!estado.panel || !estado.abierto) return;
        clearTimeout(estado.timer);
        estado.panel.classList.remove('help-panel--open');
        estado.panel.classList.add('help-panel--closing');
        estado.panel.setAttribute('aria-hidden', 'true');
        estado.trigger.setAttribute('aria-expanded', 'false');
        estado.abierto = false;
        estado.panel.addEventListener('animationend', function once() {
            estado.panel.removeEventListener('animationend', once);
            if (estado.panel) estado.panel.classList.remove('help-panel--closing');
        });
    }

    function actualizar_y_mostrar(contenido) {
        if (!estado.panel) return;
        var titleEl = estado.panel.querySelector('.help-title');
        if (titleEl) titleEl.textContent = contenido.titulo;
        var lista = estado.panel.querySelector('#help-list');
        if (lista) construir_items(lista, contenido.puntos);
        if (estado.abierto) cerrar();
        clearTimeout(estado.timer);
        setTimeout(function () {
            abrir();
            estado.timer = setTimeout(cerrar, 4000);
        }, 350);
    }

    function observar_paneles() {
        var secciones = document.querySelectorAll('.panel-section');
        if (!secciones.length) return;

        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.attributeName === 'class') {
                    var el = mutation.target;
                    if (el.classList.contains('active') && CONTENIDO_PANEL[el.id]) {
                        actualizar_y_mostrar(CONTENIDO_PANEL[el.id]);
                    }
                }
            });
        });

        secciones.forEach(function (s) {
            observer.observe(s, { attributes: true, attributeFilter: ['class'] });
        });
    }

    function inicializar() {
        if (!crear_html(obtener_contenido())) return;

        document.getElementById('help-close').addEventListener('click', cerrar);

        estado.trigger.addEventListener('click', function () {
            if (estado.abierto) {
                cerrar();
            } else {
                abrir();
                estado.timer = setTimeout(cerrar, 4000);
            }
        });

        /* Watch for panel section switches in console.html SPA */
        observar_paneles();

        /* Auto-open on page load */
        setTimeout(function () {
            abrir();
            estado.timer = setTimeout(cerrar, 4000);
        }, 700);
    }

    document.addEventListener('DOMContentLoaded', inicializar);
})();
