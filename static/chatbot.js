/* Asistente Operativo NEXO-147 — Widget flotante con respuestas predeterminadas */
(function () {
    'use strict';

    var RESPUESTAS = [
        {
            patrones: ['reporte', 'formulario', '147', 'registrar', 'nuevo caso', 'linea'],
            respuesta: 'Para registrar un reporte en la Línea 147, accede al módulo "Formulario 147" desde el menú. Completa los campos requeridos: tipo de incidente, datos del afectado y descripción del hecho. El sistema asigna un ID de radicado al guardar.'
        },
        {
            patrones: ['estado', 'seguimiento', 'trazabilidad', 'consultar caso', 'radicado'],
            respuesta: 'Consulta el estado de un reporte desde el módulo "Trazabilidad". Ingresa el número de radicado para ver el historial completo de acciones y el estado operativo actual del caso.'
        },
        {
            patrones: ['dashboard', 'panel de control', 'estadisticas', 'metricas', 'resumen'],
            respuesta: 'El Dashboard principal muestra indicadores operacionales en tiempo real: total de reportes activos, distribución por tipo de incidente y flujo de estados. Disponible para perfiles Admin o Director.'
        },
        {
            patrones: ['osint', 'inteligencia abierta', 'fuentes abiertas', 'investigacion', 'busqueda'],
            respuesta: 'El módulo OSINT permite búsquedas de inteligencia en fuentes abiertas. Accede desde "Dashboard OSINT" para el resumen, o desde "Búsqueda OSINT" para iniciar una nueva consulta. El historial queda registrado para auditoría.'
        },
        {
            patrones: ['brecha', 'seguridad', 'vulnerabilidad', 'verificacion'],
            respuesta: 'El módulo de Verificación de Brechas de Seguridad consulta bases de datos externas para identificar compromisos de credenciales. Disponible solo para perfiles Admin desde el menú de navegación.'
        },
        {
            patrones: ['usuario', 'contrasena', 'sesion', 'login', 'acceso', 'cuenta', 'clave'],
            respuesta: 'Para problemas de acceso, contacta al administrador del sistema NEXO-147. Las credenciales son asignadas por rol: Operador, Analista, Director o Admin. No compartas tus credenciales institucionales.'
        },
        {
            patrones: ['caso', 'incidente', 'expediente'],
            respuesta: 'Los casos activos están disponibles en el módulo "Casos". Desde allí puedes ver el listado completo con filtros por estado, fecha y unidad GAULA responsable.'
        },
        {
            patrones: ['watchlist', 'vigilancia', 'monitoreo', 'alerta'],
            respuesta: 'Las Watchlists OSINT permiten registrar objetivos bajo monitoreo continuo. Accede desde "Historial OSINT" y selecciona la pestaña de listas de vigilancia para gestionar los elementos monitoreados.'
        },
        {
            patrones: ['gaula', 'unidad', 'bogota', 'medellin', 'cali', 'barranquilla'],
            respuesta: 'NEXO-147 opera con unidades GAULA en Bogotá D.C., Medellín, Cali, Barranquilla y Bucaramanga. La asignación de casos se gestiona desde el Dashboard Admin según la jurisdicción del incidente.'
        },
        {
            patrones: ['ayuda', 'help', 'soporte', 'manual', 'que puedes', 'instrucciones'],
            respuesta: 'Soy el asistente operativo NEXO-147. Puedo orientarte sobre: registro de reportes Línea 147, consulta de estados, módulos OSINT, gestión de casos, watchlists, brechas de seguridad y acceso al sistema.'
        }
    ];

    var RESPUESTA_DEFAULT = 'No encontré información específica para esa consulta. Puedo orientarte sobre: registro de reportes (Línea 147), módulos OSINT, consulta de estados o gestión de usuarios. ¿Qué necesitas?';

    function normalizar(texto) {
        return texto.toLowerCase()
            .normalize('NFD')
            .replace(/[̀-ͯ]/g, '');
    }

    function buscar_respuesta(pregunta) {
        var texto = normalizar(pregunta);
        for (var i = 0; i < RESPUESTAS.length; i++) {
            var item = RESPUESTAS[i];
            for (var j = 0; j < item.patrones.length; j++) {
                if (texto.indexOf(normalizar(item.patrones[j])) !== -1) {
                    return item.respuesta;
                }
            }
        }
        return RESPUESTA_DEFAULT;
    }

    function inicializar_widget() {
        var trigger   = document.getElementById('chatbot-trigger');
        var panel     = document.getElementById('chatbot-panel');
        var btnCerrar = document.getElementById('chatbot-close');
        var input     = document.getElementById('chatbot-pregunta');
        var btnEnviar = document.getElementById('chatbot-enviar');
        var mensajes  = document.getElementById('chatbot-mensajes');
        var sugerencias = document.querySelectorAll('.chat-suggestion');

        if (!trigger || !panel || !mensajes) return;

        var abierto = false;

        function getStack() { return document.querySelector('.trigger-stack'); }

        function abrir() {
            panel.classList.remove('chatbot-panel--closing');
            panel.classList.add('chatbot-panel--open');
            panel.setAttribute('aria-hidden', 'false');
            trigger.setAttribute('aria-expanded', 'true');
            var stack = getStack();
            if (stack) stack.classList.add('trigger-stack--displaced');
            if (input) setTimeout(function () { input.focus(); }, 50);
            abierto = true;
        }

        function cerrar() {
            panel.classList.remove('chatbot-panel--open');
            panel.classList.add('chatbot-panel--closing');
            panel.setAttribute('aria-hidden', 'true');
            trigger.setAttribute('aria-expanded', 'false');
            abierto = false;
            panel.addEventListener('animationend', function once() {
                panel.removeEventListener('animationend', once);
                panel.classList.remove('chatbot-panel--closing');
                var stack = getStack();
                if (stack) stack.classList.remove('trigger-stack--displaced');
            });
        }

        trigger.addEventListener('click', function () {
            if (abierto) { cerrar(); } else { abrir(); }
        });

        if (btnCerrar) btnCerrar.addEventListener('click', cerrar);

        function agregar_mensaje(texto, tipo) {
            var msg = document.createElement('div');
            msg.className = tipo === 'user' ? 'cb-msg cb-msg--user' : 'cb-msg cb-msg--bot';
            msg.textContent = texto;
            mensajes.appendChild(msg);
            mensajes.scrollTop = mensajes.scrollHeight;
        }

        function mostrar_typing() {
            var indicator = document.createElement('div');
            indicator.className = 'cb-msg cb-msg--bot cb-msg--typing';
            indicator.id = 'cb-typing';
            indicator.innerHTML = '<span></span><span></span><span></span>';
            mensajes.appendChild(indicator);
            mensajes.scrollTop = mensajes.scrollHeight;
            return indicator;
        }

        function enviar() {
            if (!input) return;
            var pregunta = input.value.trim();
            if (!pregunta) return;
            agregar_mensaje(pregunta, 'user');
            input.value = '';
            var indicator = mostrar_typing();
            var delay = 550 + Math.floor(Math.random() * 350);
            setTimeout(function () {
                if (indicator.parentNode) indicator.parentNode.removeChild(indicator);
                agregar_mensaje(buscar_respuesta(pregunta), 'bot');
            }, delay);
        }

        if (btnEnviar) btnEnviar.addEventListener('click', enviar);

        if (input) {
            input.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') { e.preventDefault(); enviar(); }
            });
        }

        sugerencias.forEach(function (btn) {
            btn.addEventListener('click', function () {
                var pregunta = btn.getAttribute('data-question');
                if (pregunta && input) { input.value = pregunta; enviar(); }
            });
        });
    }

    document.addEventListener('DOMContentLoaded', inicializar_widget);
})();
