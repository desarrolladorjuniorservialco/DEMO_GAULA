function guardar_reporte_json(){

    const btn_guardar_reporte = document.getElementById("guardar_reporte");
    if(!btn_guardar_reporte){
        return;
    }

    btn_guardar_reporte.onclick = async (e) => {
        e.preventDefault();
        const formulario = document.getElementById("formulario-inicial");
        const feedback = document.getElementById("feedback-reporte");

        if(!formulario){
            if(feedback){
                feedback.textContent = "Error: Formulario no encontrado";
                feedback.className = "alert error";
                feedback.style.display = "";
            }
            return;
        }

        const form_data = new FormData(formulario);
        const datos = {};

        form_data.forEach((valor, clave) => {
            if(datos[clave]){
                if(!Array.isArray(datos[clave])){
                    datos[clave] = [datos[clave]];
                }
                datos[clave].push(valor);
            }else{
                datos[clave] = valor;
            }
        });

        try{

            const response = await fetch("/registrar_reporte", {
                method: "POST",
                headers:{
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(datos)
            });

            if(!response.ok){
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const resultado = await response.json();

            if(feedback){
                feedback.textContent = resultado.mensaje || "Informe guardado de manera satisfactoria";
                feedback.className = "alert ok";
                feedback.style.display = "";
            }

            setTimeout(() => {
                window.location.href = "/#reporte";
            }, 1800);

        }catch(error){

            if(feedback){
                feedback.textContent = "Error al guardar el formulario. Verifique su conexión e intente de nuevo.";
                feedback.className = "alert error";
                feedback.style.display = "";
            }
        }
    };
}

guardar_reporte_json();
