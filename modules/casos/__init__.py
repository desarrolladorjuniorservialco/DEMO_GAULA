# modules/casos/__init__.py
from flask import Blueprint

casos_bp = Blueprint("casos", __name__)

from modules.casos import routes  # noqa: F401, E402
