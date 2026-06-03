# tests/test_migration.py
import uuid
import pytest
from sqlalchemy import text
from models.nexo147 import Caso, Reportante, CasoReportante, EventoCaso, MedioPago, Evidencia
from models.intel import Telefono, Alias


def _seed_old_reporte(session):
    session.execute(text("DROP TABLE IF EXISTS reportes_backup"))
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS reportes_backup (
            id INTEGER PRIMARY KEY,
            id_reporte TEXT,
            fecha_registro TEXT,
            estado TEXT,
            usuario_registro TEXT,
            tipo_reporte TEXT,
            prioridad TEXT,
            unidad_gaula TEXT,
            canal_recepcion TEXT,
            nombre_reportante TEXT,
            documento_reportante TEXT,
            telefono_reportante TEXT,
            descripcion TEXT,
            numero_extorsivo TEXT,
            alias_sospechoso TEXT,
            medio_pago TEXT,
            valor_exigido TEXT,
            evidencia TEXT,
            observaciones TEXT
        )
    """))
    session.execute(text("""
        INSERT INTO reportes_backup VALUES (
            1, :id_rep, '2026-01-10 10:00:00', 'Recibido', 'operador',
            'Extorsion', 'Alta', 'GAULA Bogota', 'Linea 147',
            'Maria Garcia', '10203040', '3009876543',
            'Extorsionaron a la victima por WhatsApp.',
            '3111111111', 'El Sombra', 'nequi', '2500000',
            'Captura pantalla WhatsApp', 'Sin novedad'
        )
    """), {"id_rep": str(uuid.uuid4())})
    session.commit()


def test_migrar_un_reporte(app, session):
    from scripts.migrate_reportes import migrar_reportes
    _seed_old_reporte(session)
    migrar_reportes(session)

    assert Caso.query.count() == 1
    caso = Caso.query.first()
    assert caso.tipo_caso == "Extorsion"
    assert caso.prioridad == "Alta"

    assert Reportante.query.count() == 1
    assert Reportante.query.first().nombre == "Maria Garcia"

    assert CasoReportante.query.count() == 1
    assert MedioPago.query.count() == 1
    assert float(MedioPago.query.first().valor_exigido) == 2500000.0
    assert Evidencia.query.count() == 1
    assert EventoCaso.query.count() == 1
    assert EventoCaso.query.first().tipo_evento == "migracion"


def test_migrar_idempotente(app, session):
    from scripts.migrate_reportes import migrar_reportes
    _seed_old_reporte(session)
    migrar_reportes(session)
    migrar_reportes(session)  # second call should not duplicate
    assert Caso.query.count() == 1
