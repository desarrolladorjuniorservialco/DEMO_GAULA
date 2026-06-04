import os
import pandas as pd
import plotly.express as px
import plotly.offline as po
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
    try:
        df = pd.read_csv(_CSV_CASOS, dtype=str).fillna("")
    except (FileNotFoundError, pd.errors.ParserError, OSError) as exc:
        return jsonify({"error": f"Dataset no disponible: {exc}"}), 503
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


@dataset_bp.route("/api/intel/dashboard")
@login_required
def api_intel_dashboard():
    dark = "plotly_dark"

    try:
        casos_df  = pd.read_csv(_CSV_CASOS,   dtype=str).fillna("")
        alertas_df = pd.read_csv(_CSV_ALERTAS, dtype=str).fillna("")
    except (FileNotFoundError, pd.errors.ParserError, OSError) as exc:
        return jsonify({"error": f"Dataset no disponible: {exc}"}), 503

    # Numeric conversions needed for calculations
    casos_df["monto_exigido_perdida_estimada"] = pd.to_numeric(
        casos_df["monto_exigido_perdida_estimada"], errors="coerce"
    ).fillna(0)
    casos_df["score_riesgo"] = pd.to_numeric(
        casos_df["score_riesgo"], errors="coerce"
    ).fillna(0)

    casos_df["fecha_registro"] = pd.to_datetime(casos_df["fecha_registro"], errors="coerce")
    casos_df["mes_anio"] = casos_df["fecha_registro"].dt.strftime("%Y-%m")
    casos_df = casos_df.sort_values("mes_anio")
    casos_df = casos_df[casos_df["mes_anio"].notna()]

    # KPIs
    total_casos   = int(len(casos_df))
    total_monto   = int(casos_df["monto_exigido_perdida_estimada"].sum())
    _mean_riesgo = casos_df["score_riesgo"].mean()
    avg_riesgo   = float(_mean_riesgo) if not pd.isna(_mean_riesgo) else 0.0
    total_alertas = int(len(alertas_df))

    # G1: Monthly trend
    monthly_types = (
        casos_df.groupby(["mes_anio", "tipo_reporte"], as_index=False)
        .size()
        .rename(columns={"size": "cantidad"})
    )
    fig_line = px.line(monthly_types, x="mes_anio", y="cantidad", color="tipo_reporte",
                       title="Tendencia Mensual de Casos por Tipo de Reporte",
                       labels={"mes_anio": "Mes/Año", "cantidad": "Número de Casos", "tipo_reporte": "Tipo"},
                       markers=True, template=dark)

    # G2: Monthly economic impact
    monthly_monto = casos_df.groupby("mes_anio", as_index=False)["monto_exigido_perdida_estimada"].sum()
    fig_bar_monto = px.bar(monthly_monto, x="mes_anio", y="monto_exigido_perdida_estimada",
                           title="Impacto Económico Mensual Consolidado ($ COP)",
                           labels={"mes_anio": "Mes/Año", "monto_exigido_perdida_estimada": "Monto ($)"},
                           template=dark, color_discrete_sequence=["#38bdf8"])

    # G3: Cases by department
    dept_counts = casos_df["departamento"].value_counts().reset_index()
    dept_counts = dept_counts.rename(columns={"count": "cantidad"})
    fig_bar_dept = px.bar(dept_counts, x="cantidad", y="departamento", orientation="h",
                          title="Volumen de Casos Totales por Departamento",
                          labels={"cantidad": "Número de Casos", "departamento": "Departamento"},
                          template=dark, color="cantidad", color_continuous_scale="Blues")

    # G4: Crime type share (donut)
    tipo_counts = casos_df["tipo_reporte"].value_counts().reset_index()
    tipo_counts = tipo_counts.rename(columns={"count": "cantidad"})
    fig_donut = px.pie(tipo_counts, names="tipo_reporte", values="cantidad", hole=0.4,
                       title="Participación Absoluta por Delito",
                       template=dark, color_discrete_sequence=px.colors.qualitative.Pastel)

    # G5: Channel vs Priority
    canal_prioridad = (
        casos_df.groupby(["canal", "prioridad"], as_index=False)
        .size()
        .rename(columns={"size": "cantidad"})
    )
    fig_canal = px.bar(canal_prioridad, x="canal", y="cantidad", color="prioridad",
                       title="Casos por Canal de Recepción y Nivel de Prioridad",
                       labels={"canal": "Canal de Recepción", "cantidad": "Casos", "prioridad": "Prioridad"},
                       template=dark, barmode="stack",
                       color_discrete_map={"Crítica": "#ef4444", "Alta": "#f97316",
                                           "Media": "#eab308", "Baja": "#22c55e"})

    # G6: OSINT indicators
    ind_counts = alertas_df["indicador"].value_counts().reset_index()
    ind_counts = ind_counts.rename(columns={"count": "cantidad"})
    fig_osint = px.bar(ind_counts, x="indicador", y="cantidad",
                       title="Principales Indicadores de Riesgo OSINT Detectados",
                       labels={"indicador": "Indicador Técnico", "cantidad": "Número de Alertas"},
                       template=dark, color="cantidad", color_continuous_scale="Reds")

    return jsonify({
        "kpis": {
            "total_casos":   total_casos,
            "total_monto":   total_monto,
            "avg_riesgo":    round(avg_riesgo, 1),
            "total_alertas": total_alertas,
        },
        "charts": {
            "line_casos":          po.plot(fig_line,      include_plotlyjs=False, output_type="div"),
            "bar_monto":           po.plot(fig_bar_monto, include_plotlyjs=False, output_type="div"),
            "bar_dept":            po.plot(fig_bar_dept,  include_plotlyjs=False, output_type="div"),
            "donut_tipo":          po.plot(fig_donut,     include_plotlyjs=False, output_type="div"),
            "bar_canal_prioridad": po.plot(fig_canal,     include_plotlyjs=False, output_type="div"),
            "osint_indicador":     po.plot(fig_osint,     include_plotlyjs=False, output_type="div"),
        }
    })
