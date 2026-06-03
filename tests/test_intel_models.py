# tests/test_intel_models.py
import pytest
from sqlalchemy.exc import IntegrityError
from models.intel import (
    Persona, Alias, Telefono, Correo, Direccion,
    Ubicacion, Vehiculo, CuentaBancaria, RedSocial, Organizacion,
)


def test_persona_creacion(session):
    p = Persona(
        nombres="Carlos", apellidos="Ramirez", documento="987654",
        tipo_documento="CC", nivel_riesgo="alto", es_objetivo=True,
        created_by="analista",
    )
    session.add(p)
    session.commit()
    assert p.id is not None
    assert p.es_objetivo is True


def test_alias_creacion(session):
    a = Alias(valor="El Tigre", contexto="calle", created_by="analista")
    session.add(a)
    session.commit()
    assert a.id is not None


def test_telefono_unico(session):
    t1 = Telefono(numero="3001234567", operador="Claro", tipo="celular")
    session.add(t1)
    session.commit()
    t2 = Telefono(numero="3001234567")
    session.add(t2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_correo_creacion(session):
    c = Correo(direccion="test@gmail.com", dominio="gmail.com", proveedor="Gmail")
    session.add(c)
    session.commit()
    assert c.id is not None


def test_vehiculo_creacion(session):
    v = Vehiculo(placa="ABC123", tipo="auto", marca="Toyota", color="Negro")
    session.add(v)
    session.commit()
    assert v.id is not None


def test_cuenta_bancaria_creacion(session):
    cb = CuentaBancaria(numero="4500123456", tipo="ahorros", entidad="Bancolombia")
    session.add(cb)
    session.commit()
    assert cb.id is not None


def test_organizacion_creacion(session):
    org = Organizacion(nombre="Los Urabenios", tipo="grupo armado", activa=True)
    session.add(org)
    session.commit()
    assert org.id is not None
