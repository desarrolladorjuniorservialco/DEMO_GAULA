# modules/casos/routes.py
from flask import request, redirect, url_for, flash, session, jsonify
from modules.casos import casos_bp
from modules.auth.decorators import login_required
from modules.extensions import db
from models.nexo147 import Caso, Reportante, CasoReportante, Evidencia, EventoCaso, MedioPago, UnidadGaula
import uuid


@casos_bp.route("/registrar-reporte", methods=["POST"])
@login_required
def registrar_reporte():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    tipo_caso   = data.get("tipo_reporte", "").strip()
    prioridad   = data.get("prioridad", "").strip()
    descripcion = data.get("descripcion", "").strip()

    if not tipo_caso or not prioridad or not descripcion:
        if request.is_json:
            return {"error": "Debe registrar tipo de reporte, prioridad y descripcion minima."}, 400
        flash("Debe registrar tipo de reporte, prioridad y descripcion minima.", "error")
        return redirect(url_for("auth.home") + "#reporte")

    nombre_unidad = data.get("unidad_gaula", "").strip()
    unidad = None
    if nombre_unidad:
        unidad = UnidadGaula.query.filter_by(nombre=nombre_unidad).first()
        if not unidad:
            unidad = UnidadGaula(nombre=nombre_unidad, created_by=session.get("user"))
            db.session.add(unidad)
            db.session.flush()

    caso = Caso(
        id_caso         = str(uuid.uuid4()),
        estado          = "Recibido",
        prioridad       = prioridad,
        tipo_caso       = tipo_caso,
        canal_recepcion = data.get("canal_recepcion", "").strip(),
        unidad_gaula_id = unidad.id if unidad else None,
        descripcion     = descripcion,
        observaciones   = data.get("observaciones", "").strip(),
        created_by      = session.get("user"),
    )
    db.session.add(caso)
    db.session.flush()

    nombre_rep = data.get("nombre_reportante", "").strip()
    if nombre_rep or data.get("documento_reportante") or data.get("telefono_reportante"):
        rep = Reportante(
            nombre     = nombre_rep,
            documento  = data.get("documento_reportante", "").strip(),
            telefono   = data.get("telefono_reportante", "").strip(),
            anonimo    = not bool(nombre_rep),
            created_by = session.get("user"),
        )
        db.session.add(rep)
        db.session.flush()
        db.session.add(CasoReportante(
            caso_id       = caso.id,
            reportante_id = rep.id,
            rol_en_caso   = "denunciante",
            created_by    = session.get("user"),
        ))

    medio = data.get("medio_pago", "").strip()
    if medio:
        raw = data.get("valor_exigido", "0").strip().replace(",", "").replace("$", "") or "0"
        try:
            valor_decimal = float(raw)
        except ValueError:
            valor_decimal = 0.0
        db.session.add(MedioPago(
            caso_id       = caso.id,
            tipo          = medio,
            valor_exigido = valor_decimal,
            referencia    = data.get("numero_extorsivo", "").strip(),
            created_by    = session.get("user"),
        ))

    evidencia_txt = data.get("evidencia", "").strip()
    if evidencia_txt:
        db.session.add(Evidencia(
            caso_id     = caso.id,
            tipo        = "referencia",
            descripcion = evidencia_txt,
            created_by  = session.get("user"),
        ))

    db.session.add(EventoCaso(
        caso_id      = caso.id,
        tipo_evento  = "creacion",
        descripcion  = "Caso registrado desde formulario.",
        estado_nuevo = "Recibido",
        created_by   = session.get("user"),
    ))

    db.session.commit()

    if request.is_json:
        return {"mensaje": f"Reporte registrado. Codigo: {caso.id_caso}", "id_reporte": caso.id_caso}, 201
    flash(f"Reporte registrado correctamente. Codigo interno: {caso.id_caso}", "ok")
    return redirect(url_for("auth.home") + "#reporte")


@casos_bp.route("/api/casos", methods=["GET"])
@login_required
def api_casos():
    role = session.get("role")
    username = session.get("user")
    if role == "operador":
        casos = Caso.query.filter_by(created_by=username).order_by(Caso.fecha_registro.desc()).all()
    else:
        casos = Caso.query.order_by(Caso.fecha_registro.desc()).all()

    resultados = []
    for c in casos:
        unidad_nombre = c.unidad_gaula.nombre if c.unidad_gaula else ""
        medio = c.medios_pago[0] if c.medios_pago else None
        rep_link = c.reportantes[0] if c.reportantes else None
        rep = rep_link.reportante if rep_link else None
        resultados.append({
            "id_reporte":           c.id_caso,
            "fecha_registro":       c.fecha_registro.strftime('%Y-%m-%d %H:%M') if c.fecha_registro else "",
            "estado":               c.estado,
            "usuario_registro":     c.created_by,
            "tipo_reporte":         c.tipo_caso,
            "prioridad":            c.prioridad,
            "unidad_gaula":         unidad_nombre,
            "canal_recepcion":      c.canal_recepcion,
            "nombre_reportante":    rep.nombre if rep else "",
            "documento_reportante": rep.documento if rep else "",
            "telefono_reportante":  rep.telefono if rep else "",
            "descripcion":          c.descripcion,
            "medio_pago":           medio.tipo if medio else "",
            "valor_exigido":        str(medio.valor_exigido) if medio else "",
            "observaciones":        c.observaciones,
        })
    return jsonify(resultados)


@casos_bp.route("/api/casos/<id_reporte>/estado", methods=["POST"])
@login_required
def api_actualizar_estado(id_reporte):
    role = session.get("role")
    if role not in ["admin", "analista", "director"]:
        return jsonify({"error": "No autorizado para cambiar el estado del caso."}), 403

    data = request.get_json() or {}
    nuevo_estado = data.get("estado", "").strip()
    if not nuevo_estado:
        return jsonify({"error": "Debe proporcionar un estado valido."}), 400

    caso = Caso.query.filter_by(id_caso=id_reporte).first()
    if not caso:
        return jsonify({"error": "Caso no encontrado."}), 404

    caso.estado = nuevo_estado
    db.session.commit()
    return jsonify({"mensaje": f"Estado actualizado a: {nuevo_estado}", "id_reporte": id_reporte})
