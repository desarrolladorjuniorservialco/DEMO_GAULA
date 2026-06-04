import os
import pandas as pd
from flask import jsonify
from modules.dataset import dataset_bp
from modules.auth.decorators import login_required

_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "Data_Set", "nexo147_dataset_relacional_csv")
)
_CSV_CASOS   = os.path.join(_DATA_DIR, "nexo147_casos_demo_500.csv")
_CSV_ALERTAS = os.path.join(_DATA_DIR, "nexo147_alertas_osint_demo.csv")  # used in api_intel_dashboard (Task 3)


@dataset_bp.route("/api/dataset/casos")
@login_required
def api_dataset_casos():
    df = pd.read_csv(_CSV_CASOS, dtype=str).fillna("")
    df = df.rename(columns={
        "unidad_gaula_receptora":         "unidad_gaula",
        "estado_caso":                    "estado",
        "numero_telefonico_asociado":     "numero_extorsivo",
        "monto_exigido_perdida_estimada": "valor_exigido",
        "medio_cuenta_pago":              "medio_pago",
        "descripcion_hechos":             "descripcion",
    })
    cols = [
        "id_reporte", "fecha_registro", "tipo_reporte", "prioridad",
        "unidad_gaula", "estado", "nombre_reportante", "alias_sospechoso",
        "numero_extorsivo", "valor_exigido", "medio_pago", "descripcion",
        "departamento", "municipio", "score_riesgo", "modalidad", "posible_grupo",
    ]
    return jsonify(df[cols].to_dict(orient="records"))
