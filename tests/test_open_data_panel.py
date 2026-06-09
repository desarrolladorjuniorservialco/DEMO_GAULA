from modules.osint.open_data.service import OpenDataEngine


def test_open_data_engine_classifies_plate_and_document():
    engine = OpenDataEngine()

    plate = engine.classify("MIK-715")
    document = engine.classify("123456789")

    assert plate["kind"] == "plate"
    assert plate["normalized"] == "MIK715"
    assert document["kind"] == "document"
    assert document["normalized"] == "123456789"


def test_open_data_engine_source_groups_for_official_queries():
    engine = OpenDataEngine()

    plate_sources = engine._source_groups("plate", "official")
    document_sources = engine._source_groups("document", "official")
    simit_sources = engine._source_groups("text", "simit")

    assert "simit_historical" in plate_sources
    assert "datos_gov" in plate_sources
    assert "rnmc_open_data" in document_sources
    assert "datos_gov" in document_sources
    assert "simit_historical" in simit_sources


def test_open_data_lookup_page_loads_with_official_catalog(app):
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["user"] = "analista"
        sess["role"] = "analista"
        sess["name"] = "Analista Test"

    response = client.get("/osint/opendata/lookup?source=official")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Fuentes oficiales disponibles" in body
    assert "Catálogo" in body or "CATALOGO" in body
