# tests/test_opendata_routes.py
import pytest
from unittest.mock import patch
from modules.osint.connectors.base import ConnectorResult


def _auth_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analista"
        sess["role"] = "analista"
        sess["name"] = "Analista Test"
    return client


def test_opendata_lookup_no_query(app):
    client = _auth_client(app)
    resp = client.get("/osint/opendata/lookup")
    assert resp.status_code == 200
    assert "No se proporcion" in resp.data.decode("utf-8")


def test_opendata_lookup_redirects_unauthenticated(app):
    client = app.test_client()
    resp = client.get("/osint/opendata/lookup?q=123456")
    assert resp.status_code == 302


def test_opendata_lookup_document(app):
    simit_result = ConnectorResult(
        connector="simit", ok=True,
        data={"rows": [{"placa": "ABC123", "fecha": "2020-03-10", "valor": "390000",
                        "lugar": "Bogota", "estado": "Pendiente", "vigencia": "2020",
                        "identificacion": "12345678"}]},
        errors=[], metadata={"latency_ms": 50, "count": 1, "dataset": "rfag-apa4"},
    )
    rues_result = ConnectorResult(
        connector="rues", ok=True,
        data={"expedientes": [{"razon_social": "XYZ SAS", "matricula": "0001",
                               "estado": "ACTIVA", "camara": "BOGOTA", "nit": "12345678"}]},
        errors=[], metadata={"count": 1},
    )
    ctx = {"simit": simit_result, "rues": rues_result, "phone": None,
           "dork": ([], [])}
    with patch("modules.osint.opendata.routes._gather", return_value=ctx):
        client = _auth_client(app)
        resp = client.get("/osint/opendata/lookup?q=12345678")

    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    assert "ABC123" in body
    assert "XYZ SAS" in body


def test_opendata_detect_type_document():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("12345678") == "document"
    assert _detect_type("1234567") == "document"
    assert _detect_type("123456789012") == "unknown"


def test_opendata_detect_type_plate():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("ABC123") == "plate"
    assert _detect_type("abc123") == "plate"


def test_opendata_detect_type_phone():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("+573001234567") == "phone"
    assert _detect_type("3001234567") == "phone"


def test_opendata_detect_type_name():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("JUAN CARLOS PEREZ") == "name"


def test_opendata_detect_type_unknown():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("???") == "unknown"
