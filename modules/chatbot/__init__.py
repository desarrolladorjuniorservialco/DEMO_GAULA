from flask import Blueprint

chatbot_bp = Blueprint("chatbot", __name__)

from modules.chatbot import routes  # noqa: F401, E402
