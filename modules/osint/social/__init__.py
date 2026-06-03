from flask import Blueprint

social_osint_bp = Blueprint("social_osint", __name__)

from modules.osint.social import routes  # noqa: E402, F401
