from flask import Blueprint

history_osint_bp = Blueprint("history_osint", __name__)

from modules.osint.history import routes  # noqa: E402,F401
