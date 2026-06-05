from flask import Blueprint

watchlists_osint_bp = Blueprint("watchlists_osint", __name__)

from modules.osint.watchlists import routes  # noqa: E402,F401
