# tests/test_osint_models.py
import pytest
from sqlalchemy.exc import IntegrityError
from models.osint import (
    FuenteOsint, ConsultaOsint, CacheConsulta,
    ResultadoOsint, IndicadorRiesgo,
)


def test_fuente_osint_creacion(session):
    f = FuenteOsint(nombre="HaveIBeenPwned", tipo="email",
                    url_base="https://haveibeenpwned.com/api/v3",
                    requiere_key=True, activa=True,
                    rate_limit_por_min=10, created_by="admin")
    session.add(f)
    session.commit()
    assert f.id is not None
    assert f.activa is True


def test_consulta_osint_creacion(session):
    f = FuenteOsint(nombre="Shodan", tipo="ip", activa=True)
    session.add(f)
    session.flush()
    c = ConsultaOsint(fuente_id=f.id, tipo_consulta="ip",
                      valor_consultado="8.8.8.8", estado="completada",
                      usuario_id=1, created_by="analista")
    session.add(c)
    session.commit()
    assert c.id is not None
    assert c.estado == "completada"


def test_cache_hash_unico(session):
    f = FuenteOsint(nombre="VirusTotal", tipo="dominio", activa=True)
    session.add(f)
    session.flush()
    c = ConsultaOsint(fuente_id=f.id, tipo_consulta="dominio",
                      valor_consultado="evil.com", estado="completada",
                      usuario_id=1, created_by="analista")
    session.add(c)
    session.flush()
    h = "abc123hash"
    session.add(CacheConsulta(consulta_id=c.id, hash_clave=h,
                              respuesta_raw='{"data":"ok"}', codigo_http=200))
    session.commit()
    session.add(CacheConsulta(consulta_id=c.id, hash_clave=h,
                              respuesta_raw='{"data":"dup"}', codigo_http=200))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_resultado_osint(session):
    f = FuenteOsint(nombre="HIBP2", tipo="email", activa=True)
    session.add(f)
    session.flush()
    c = ConsultaOsint(fuente_id=f.id, tipo_consulta="email",
                      valor_consultado="test@test.com", estado="completada",
                      usuario_id=1, created_by="analista")
    session.add(c)
    session.flush()
    r = ResultadoOsint(consulta_id=c.id, tipo_hallazgo="brecha",
                       titulo="Adobe 2013", relevancia=0.8,
                       verificado=False, created_by="analista")
    session.add(r)
    session.commit()
    assert r.id is not None


def test_indicador_riesgo_creacion(session):
    ir = IndicadorRiesgo(tipo="telefono", valor="3001234567",
                         nivel_riesgo="alto", fuente_origen="caso_007",
                         activo=True, created_by="analista")
    session.add(ir)
    session.commit()
    assert ir.id is not None
    assert ir.activo is True
