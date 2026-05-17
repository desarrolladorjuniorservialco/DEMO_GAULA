function guardar_reporte_json(){

    const btn_guardar_reporte = document.getElementById("guardar_reporte");
    if(!btn_guardar_reporte){
        console.warn("Botón para guardar formulario no está disponible");
        return;
    }

    btn_guardar_reporte.onclick = async (e) => {
        e.preventDefault();
        const formulario = document.getElementById("formulario-inicial");
        if(!formulario){
            console.error("Formulario no encontrado");
            alert("Error: Formulario no encontrado");
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

            alert(resultado.mensaje || "Informe guardado de manera satisfactoria");
            window.location.href = "/#reporte";

        }catch(error){

            console.error("Error al guardar el formulario", error);

            alert("Error al guardar el formulario, revisa la consola");
        }
    };
}

guardar_reporte_json();