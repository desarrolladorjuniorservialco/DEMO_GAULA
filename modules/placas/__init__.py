# modules/placas/__init__.py
from flask import Blueprint

placas_bp = Blueprint("placas", __name__)

from modules.placas import routes  # noqa: F401, E402
