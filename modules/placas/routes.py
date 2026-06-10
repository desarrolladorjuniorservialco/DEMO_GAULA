# modules/placas/routes.py
from flask import jsonify, render_template, request

from modules.auth.decorators import login_required
from modules.placas import engine, placas_bp


@placas_bp.route("/")
@login_required
def index():
    return render_template("placas/index.html")


@placas_bp.route("/analizar", methods=["POST"])
@login_required
def analizar():
    if "imagen" not in request.files:
        return jsonify({"ok": False, "error": "No se envió archivo"}), 400

    archivo = request.files["imagen"]
    if not archivo.mimetype.startswith("image/"):
        return jsonify({"ok": False, "error": "El archivo no es una imagen"}), 400

    resultado = engine.reconocer_placa(archivo.read())
    return jsonify(resultado)
