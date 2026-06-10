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


import os
from unittest.mock import patch as _patch2, MagicMock as _MagicMock2
from modules.osint.connectors.phone import PhoneConnector


def test_phone_connector_name():
    c = PhoneConnector()
    assert c.name == "phone"


def test_phone_supported_types():
    c = PhoneConnector()
    assert "phone" in c.supported_target_types


def test_phone_fetch_local_carrier():
    c = PhoneConnector()
    with _patch2("modules.osint.connectors.phone.os.getenv", return_value=""):
        with _patch2("duckduckgo_search.DDGS") as mock_ddgs:
            mock_ddgs.return_value.__enter__.return_value.text.return_value = []
            result = c.fetch("+573151234567")

    assert result.ok is True
    assert result.connector == "phone"
    assert result.data["country"] == "Colombia"


def test_phone_fetch_numverify_enrichment():
    c = PhoneConnector()
    mock_nv = {
        "valid": True,
        "carrier": "CLARO",
        "line_type": "mobile",
        "country_name": "Colombia",
        "location": "Bogota",
        "international_format": "+57 315 123 4567",
    }
    with _patch2("modules.osint.connectors.phone.requests.get") as mock_get:
        mock_get.return_value = _MagicMock2(status_code=200, json=lambda: mock_nv)
        mock_get.return_value.raise_for_status = lambda: None
        with _patch2("modules.osint.connectors.phone.os.getenv", return_value="test-key"):
            with _patch2("duckduckgo_search.DDGS") as mock_ddgs:
                mock_ddgs.return_value.__enter__.return_value.text.return_value = []
                result = c.fetch("+573151234567")

    assert result.ok is True
    assert result.data["carrier"] == "CLARO"
    assert result.metadata["enriched"] is True


def test_phone_fetch_no_numverify_key():
    c = PhoneConnector()
    with _patch2("modules.osint.connectors.phone.os.getenv", return_value=""):
        with _patch2("duckduckgo_search.DDGS") as mock_ddgs:
            mock_ddgs.return_value.__enter__.return_value.text.return_value = []
            result = c.fetch("+573001234567")

    assert result.ok is True
    assert result.metadata["enriched"] is False


from modules.osint.connectors import web_dork


def test_web_dork_dedups_by_url():
    rows = [
        {"href": "https://a.com", "title": "A", "body": "ba"},
        {"href": "https://a.com", "title": "A dup", "body": "dup"},
        {"href": "https://b.com", "title": "B", "body": "bb"},
    ]
    with patch("modules.osint.connectors.web_dork.DDGS") as mock_ddgs:
        mock_ddgs.return_value.__enter__.return_value.text.return_value = rows
        results, errors = web_dork.run_dork(['"123"'], max_results=10, sleep_between=0)

    urls = [r["url"] for r in results]
    assert urls == ["https://a.com", "https://b.com"]
    assert errors == []


def test_web_dork_handles_ratelimit():
    from duckduckgo_search.exceptions import DuckDuckGoSearchException
    with patch("modules.osint.connectors.web_dork.DDGS") as mock_ddgs:
        inst = mock_ddgs.return_value.__enter__.return_value
        inst.text.side_effect = DuckDuckGoSearchException("ratelimit")
        results, errors = web_dork.run_dork(['"x"'], max_results=5, sleep_between=0)

    assert results == []
    assert len(errors) == 1
