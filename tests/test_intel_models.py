# tests/test_intel_models.py
import pytest
from sqlalchemy.exc import IntegrityError
from models.intel import (
    Persona, Alias, Telefono, Correo,
    Ubicacion, Vehiculo, CuentaBancaria, Organizacion,
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


def test_persona_alias(session):
    from models.intel import PersonaAlias
    p = Persona(nombres="Pedro", apellidos="Lopez", created_by="test")
    a = Alias(valor="El Toro", contexto="calle", created_by="test")
    session.add_all([p, a])
    session.flush()
    pa = PersonaAlias(persona_id=p.id, alias_id=a.id, created_by="test")
    session.add(pa)
    session.commit()
    assert pa.persona_id == p.id
    assert pa.alias_id == a.id


def test_persona_telefono(session):
    from models.intel import PersonaTelefono
    p = Persona(nombres="Ana", apellidos="Torres", created_by="test")
    t = Telefono(numero="3109876543", operador="Movistar", created_by="test")
    session.add_all([p, t])
    session.flush()
    pt = PersonaTelefono(persona_id=p.id, telefono_id=t.id,
                         relacion="titular", created_by="test")
    session.add(pt)
    session.commit()
    assert pt.relacion == "titular"


def test_caso_persona_cross_db(session):
    from models.intel import CasoPersona
    p = Persona(nombres="Luis", apellidos="Perez", created_by="test")
    session.add(p)
    session.flush()
    cp = CasoPersona(caso_id=999, persona_id=p.id,
                     rol_en_caso="sospechoso", created_by="test")
    session.add(cp)
    session.commit()
    assert cp.caso_id == 999


def test_intel_node_creacion(session):
    from models.intel import IntelNode
    node = IntelNode(entity_type="persona", entity_id=1,
                     label="Carlos Ramirez", nivel_riesgo="alto",
                     created_by="analista")
    session.add(node)
    session.commit()
    assert node.id is not None


def test_intel_edge_relacion(session):
    from models.intel import IntelNode, IntelEdge
    n1 = IntelNode(entity_type="persona",  entity_id=1, label="Sujeto A")
    n2 = IntelNode(entity_type="telefono", entity_id=5, label="+57 300 123")
    session.add_all([n1, n2])
    session.flush()
    edge = IntelEdge(source_node_id=n1.id, target_node_id=n2.id,
                     tipo_relacion="USA_TELEFONO", confianza=0.9,
                     fuente="caso_42", created_by="analista")
    session.add(edge)
    session.commit()
    assert edge.id is not None
    assert edge.tipo_relacion == "USA_TELEFONO"


def test_intel_node_entity_unico(session):
    from models.intel import IntelNode
    n1 = IntelNode(entity_type="cuenta", entity_id=7, label="Cuenta X")
    n2 = IntelNode(entity_type="cuenta", entity_id=7, label="Cuenta X dup")
    session.add(n1)
    session.commit()
    session.add(n2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_hallazgo_intel(session):
    from models.intel import HallazgoIntel
    h = HallazgoIntel(titulo="Red de extorsion sector norte",
                      nivel_clasificacion="confidencial",
                      caso_referencia_id=10,
                      analista_id=2,
                      estado="borrador",
                      created_by="analista")
    session.add(h)
    session.commit()
    assert h.id is not None
