from flask import Blueprint

dataset_bp = Blueprint("dataset", __name__)

from modules.dataset import routes  # noqa: F401, E402
