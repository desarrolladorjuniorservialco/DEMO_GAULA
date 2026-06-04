# tests/conftest.py
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules import create_app
from modules.config import TestConfig
from modules.extensions import db as _db


@pytest.fixture(scope="function")
def app():
    app = create_app(TestConfig)
    with app.app_context():
        yield app


@pytest.fixture
def session(app):
    yield _db.session


@pytest.fixture
def client(app):
    return app.test_client()
