function guardar_reporte_json() {
    const btn_guardar_reporte = document.getElementById("guardar_reporte");

    if (!btn_guardar_reporte) {
        return;
    }

    btn_guardar_reporte.onclick = async (e) => {
        e.preventDefault();

        const formulario = document.getElementById("formulario-inicial");
        const feedback = document.getElementById("feedback-reporte");

        if (!formulario) {
            if (feedback) {
                feedback.textContent = "Error: Formulario no encontrado.";
                feedback.className = "alert error";
                feedback.style.display = "";
            }
            return;
        }

        const form_data = new FormData(formulario);
        const datos = {};

        form_data.forEach((valor, clave) => {
            if (datos[clave]) {
                if (!Array.isArray(datos[clave])) {
                    datos[clave] = [datos[clave]];
                }
                datos[clave].push(valor);
            } else {
                datos[clave] = valor;
            }
        });

        try {
            const response = await fetch("/registrar-reporte", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(datos)
            });

            const resultado = await response.json();

            if (!response.ok) {
                throw new Error(resultado.error || `Error HTTP: ${response.status}`);
            }

            if (feedback) {
                feedback.textContent = resultado.mensaje || "Reporte guardado correctamente.";
                feedback.className = "alert ok";
                feedback.style.display = "";
            }

            formulario.reset();

            setTimeout(() => {
                window.location.href = "/#chatbot-estados";
            }, 1200);

        } catch (error) {
            if (feedback) {
                feedback.textContent = "Error al guardar el formulario. Verifique la información e intente de nuevo.";
                feedback.className = "alert error";
                feedback.style.display = "";
            }

            console.error("Error guardando reporte:", error);
        }
    };
}


function iniciar_chatbot_estados() {
    const input_chatbot = document.getElementById("chatbot-pregunta");
    const btn_chatbot = document.getElementById("chatbot-enviar");
    const contenedor_mensajes = document.getElementById("chatbot-mensajes");
    const botones_sugerencia = document.querySelectorAll(".chat-suggestion");

    if (!input_chatbot || !btn_chatbot || !contenedor_mensajes) {
        return;
    }

    function agregar_mensaje(texto, tipo) {
        const mensaje = document.createElement("div");

        if (tipo === "user") {
            mensaje.className = "user-message";
        } else {
            mensaje.className = "bot-message";
        }

        mensaje.textContent = texto;
        contenedor_mensajes.appendChild(mensaje);
        contenedor_mensajes.scrollTop = contenedor_mensajes.scrollHeight;
    }

    async function enviar_pregunta() {
        const pregunta = input_chatbot.value.trim();

        if (!pregunta) {
            agregar_mensaje("Escribe una pregunta para consultar.", "bot");
            return;
        }

        agregar_mensaje(pregunta, "user");
        input_chatbot.value = "";

        try {
            const response = await fetch("/api/chatbot", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    pregunta: pregunta
                })
            });

            const data = await response.json();

            if (!response.ok) {
                agregar_mensaje(data.respuesta || "No fue posible procesar la consulta.", "bot");
                return;
            }

            agregar_mensaje(data.respuesta || "No encontré información para esa consulta.", "bot");

        } catch (error) {
            agregar_mensaje("Error de conexión con el chatbot.", "bot");
            console.error("Error en chatbot:", error);
        }
    }

    btn_chatbot.onclick = enviar_pregunta;

    input_chatbot.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            enviar_pregunta();
        }
    });

    botones_sugerencia.forEach((boton) => {
        boton.addEventListener("click", function () {
            const pregunta = boton.getAttribute("data-question");

            if (pregunta) {
                input_chatbot.value = pregunta;
                enviar_pregunta();
            }
        });
    });
}


document.addEventListener("DOMContentLoaded", function () {
    guardar_reporte_json();
    iniciar_chatbot_estados();
});