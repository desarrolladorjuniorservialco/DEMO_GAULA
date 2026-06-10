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
        data={"rows": [{"nombre": "JUAN", "placa": "ABC123", "valor_a_pagar": "100000",
                        "estado": "PENDIENTE", "fecha_infraccion": "2024-01-01",
                        "municipio": "BOGOTA", "numero_identificacion": "12345678"}]},
        errors=[], metadata={"latency_ms": 50, "count": 1},
    )
    tc_result = ConnectorResult(
        connector="truecaller", ok=False, data={}, errors=[],
        metadata={"status": "unconfigured"},
    )
    with patch("modules.osint.opendata.routes._run_connectors",
               return_value={"simit": simit_result, "truecaller": tc_result}):
        client = _auth_client(app)
        resp = client.get("/osint/opendata/lookup?q=12345678")

    assert resp.status_code == 200
    assert b"JUAN" in resp.data


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


def test_opendata_detect_type_unknown():
    from modules.osint.opendata.routes import _detect_type
    assert _detect_type("JUAN CARLOS PEREZ") == "unknown"
