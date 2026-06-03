# tests/test_nexo147_models.py
import pytest
from sqlalchemy.exc import IntegrityError
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
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


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
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_caso_creacion(session):
    import uuid
    from models.nexo147 import Caso
    ug = UnidadGaula(nombre="GAULA Medellin")
    session.add(ug)
    session.flush()

    c = Caso(
        id_caso=str(uuid.uuid4()),
        estado="Recibido",
        prioridad="Alta",
        tipo_caso="Extorsion",
        canal_recepcion="Linea 147",
        unidad_gaula_id=ug.id,
        descripcion="Extorsion telefonica.",
        created_by="operador1",
    )
    session.add(c)
    session.commit()
    assert c.id is not None
    assert c.estado == "Recibido"
    assert c.unidad_gaula.nombre == "GAULA Medellin"


def test_caso_id_caso_unico(session):
    import uuid
    import pytest
    from sqlalchemy.exc import IntegrityError
    from models.nexo147 import Caso
    uid = str(uuid.uuid4())
    session.add(Caso(id_caso=uid, estado="Recibido", created_by="test"))
    session.commit()
    session.add(Caso(id_caso=uid, estado="Recibido", created_by="test"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
