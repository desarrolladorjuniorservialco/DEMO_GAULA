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


def test_simit_fetch_plate_ok():
    c = SimitConnector()
    mock_rows = [{
        "vigencia": "2019", "placa": "MIK715", "fecha_multa": "25/01/2019",
        "valor_multa": "414058", "departamento": "Santander",
        "ciudad": "Bucaramanga", "pagado_si_no": "SI",
    }]
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_rows)
        mock_get.return_value.raise_for_status = lambda: None
        result = c.fetch("MIK715", target_type="plate")

    assert result.ok is True
    assert result.connector == "simit"
    row = result.data["rows"][0]
    assert row["placa"] == "MIK715"
    assert row["valor"] == "414058"
    assert row["lugar"] == "Bucaramanga, Santander"
    assert row["estado"] == "Pagada"
    assert result.metadata["dataset"] == "72nf-y4v3"


def test_simit_fetch_document_uses_comparendos_dataset():
    c = SimitConnector()
    mock_rows = [{
        "identificacion": "12345678", "placa": "ABC123",
        "fecha": "2020-03-10", "infraccion": "C29", "valor": "390000",
    }]
    captured = {}
    def _fake_get(url, **kwargs):
        captured["url"] = url
        captured["where"] = kwargs["params"]["$where"]
        m = MagicMock(status_code=200, json=lambda: mock_rows)
        m.raise_for_status = lambda: None
        return m
    with patch("modules.osint.connectors.simit.requests.get", side_effect=_fake_get):
        result = c.fetch("12345678", target_type="document")

    assert "rfag-apa4" in captured["url"]
    assert "identificacion='12345678'" in captured["where"]
    assert result.ok is True
    assert result.data["rows"][0]["identificacion"] == "12345678"


def test_simit_fetch_no_results():
    c = SimitConnector()
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
        mock_get.return_value.raise_for_status = lambda: None
        result = c.fetch("XXX000", target_type="plate")

    assert result.ok is False
    assert result.data["rows"] == []


def test_simit_fetch_network_error():
    import requests as req
    c = SimitConnector()
    with patch("modules.osint.connectors.simit.requests.get") as mock_get:
        mock_get.side_effect = req.RequestException("timeout")
        result = c.fetch("MIK715", target_type="plate")

    assert result.ok is False
    assert len(result.errors) == 1
    assert "timeout" in result.errors[0]


def test_simit_build_where_sanitizes_quotes():
    c = SimitConnector()
    where = c._build_where("AB'C12", "plate")
    assert "''" in where


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
        with _patch2("modules.osint.connectors.web_dork.DDGS") as mock_ddgs:
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
            with _patch2("modules.osint.connectors.web_dork.DDGS") as mock_ddgs:
                mock_ddgs.return_value.__enter__.return_value.text.return_value = []
                result = c.fetch("+573151234567")

    assert result.ok is True
    assert result.data["carrier"] == "CLARO"
    assert result.metadata["enriched"] is True


def test_phone_fetch_no_numverify_key():
    c = PhoneConnector()
    with _patch2("modules.osint.connectors.phone.os.getenv", return_value=""):
        with _patch2("modules.osint.connectors.web_dork.DDGS") as mock_ddgs:
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


from modules.osint.connectors.rues import RuesConnector


def test_rues_connector_name_and_types():
    c = RuesConnector()
    assert c.name == "rues"
    assert "document" in c.supported_target_types
    assert "name" in c.supported_target_types
    assert c.needs_api_key is False


def test_rues_fetch_ok():
    c = RuesConnector()
    payload = {"registros": [{
        "razon_social": "COMERCIALIZADORA XYZ SAS",
        "matricula": "0001234",
        "estado_matricula": "ACTIVA",
        "camara_comercio": "BOGOTA",
        "nit": "900123456",
    }]}
    with patch("modules.osint.connectors.rues.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: payload)
        mock_get.return_value.raise_for_status = lambda: None
        result = c.fetch("900123456", target_type="document")

    assert result.ok is True
    assert result.connector == "rues"
    exp = result.data["expedientes"][0]
    assert exp["razon_social"] == "COMERCIALIZADORA XYZ SAS"
    assert exp["estado"] == "ACTIVA"


def test_rues_fetch_no_results():
    c = RuesConnector()
    with patch("modules.osint.connectors.rues.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"registros": []})
        mock_get.return_value.raise_for_status = lambda: None
        result = c.fetch("000", target_type="document")

    assert result.ok is False
    assert result.data["expedientes"] == []


def test_rues_fetch_non_json_fails_gracefully():
    c = RuesConnector()
    def _raise_json():
        raise ValueError("no json")
    with patch("modules.osint.connectors.rues.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=_raise_json)
        mock_get.return_value.raise_for_status = lambda: None
        result = c.fetch("900123456", target_type="document")

    assert result.ok is False
    assert len(result.errors) == 1


def test_rues_fetch_socrata_shape_by_cedula():
    """Forma real del dataset c82u-588k: lista, con numero_identificacion
    (cédula) y fecha_cancelacion -> estado derivado."""
    c = RuesConnector()
    rows = [{
        "codigo_camara": "01", "camara_comercio": "ARMENIA", "matricula": "9249",
        "razon_social": "RAMIREZ DE OSPINA MARIA",
        "clase_identificacion": "CEDULA DE CIUDADANIA",
        "numero_identificacion": "24560913", "fecha_cancelacion": "20111229",
    }]
    captured = {}
    def _fake_get(url, **kwargs):
        captured["where"] = kwargs["params"]["$where"]
        m = MagicMock(status_code=200, json=lambda: rows)
        m.raise_for_status = lambda: None
        return m
    with patch("modules.osint.connectors.rues.requests.get", side_effect=_fake_get):
        result = c.fetch("24560913", target_type="document")

    assert "numero_identificacion='24560913'" in captured["where"]
    assert result.ok is True
    exp = result.data["expedientes"][0]
    assert exp["razon_social"] == "RAMIREZ DE OSPINA MARIA"
    assert exp["camara"] == "ARMENIA"
    assert exp["nit"] == "24560913"
    assert exp["estado"] == "CANCELADA"
