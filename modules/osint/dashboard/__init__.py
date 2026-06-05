from flask import Blueprint

dashboard_osint_bp = Blueprint("osint_dashboard", __name__)

from modules.osint.dashboard import routes  # noqa: E402,F401
