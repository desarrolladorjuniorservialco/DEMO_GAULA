from flask import Blueprint

opendata_bp = Blueprint("opendata_osint", __name__)

from modules.osint.opendata import routes  # noqa: E402, F401
