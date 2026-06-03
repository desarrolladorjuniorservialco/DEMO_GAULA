import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import nexo
from models import db as _db


@pytest.fixture(scope="function")
def app():
    original_config = nexo.config.copy()
    nexo.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_BINDS": {
            "intel": "sqlite:///:memory:",
            "osint": "sqlite:///:memory:",
        },
    })
    with nexo.app_context():
        _db.create_all()
        yield nexo
        _db.drop_all()
    nexo.config.update(original_config)


@pytest.fixture
def session(app):
    yield _db.session
