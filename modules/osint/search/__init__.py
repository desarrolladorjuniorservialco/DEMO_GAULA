from flask import Blueprint

search_osint_bp = Blueprint("search_osint", __name__)

from modules.osint.search import routes  # noqa: E402,F401
