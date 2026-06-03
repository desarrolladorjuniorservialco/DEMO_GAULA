# tests/test_nexo147_models.py
from models.nexo147 import Usuario, UnidadGaula


def test_usuario_creacion(session):
    u = Usuario(
        username="operador1",
        password_hash="hashed",
        nombre="Operador Uno",
        rol="operador",
        created_by="test",
    )
    session.add(u)
    session.commit()
    assert u.id is not None
    assert u.activo is True
    assert u.created_at is not None


def test_usuario_username_unico(session):
    u1 = Usuario(username="dup", password_hash="h", nombre="A", rol="operador")
    u2 = Usuario(username="dup", password_hash="h", nombre="B", rol="operador")
    session.add(u1)
    session.commit()
    session.add(u2)
    import pytest
    with pytest.raises(Exception):
        session.commit()


def test_unidad_gaula_creacion(session):
    ug = UnidadGaula(nombre="GAULA Bogota", ciudad="Bogota", departamento="Cundinamarca")
    session.add(ug)
    session.commit()
    assert ug.id is not None
    assert ug.activa is True


def test_unidad_gaula_nombre_unico(session):
    ug1 = UnidadGaula(nombre="GAULA Cali")
    ug2 = UnidadGaula(nombre="GAULA Cali")
    session.add(ug1)
    session.commit()
    session.add(ug2)
    import pytest
    with pytest.raises(Exception):
        session.commit()
