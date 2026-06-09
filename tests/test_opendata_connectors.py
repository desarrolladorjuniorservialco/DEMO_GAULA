# tests/test_opendata_connectors.py
import pytest
from unittest.mock import patch, MagicMock
from modules.osint.connectors.simit import SimitConnector


def test_simit_connector_name():
    c = SimitConnector()
    assert c.name == "simit"


def test_simit_supported_types():
    c = SimitConnector()
    assert "document" in c.supported_target_types
    assert "plate" in c.supported_target_types
    assert "unknown" in c.supported_target_types


def test_simit_fetch_document_ok():
    c = SimitConnector()
    mock_rows = [
        {
            "nombre": "JUAN PEREZ",
            "numero_identificacion": "12345678",
            "placa": "ABC123",
            "valor_a_pagar": "150000",
            "estado": "PENDIENTE",
            "fecha_infraccion": "2024-01-15",
            "municipio": "BOGOTA",
        }
    ]
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_rows)
        result = c.fetch("12345678", target_type="document")

    assert result.ok is True
    assert result.connector == "simit"
    assert len(result.data["rows"]) == 1
    assert result.data["rows"][0]["nombre"] == "JUAN PEREZ"
    assert result.errors == []


def test_simit_fetch_no_results():
    c = SimitConnector()
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
        result = c.fetch("99999999", target_type="document")

    assert result.ok is False
    assert result.data["rows"] == []


def test_simit_fetch_network_error():
    import requests as req
    c = SimitConnector()
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.side_effect = req.RequestException("timeout")
        result = c.fetch("12345678", target_type="document")

    assert result.ok is False
    assert len(result.errors) == 1
    assert "timeout" in result.errors[0]
