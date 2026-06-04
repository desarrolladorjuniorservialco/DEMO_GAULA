# modules/dashboard/__init__.py
from flask import Blueprint

dashboard_bp = Blueprint("dashboard", __name__)

from modules.dashboard import routes  # noqa: F401, E402
