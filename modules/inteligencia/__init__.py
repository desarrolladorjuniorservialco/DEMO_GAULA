# modules/inteligencia/__init__.py
from flask import Blueprint

intel_bp = Blueprint("intel", __name__)

from modules.inteligencia import routes  # noqa: F401, E402
