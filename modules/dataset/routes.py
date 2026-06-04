import os
import pandas as pd
from flask import jsonify
from modules.dataset import dataset_bp
from modules.auth.decorators import login_required

_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "Data_Set", "nexo147_dataset_relacional_csv")
)
_CSV_CASOS   = os.path.join(_DATA_DIR, "nexo147_casos_demo_500.csv")
_CSV_ALERTAS = os.path.join(_DATA_DIR, "nexo147_alertas_osint_demo.csv")


@dataset_bp.route("/api/dataset/casos")
@login_required
def api_dataset_casos():
    df = pd.read_csv(_CSV_CASOS, dtype=str).fillna("")
    resultados = []
    for _, row in df.iterrows():
        resultados.append({
            "id_reporte":        row["id_reporte"],
            "fecha_registro":    row["fecha_registro"],
            "tipo_reporte":      row["tipo_reporte"],
            "prioridad":         row["prioridad"],
            "unidad_gaula":      row["unidad_gaula_receptora"],
            "estado":            row["estado_caso"],
            "nombre_reportante": row["nombre_reportante"],
            "alias_sospechoso":  row["alias_sospechoso"],
            "numero_extorsivo":  row["numero_telefonico_asociado"],
            "valor_exigido":     row["monto_exigido_perdida_estimada"],
            "medio_pago":        row["medio_cuenta_pago"],
            "descripcion":       row["descripcion_hechos"],
            "departamento":      row["departamento"],
            "municipio":         row["municipio"],
            "score_riesgo":      row["score_riesgo"],
            "modalidad":         row["modalidad"],
            "posible_grupo":     row["posible_grupo"],
        })
    return jsonify(resultados)
