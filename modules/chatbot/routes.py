from flask import request, jsonify
from modules.chatbot import chatbot_bp

_RESPUESTAS = [
    {
        "patrones": ["reporte", "formulario", "147", "registrar", "nuevo caso", "linea"],
        "respuesta": (
            "Para registrar un reporte en la Línea 147, accede al módulo 'Formulario 147' "
            "desde el menú. Completa los campos requeridos: tipo de incidente, datos del "
            "afectado y descripción del hecho. El sistema asigna un ID de radicado al guardar."
        ),
    },
    {
        "patrones": ["estado", "seguimiento", "trazabilidad", "consultar caso", "ver reporte", "radicado"],
        "respuesta": (
            "Consulta el estado de un reporte desde el módulo 'Trazabilidad'. "
            "Ingresa el número de radicado para ver el historial completo de acciones "
            "y el estado operativo actual del caso."
        ),
    },
    {
        "patrones": ["dashboard", "panel de control", "estadisticas", "metricas", "resumen operativo"],
        "respuesta": (
            "El Dashboard principal muestra indicadores operacionales en tiempo real: "
            "total de reportes activos, distribución por tipo de incidente y flujo de estados. "
            "Disponible para perfiles con rol Admin o Director."
        ),
    },
    {
        "patrones": ["osint", "inteligencia abierta", "busqueda osint", "fuentes abiertas", "investigacion"],
        "respuesta": (
            "El módulo OSINT permite búsquedas de inteligencia en fuentes abiertas. "
            "Accede desde 'Dashboard OSINT' para el resumen de operaciones, o desde "
            "'Búsqueda OSINT' para iniciar una nueva consulta. El historial queda registrado para auditoría."
        ),
    },
    {
        "patrones": ["brecha", "seguridad", "vulnerabilidad", "verificacion", "credenciales comprometidas"],
        "respuesta": (
            "El módulo de Verificación de Brechas de Seguridad consulta bases de datos "
            "externas para identificar compromisos de credenciales. "
            "Disponible solo para perfiles Admin desde el menú de navegación."
        ),
    },
    {
        "patrones": ["usuario", "contrasena", "sesion", "login", "acceso", "cuenta", "clave"],
        "respuesta": (
            "Para problemas de acceso, contacta al administrador del sistema NEXO-147. "
            "Las credenciales son asignadas por rol: Operador, Analista, Director o Admin. "
            "No compartas tus credenciales institucionales."
        ),
    },
    {
        "patrones": ["caso", "incidente", "expediente", "casos activos"],
        "respuesta": (
            "Los casos activos están disponibles en el módulo 'Casos'. "
            "Desde allí puedes ver el listado completo con filtros por estado, "
            "fecha y unidad GAULA responsable."
        ),
    },
    {
        "patrones": ["watchlist", "vigilancia", "monitoreo", "alerta", "lista de vigilancia"],
        "respuesta": (
            "Las Watchlists OSINT permiten registrar objetivos bajo monitoreo continuo. "
            "Accede desde 'Historial OSINT' y selecciona la pestaña de listas de vigilancia "
            "para gestionar los elementos monitoreados."
        ),
    },
    {
        "patrones": ["gaula", "unidad", "bogota", "medellin", "cali", "barranquilla"],
        "respuesta": (
            "NEXO-147 opera con unidades GAULA en Bogotá D.C., Medellín, Cali, "
            "Barranquilla y Bucaramanga. La asignación de casos a unidades se gestiona "
            "desde el Dashboard Admin según la jurisdicción del incidente."
        ),
    },
    {
        "patrones": ["ayuda", "help", "soporte", "manual", "instrucciones", "que puedes hacer"],
        "respuesta": (
            "Soy el asistente operativo NEXO-147. Puedo orientarte sobre: "
            "registro de reportes Línea 147, consulta de estados, módulos OSINT, "
            "gestión de casos, watchlists, brechas de seguridad y acceso al sistema. "
            "Escribe tu consulta o selecciona una sugerencia."
        ),
    },
]

_RESPUESTA_DEFAULT = (
    "No encontré información específica para esa consulta. "
    "Puedo orientarte sobre: registro de reportes (Línea 147), módulos OSINT, "
    "consulta de estados o gestión de usuarios. ¿Qué necesitas?"
)


def _normalizar(texto: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFD", texto.lower()).encode("ascii", "ignore").decode("ascii")


@chatbot_bp.route("/api/chatbot", methods=["POST"])
def api_chatbot():
    datos = request.get_json(silent=True) or {}
    pregunta = str(datos.get("pregunta", "")).strip()

    if not pregunta:
        return jsonify({"respuesta": "Escribe una pregunta para consultar."}), 400

    texto = _normalizar(pregunta)
    for item in _RESPUESTAS:
        if any(_normalizar(p) in texto for p in item["patrones"]):
            return jsonify({"respuesta": item["respuesta"]})

    return jsonify({"respuesta": _RESPUESTA_DEFAULT})
