import pytest
from flask import session
from models.osint import FuenteOsint, ConsultaOsint, CacheConsulta
from models import db

def test_api_osint_brechas_permissions(app):
    client = app.test_client()
    
    # 1. Access without login should redirect (302) to login page
    response = client.get("/api/osint/brechas")
    assert response.status_code == 302

    # 2. Access with "operador" role should be forbidden (403)
    with client.session_transaction() as sess:
        sess["user"] = "operador"
        sess["role"] = "operador"
        sess["name"] = "Operador Test"
        
    response = client.get("/api/osint/brechas")
    assert response.status_code == 403

    # 3. Access with "analista" role should be successful (200)
    with client.session_transaction() as sess:
        sess["user"] = "analista"
        sess["role"] = "analista"
        sess["name"] = "Analista Test"
        
    response = client.get("/api/osint/brechas")
    assert response.status_code == 200

def test_api_osint_brechas_caching(app):
    client = app.test_client()
    
    with client.session_transaction() as sess:
        sess["user"] = "analista"
        sess["role"] = "analista"
        sess["name"] = "Analista Test"
        
    # First query - should populate cache
    response1 = client.get("/api/osint/brechas?q=test_query")
    assert response1.status_code == 200
    data1 = response1.get_json()
    assert len(data1) > 0
    
    # Check that cache records are created in memory DB
    fuente = FuenteOsint.query.filter_by(nombre="HaveIBeenPwned").first()
    assert fuente is not None
    
    consulta = ConsultaOsint.query.filter_by(fuente_id=fuente.id, valor_consultado="test_query").first()
    assert consulta is not None
    
    cache = CacheConsulta.query.filter_by(consulta_id=consulta.id).first()
    assert cache is not None
    assert cache.hits == 1
    
    # Second query - should increment cache hits
    response2 = client.get("/api/osint/brechas?q=test_query")
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert data1 == data2
    
    db.session.refresh(cache)
    assert cache.hits == 2
