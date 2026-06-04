# modules/config.py
import os
from sqlalchemy.pool import StaticPool

_basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_data_dir = "/tmp/data" if os.environ.get("VERCEL") else os.path.join(_basedir, "data")

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "demo-gaula-nexo-147")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(_data_dir, "nexo147.db")
    SQLALCHEMY_BINDS = {
        "intel": "sqlite:///" + os.path.join(_data_dir, "intel.db"),
        "osint": "sqlite:///" + os.path.join(_data_dir, "osint.db"),
    }
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_BINDS = {
        "intel": "sqlite:///:memory:",
        "osint": "sqlite:///:memory:",
    }
    # StaticPool necesario: SQLite :memory: pierde datos cuando cambia la conexión
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
