# modules/auth/__init__.py
from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

from modules.auth import routes  # noqa: F401, E402
