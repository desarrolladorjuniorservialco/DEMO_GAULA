# tests/test_nexo147_models.py
import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from models.nexo147 import Usuario, UnidadGaula, Caso, Reportante, CasoReportante, Evidencia, EventoCaso, MedioPago


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
    uid = str(uuid.uuid4())
    session.add(Caso(id_caso=uid, estado="Recibido", created_by="test"))
    session.commit()
    session.add(Caso(id_caso=uid, estado="Recibido", created_by="test"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_reportante_y_junction(session):
    caso = Caso(id_caso=str(uuid.uuid4()), estado="Recibido", created_by="test")
    rep  = Reportante(nombre="Juan Perez", documento="123456", telefono="3001234567")
    session.add_all([caso, rep])
    session.flush()

    jr = CasoReportante(
        caso_id=caso.id,
        reportante_id=rep.id,
        rol_en_caso="denunciante",
        created_by="test",
    )
    session.add(jr)
    session.commit()

    assert len(caso.reportantes) == 1
    assert caso.reportantes[0].reportante.nombre == "Juan Perez"


def test_reportante_anonimo_por_defecto(session):
    r = Reportante()
    session.add(r)
    session.commit()
    assert r.anonimo is False


def test_evidencia(session):
    caso = Caso(id_caso=str(uuid.uuid4()), estado="Recibido", created_by="test")
    session.add(caso)
    session.flush()
    e = Evidencia(caso_id=caso.id, tipo="audio", descripcion="Llamada grabada", created_by="test")
    session.add(e)
    session.commit()
    assert e.id is not None
    assert caso.evidencias[0].tipo == "audio"


def test_evento_caso(session):
    caso = Caso(id_caso=str(uuid.uuid4()), estado="Recibido", created_by="test")
    session.add(caso)
    session.flush()
    ev = EventoCaso(
        caso_id=caso.id,
        tipo_evento="creacion",
        descripcion="Caso registrado.",
        estado_nuevo="Recibido",
        created_by="operador1",
    )
    session.add(ev)
    session.commit()
    assert ev.id is not None
    assert ev.estado_anterior is None


def test_medio_pago(session):
    caso = Caso(id_caso=str(uuid.uuid4()), estado="Recibido", created_by="test")
    session.add(caso)
    session.flush()
    mp = MedioPago(caso_id=caso.id, tipo="nequi", valor_exigido=500000, moneda="COP", created_by="test")
    session.add(mp)
    session.commit()
    assert float(mp.valor_exigido) == 500000.0
