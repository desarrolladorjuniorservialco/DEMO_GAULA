"""
One-time migration: table `reportes_backup` -> new normalized schema.

CLI usage (run once after deploying new schema):
    python scripts/migrate_reportes.py

Test/programmatic usage:
    from scripts.migrate_reportes import migrar_reportes
    migrar_reportes(session)
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def migrar_reportes(session):
    from sqlalchemy import text
    from models.nexo147 import (
        Caso, Reportante, CasoReportante, Evidencia, EventoCaso, MedioPago, UnidadGaula,
    )
    from models.intel import Telefono, Alias

    filas = session.execute(text("SELECT * FROM reportes_backup")).fetchall()
    migrados = 0

    for row in filas:
        row = row._mapping

        # Idempotency: skip if already migrated
        if Caso.query.filter_by(id_caso=row["id_reporte"]).first():
            continue

        # UnidadGaula: get or create
        unidad = None
        if row.get("unidad_gaula"):
            unidad = UnidadGaula.query.filter_by(nombre=row["unidad_gaula"]).first()
            if not unidad:
                unidad = UnidadGaula(nombre=row["unidad_gaula"], created_by="migration")
                session.add(unidad)
                session.flush()

        # Caso
        caso = Caso(
            id_caso         = row["id_reporte"] or str(uuid.uuid4()),
            estado          = row.get("estado") or "Recibido",
            prioridad       = row.get("prioridad"),
            tipo_caso       = row.get("tipo_reporte"),
            canal_recepcion = row.get("canal_recepcion"),
            unidad_gaula_id = unidad.id if unidad else None,
            descripcion     = row.get("descripcion"),
            observaciones   = row.get("observaciones"),
            created_by      = row.get("usuario_registro") or "migration",
        )
        session.add(caso)
        session.flush()

        # Reportante
        if row.get("nombre_reportante") or row.get("documento_reportante") or row.get("telefono_reportante"):
            rep = Reportante(
                nombre     = row.get("nombre_reportante"),
                documento  = row.get("documento_reportante"),
                telefono   = row.get("telefono_reportante"),
                anonimo    = not bool(row.get("nombre_reportante")),
                created_by = "migration",
            )
            session.add(rep)
            session.flush()
            session.add(CasoReportante(
                caso_id       = caso.id,
                reportante_id = rep.id,
                rol_en_caso   = "denunciante",
                created_by    = "migration",
            ))

        # MedioPago
        if row.get("medio_pago"):
            raw = str(row.get("valor_exigido") or "0").replace(",", "").replace("$", "").strip()
            try:
                valor = float(raw) if raw else 0.0
            except ValueError:
                valor = 0.0
            session.add(MedioPago(
                caso_id       = caso.id,
                tipo          = row["medio_pago"],
                valor_exigido = valor,
                referencia    = row.get("numero_extorsivo"),
                created_by    = "migration",
            ))

        # Evidencia
        if row.get("evidencia"):
            session.add(Evidencia(
                caso_id     = caso.id,
                tipo        = "referencia",
                descripcion = row["evidencia"],
                created_by  = "migration",
            ))

        # intel.db: Telefono (numero_extorsivo)
        if row.get("numero_extorsivo"):
            if not Telefono.query.filter_by(numero=row["numero_extorsivo"]).first():
                session.add(Telefono(
                    numero     = row["numero_extorsivo"],
                    tipo       = "celular",
                    pais       = "CO",
                    created_by = "migration",
                ))

        # intel.db: Alias (alias_sospechoso)
        if row.get("alias_sospechoso"):
            if not Alias.query.filter_by(valor=row["alias_sospechoso"]).first():
                session.add(Alias(
                    valor      = row["alias_sospechoso"],
                    contexto   = "caso_extorsion",
                    created_by = "migration",
                ))

        # EventoCaso (audit log)
        session.add(EventoCaso(
            caso_id      = caso.id,
            tipo_evento  = "migracion",
            descripcion  = "Caso migrado desde esquema anterior.",
            estado_nuevo = caso.estado,
            created_by   = "migration",
        ))

        migrados += 1

    session.commit()
    return migrados


def _renombrar_tabla_original():
    """Renames `reportes` -> `reportes_backup` before creating new schema."""
    from app import nexo, db
    from sqlalchemy import text, inspect
    with nexo.app_context():
        inspector = inspect(db.engine)
        tablas = inspector.get_table_names()
        if "reportes" in tablas and "reportes_backup" not in tablas:
            db.session.execute(text("ALTER TABLE reportes RENAME TO reportes_backup"))
            db.session.commit()
            print("Table `reportes` renamed to `reportes_backup`.")
        elif "reportes_backup" in tablas:
            print("`reportes_backup` already exists. Continuing.")
        else:
            print("No `reportes` table found. Nothing to rename.")


if __name__ == "__main__":
    from app import nexo, db
    with nexo.app_context():
        _renombrar_tabla_original()
        db.create_all()
        n = migrar_reportes(db.session)
        print(f"Migration complete: {n} cases migrated.")
