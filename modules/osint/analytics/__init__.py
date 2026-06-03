from flask import Blueprint

analytics_osint_bp = Blueprint("analytics_osint", __name__)

from modules.osint.analytics import routes  # noqa: E402, F401
