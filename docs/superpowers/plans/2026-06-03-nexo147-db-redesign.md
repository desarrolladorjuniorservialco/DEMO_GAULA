# NEXO-147 Database Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor NEXO-147 de una tabla `reportes` plana a una arquitectura normalizada de tres bases de datos (nexo147.db, intel.db, osint.db) que habilita analisis de inteligencia y correlacion de entidades.

**Architecture:** Flask-SQLAlchemy con `SQLALCHEMY_BINDS` gestiona tres archivos SQLite. Los modelos se separan en `models/nexo147.py`, `models/intel.py` y `models/osint.py`, todos importando un objeto `db` compartido de `models/__init__.py`. Las referencias cruzadas entre bases usan enteros simples sin FK (resueltas en capa de servicio Python).

**Tech Stack:** Flask 3.1.3, Flask-SQLAlchemy 3.1.1, SQLite (3 archivos), pytest 8.x, Werkzeug 3.1.8

---

## Mapa de archivos

| Archivo | Accion | Responsabilidad |
|---|---|---|
| `requirements.txt` | Modificar | Agregar pytest |
| `models/__init__.py` | Crear | Instancia compartida `db = SQLAlchemy()` |
| `models/nexo147.py` | Crear | Modelos nexo147.db (8 clases) |
| `models/intel.py` | Crear | Modelos intel.db (entidades + junctions + grafo) |
| `models/osint.py` | Crear | Modelos osint.db (5 clases) |
| `app.py` | Modificar | SQLALCHEMY_BINDS, db.init_app(), importar nuevos modelos, actualizar rutas |
| `scripts/migrate_reportes.py` | Crear | Script unico de migracion datos |
| `tests/conftest.py` | Crear | Fixtures pytest |
| `tests/test_nexo147_models.py` | Crear | Tests modelos nexo147.db |
| `tests/test_intel_models.py` | Crear | Tests modelos intel.db |
| `tests/test_osint_models.py` | Crear | Tests modelos osint.db |
| `tests/test_migration.py` | Crear | Test del script de migracion |

---

## Task 1: Instalar pytest y crear el paquete `models`

**Files:**
- Modify: `requirements.txt`
- Create: `models/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1.1: Agregar pytest a requirements.txt**

```text
blinker==1.9.0
click==8.4.0
colorama==0.4.6
Flask==3.1.3
flask-sqlalchemy==3.1.1
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.3
Werkzeug==3.1.8
pytest==8.3.5
requests==2.32.3
beautifulsoup4==4.13.4
```

- [ ] **Step 1.2: Instalar dependencias**

```bash
pip install pytest==8.3.5 requests==2.32.3 beautifulsoup4==4.13.4
```

Salida esperada: `Successfully installed pytest-8.3.5 ...`

- [ ] **Step 1.3: Crear `models/__init__.py`**

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
```

- [ ] **Step 1.4: Crear `tests/__init__.py`**

Archivo vacio (sin contenido).

- [ ] **Step 1.5: Escribir `tests/conftest.py`**

```python
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import nexo
from models import db as _db


@pytest.fixture(scope="function")
def app():
    nexo.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_BINDS": {
            "intel": "sqlite:///:memory:",
            "osint": "sqlite:///:memory:",
        },
    })
    with nexo.app_context():
        _db.create_all()
        yield nexo
        _db.drop_all()


@pytest.fixture
def session(app):
    yield _db.session
```

- [ ] **Step 1.6: Modificar `app.py` — sustituir instancia `db` por `init_app`**

Reemplazar el bloque al inicio de `app.py` que contiene `from flask_sqlalchemy import SQLAlchemy` y `db = SQLAlchemy(nexo)`:

```python
# Eliminar esta linea:
from flask_sqlalchemy import SQLAlchemy

# Agregar esta importacion al inicio, junto a los otros imports de Flask:
from models import db
```

Reemplazar el bloque de configuracion:

```python
# ANTES:
nexo.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(_basedir, "data", "nexo147.db")
nexo.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(nexo)

# DESPUES:
nexo.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(_basedir, "data", "nexo147.db")
nexo.config["SQLALCHEMY_BINDS"] = {
    "intel": "sqlite:///" + os.path.join(_basedir, "data", "intel.db"),
    "osint": "sqlite:///" + os.path.join(_basedir, "data", "osint.db"),
}
nexo.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(nexo)
```

- [ ] **Step 1.7: Verificar que Flask arranca sin error**

```bash
python -c "from app import nexo; print('OK')"
```

Salida esperada: `OK`

- [ ] **Step 1.8: Commit**

```bash
git add requirements.txt models/__init__.py tests/__init__.py tests/conftest.py app.py
git commit -m "chore: crear paquete models y configurar SQLALCHEMY_BINDS multi-DB"
```

---

## Task 2: nexo147.db — modelos `Usuario` y `UnidadGaula`

**Files:**
- Create: `models/nexo147.py`
- Create: `tests/test_nexo147_models.py`

- [ ] **Step 2.1: Escribir el test que falla**

```python
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
```

- [ ] **Step 2.2: Ejecutar para confirmar que falla**

```bash
pytest tests/test_nexo147_models.py -v
```

Salida esperada: `ERROR` — `ModuleNotFoundError: No module named 'models.nexo147'`

- [ ] **Step 2.3: Crear `models/nexo147.py` con `Usuario` y `UnidadGaula`**

```python
from datetime import datetime
from . import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre        = db.Column(db.String(100), nullable=False)
    rol           = db.Column(db.String(20), nullable=False)
    activo        = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by    = db.Column(db.String(50))
    updated_by    = db.Column(db.String(50))


class UnidadGaula(db.Model):
    __tablename__ = "unidades_gaula"

    id           = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(100), unique=True, nullable=False)
    ciudad       = db.Column(db.String(100))
    departamento = db.Column(db.String(100))
    activa       = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by   = db.Column(db.String(50))
    updated_by   = db.Column(db.String(50))

    casos = db.relationship("Caso", back_populates="unidad_gaula")
```

- [ ] **Step 2.4: Agregar imports en `app.py`**

Al inicio de `app.py`, despues de `from models import db`, agregar:

```python
from models.nexo147 import Usuario, UnidadGaula
```

- [ ] **Step 2.5: Ejecutar tests**

```bash
pytest tests/test_nexo147_models.py::test_usuario_creacion tests/test_nexo147_models.py::test_unidad_gaula_creacion -v
```

Salida esperada: `2 passed`

- [ ] **Step 2.6: Commit**

```bash
git add models/nexo147.py tests/test_nexo147_models.py app.py
git commit -m "feat: agregar modelos Usuario y UnidadGaula en nexo147.db"
```

---

## Task 3: nexo147.db — modelo `Caso`

**Files:**
- Modify: `models/nexo147.py`
- Modify: `tests/test_nexo147_models.py`

- [ ] **Step 3.1: Agregar test**

Anadir al final de `tests/test_nexo147_models.py`:

```python
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
    from models.nexo147 import Caso
    uid = str(uuid.uuid4())
    session.add(Caso(id_caso=uid, estado="Recibido", created_by="test"))
    session.commit()
    session.add(Caso(id_caso=uid, estado="Recibido", created_by="test"))
    import pytest
    with pytest.raises(Exception):
        session.commit()
```

- [ ] **Step 3.2: Ejecutar para confirmar que falla**

```bash
pytest tests/test_nexo147_models.py::test_caso_creacion -v
```

Salida esperada: `FAILED` — `ImportError` o `AttributeError`

- [ ] **Step 3.3: Agregar clase `Caso` a `models/nexo147.py`**

Anadir despues de `UnidadGaula`:

```python
class Caso(db.Model):
    __tablename__ = "casos"
    __table_args__ = (
        db.Index("ix_casos_estado",    "estado"),
        db.Index("ix_casos_prioridad", "prioridad"),
        db.Index("ix_casos_tipo",      "tipo_caso"),
        db.Index("ix_casos_fecha",     "fecha_registro"),
        {},
    )

    id                  = db.Column(db.Integer, primary_key=True)
    id_caso             = db.Column(db.String(36), unique=True, nullable=False)
    fecha_registro      = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, onupdate=datetime.utcnow)
    estado              = db.Column(db.String(20), default="Recibido")
    prioridad           = db.Column(db.String(20))
    tipo_caso           = db.Column(db.String(50))
    canal_recepcion     = db.Column(db.String(50))
    unidad_gaula_id     = db.Column(db.Integer, db.ForeignKey("unidades_gaula.id"))
    descripcion         = db.Column(db.Text)
    observaciones       = db.Column(db.Text)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at          = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by          = db.Column(db.String(50))
    updated_by          = db.Column(db.String(50))

    unidad_gaula = db.relationship("UnidadGaula", back_populates="casos")
    reportantes  = db.relationship("CasoReportante", back_populates="caso")
    evidencias   = db.relationship("Evidencia",       back_populates="caso")
    eventos      = db.relationship("EventoCaso",      back_populates="caso")
    medios_pago  = db.relationship("MedioPago",       back_populates="caso")
```

- [ ] **Step 3.4: Actualizar import en `app.py`**

```python
from models.nexo147 import Usuario, UnidadGaula, Caso
```

- [ ] **Step 3.5: Ejecutar tests**

```bash
pytest tests/test_nexo147_models.py -v
```

Salida esperada: todos los tests hasta ahora `passed`

- [ ] **Step 3.6: Commit**

```bash
git add models/nexo147.py tests/test_nexo147_models.py app.py
git commit -m "feat: agregar modelo Caso con indices en nexo147.db"
```

---

## Task 4: nexo147.db — `Reportante`, `CasoReportante`

**Files:**
- Modify: `models/nexo147.py`
- Modify: `tests/test_nexo147_models.py`

- [ ] **Step 4.1: Agregar tests**

```python
def test_reportante_y_junction(session):
    import uuid
    from models.nexo147 import Caso, Reportante, CasoReportante
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
    from models.nexo147 import Reportante
    r = Reportante()
    session.add(r)
    session.commit()
    assert r.anonimo is False
```

- [ ] **Step 4.2: Ejecutar para confirmar que falla**

```bash
pytest tests/test_nexo147_models.py::test_reportante_y_junction -v
```

Salida esperada: `FAILED` — `ImportError`

- [ ] **Step 4.3: Agregar clases a `models/nexo147.py`**

```python
class Reportante(db.Model):
    __tablename__ = "reportantes"
    __table_args__ = (
        db.Index("ix_reportantes_documento", "documento"),
        db.Index("ix_reportantes_telefono",  "telefono"),
        {},
    )

    id         = db.Column(db.Integer, primary_key=True)
    nombre     = db.Column(db.String(100))
    documento  = db.Column(db.String(30))
    telefono   = db.Column(db.String(20))
    anonimo    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))

    casos = db.relationship("CasoReportante", back_populates="reportante")


class CasoReportante(db.Model):
    __tablename__ = "caso_reportante"

    caso_id       = db.Column(db.Integer, db.ForeignKey("casos.id"),       primary_key=True)
    reportante_id = db.Column(db.Integer, db.ForeignKey("reportantes.id"), primary_key=True)
    rol_en_caso   = db.Column(db.String(50))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    created_by    = db.Column(db.String(50))

    caso       = db.relationship("Caso",       back_populates="reportantes")
    reportante = db.relationship("Reportante", back_populates="casos")
```

- [ ] **Step 4.4: Actualizar import en `app.py`**

```python
from models.nexo147 import Usuario, UnidadGaula, Caso, Reportante, CasoReportante
```

- [ ] **Step 4.5: Ejecutar tests**

```bash
pytest tests/test_nexo147_models.py -v
```

Salida esperada: todos `passed`

- [ ] **Step 4.6: Commit**

```bash
git add models/nexo147.py tests/test_nexo147_models.py app.py
git commit -m "feat: agregar modelos Reportante y CasoReportante"
```

---

## Task 5: nexo147.db — `Evidencia`, `EventoCaso`, `MedioPago`

**Files:**
- Modify: `models/nexo147.py`
- Modify: `tests/test_nexo147_models.py`

- [ ] **Step 5.1: Agregar tests**

```python
def test_evidencia(session):
    import uuid
    from models.nexo147 import Caso, Evidencia
    caso = Caso(id_caso=str(uuid.uuid4()), estado="Recibido", created_by="test")
    session.add(caso)
    session.flush()
    e = Evidencia(caso_id=caso.id, tipo="audio", descripcion="Llamada grabada", created_by="test")
    session.add(e)
    session.commit()
    assert e.id is not None
    assert caso.evidencias[0].tipo == "audio"


def test_evento_caso(session):
    import uuid
    from models.nexo147 import Caso, EventoCaso
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
    import uuid
    from models.nexo147 import Caso, MedioPago
    caso = Caso(id_caso=str(uuid.uuid4()), estado="Recibido", created_by="test")
    session.add(caso)
    session.flush()
    mp = MedioPago(caso_id=caso.id, tipo="nequi", valor_exigido=500000, moneda="COP", created_by="test")
    session.add(mp)
    session.commit()
    assert float(mp.valor_exigido) == 500000.0
```

- [ ] **Step 5.2: Ejecutar para confirmar que falla**

```bash
pytest tests/test_nexo147_models.py::test_evidencia -v
```

Salida esperada: `FAILED` — `ImportError`

- [ ] **Step 5.3: Agregar las tres clases a `models/nexo147.py`**

```python
class Evidencia(db.Model):
    __tablename__ = "evidencias"

    id           = db.Column(db.Integer, primary_key=True)
    caso_id      = db.Column(db.Integer, db.ForeignKey("casos.id"), nullable=False)
    tipo         = db.Column(db.String(50))
    descripcion  = db.Column(db.String(200))
    ruta_archivo = db.Column(db.String(500))
    hash_sha256  = db.Column(db.String(64))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by   = db.Column(db.String(50))
    updated_by   = db.Column(db.String(50))

    caso = db.relationship("Caso", back_populates="evidencias")


class EventoCaso(db.Model):
    __tablename__ = "eventos_caso"

    id              = db.Column(db.Integer, primary_key=True)
    caso_id         = db.Column(db.Integer, db.ForeignKey("casos.id"), nullable=False)
    tipo_evento     = db.Column(db.String(50))
    descripcion     = db.Column(db.Text)
    estado_anterior = db.Column(db.String(20))
    estado_nuevo    = db.Column(db.String(20))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    created_by      = db.Column(db.String(50))

    caso = db.relationship("Caso", back_populates="eventos")


class MedioPago(db.Model):
    __tablename__ = "medios_pago"

    id            = db.Column(db.Integer, primary_key=True)
    caso_id       = db.Column(db.Integer, db.ForeignKey("casos.id"), nullable=False)
    tipo          = db.Column(db.String(50))
    valor_exigido = db.Column(db.Numeric(15, 2))
    moneda        = db.Column(db.String(10), default="COP")
    referencia    = db.Column(db.String(100))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by    = db.Column(db.String(50))
    updated_by    = db.Column(db.String(50))

    caso = db.relationship("Caso", back_populates="medios_pago")
```

- [ ] **Step 5.4: Actualizar import en `app.py`**

```python
from models.nexo147 import (
    Usuario, UnidadGaula, Caso, Reportante, CasoReportante,
    Evidencia, EventoCaso, MedioPago
)
```

- [ ] **Step 5.5: Ejecutar todos los tests nexo147**

```bash
pytest tests/test_nexo147_models.py -v
```

Salida esperada: todos `passed`

- [ ] **Step 5.6: Commit**

```bash
git add models/nexo147.py tests/test_nexo147_models.py app.py
git commit -m "feat: completar modelos nexo147.db (Evidencia, EventoCaso, MedioPago)"
```

---

## Task 6: intel.db — entidades principales

**Files:**
- Create: `models/intel.py`
- Create: `tests/test_intel_models.py`

- [ ] **Step 6.1: Escribir tests que fallan**

```python
# tests/test_intel_models.py
from models.intel import (
    Persona, Alias, Telefono, Correo, Direccion,
    Ubicacion, Vehiculo, CuentaBancaria, RedSocial, Organizacion,
)


def test_persona_creacion(session):
    p = Persona(nombres="Carlos", apellidos="Ramirez", documento="987654",
                tipo_documento="CC", nivel_riesgo="alto", es_objetivo=True,
                created_by="analista")
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
    import pytest
    with pytest.raises(Exception):
        session.commit()


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
```

- [ ] **Step 6.2: Ejecutar para confirmar que falla**

```bash
pytest tests/test_intel_models.py -v
```

Salida esperada: `ERROR` — `ModuleNotFoundError: No module named 'models.intel'`

- [ ] **Step 6.3: Crear `models/intel.py` con entidades principales**

```python
from datetime import datetime
from . import db


class Persona(db.Model):
    __tablename__ = "personas"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_personas_documento",    "documento"),
        db.Index("ix_personas_nivel_riesgo", "nivel_riesgo"),
        db.Index("ix_personas_objetivo",     "es_objetivo"),
        {},
    )

    id               = db.Column(db.Integer, primary_key=True)
    nombres          = db.Column(db.String(100))
    apellidos        = db.Column(db.String(100))
    documento        = db.Column(db.String(30))
    tipo_documento   = db.Column(db.String(20))
    fecha_nacimiento = db.Column(db.Date)
    nacionalidad     = db.Column(db.String(50))
    sexo             = db.Column(db.String(10))
    nivel_riesgo     = db.Column(db.String(20))
    es_objetivo      = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by       = db.Column(db.String(50))
    updated_by       = db.Column(db.String(50))


class Alias(db.Model):
    __tablename__ = "alias"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_alias_valor", "valor"),
        {},
    )

    id         = db.Column(db.Integer, primary_key=True)
    valor      = db.Column(db.String(100), nullable=False)
    contexto   = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))


class Telefono(db.Model):
    __tablename__ = "telefonos"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_telefonos_numero", "numero"),
        {},
    )

    id         = db.Column(db.Integer, primary_key=True)
    numero     = db.Column(db.String(30), unique=True, nullable=False)
    operador   = db.Column(db.String(50))
    pais       = db.Column(db.String(5), default="CO")
    tipo       = db.Column(db.String(20))
    activo     = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))


class Correo(db.Model):
    __tablename__ = "correos"
    __bind_key__ = "intel"

    id         = db.Column(db.Integer, primary_key=True)
    direccion  = db.Column(db.String(200), unique=True, nullable=False)
    dominio    = db.Column(db.String(100))
    proveedor  = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))


class Direccion(db.Model):
    __tablename__ = "direcciones"
    __bind_key__ = "intel"

    id            = db.Column(db.Integer, primary_key=True)
    linea1        = db.Column(db.String(200))
    barrio        = db.Column(db.String(100))
    ciudad        = db.Column(db.String(100))
    departamento  = db.Column(db.String(100))
    pais          = db.Column(db.String(50), default="Colombia")
    codigo_postal = db.Column(db.String(10))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by    = db.Column(db.String(50))
    updated_by    = db.Column(db.String(50))


class Ubicacion(db.Model):
    __tablename__ = "ubicaciones"
    __bind_key__ = "intel"

    id               = db.Column(db.Integer, primary_key=True)
    latitud          = db.Column(db.Float)
    longitud         = db.Column(db.Float)
    descripcion      = db.Column(db.String(200))
    precision_metros = db.Column(db.Integer)
    fuente           = db.Column(db.String(100))
    fecha_captura    = db.Column(db.DateTime)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by       = db.Column(db.String(50))
    updated_by       = db.Column(db.String(50))


class Vehiculo(db.Model):
    __tablename__ = "vehiculos"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_vehiculos_placa", "placa"),
        {},
    )

    id         = db.Column(db.Integer, primary_key=True)
    placa      = db.Column(db.String(20))
    tipo       = db.Column(db.String(50))
    marca      = db.Column(db.String(50))
    modelo     = db.Column(db.String(50))
    anio       = db.Column(db.Integer)
    color      = db.Column(db.String(30))
    vin        = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))


class CuentaBancaria(db.Model):
    __tablename__ = "cuentas_bancarias"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_cuentas_numero",  "numero"),
        db.Index("ix_cuentas_entidad", "entidad"),
        {},
    )

    id                = db.Column(db.Integer, primary_key=True)
    numero            = db.Column(db.String(50))
    tipo              = db.Column(db.String(30))
    entidad           = db.Column(db.String(100))
    titular_declarado = db.Column(db.String(100))
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at        = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by        = db.Column(db.String(50))
    updated_by        = db.Column(db.String(50))


class RedSocial(db.Model):
    __tablename__ = "redes_sociales"
    __bind_key__ = "intel"

    id         = db.Column(db.Integer, primary_key=True)
    plataforma = db.Column(db.String(50))
    handle     = db.Column(db.String(100))
    url_perfil = db.Column(db.String(500))
    activo     = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))


class Organizacion(db.Model):
    __tablename__ = "organizaciones"
    __bind_key__ = "intel"

    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(200))
    tipo        = db.Column(db.String(50))
    descripcion = db.Column(db.Text)
    activa      = db.Column(db.Boolean)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by  = db.Column(db.String(50))
    updated_by  = db.Column(db.String(50))
```

- [ ] **Step 6.4: Ejecutar tests**

```bash
pytest tests/test_intel_models.py -v
```

Salida esperada: todos `passed`

- [ ] **Step 6.5: Commit**

```bash
git add models/intel.py tests/test_intel_models.py
git commit -m "feat: agregar entidades principales de intel.db"
```

---

## Task 7: intel.db — tablas de relacion M:M

**Files:**
- Modify: `models/intel.py`
- Modify: `tests/test_intel_models.py`

- [ ] **Step 7.1: Agregar tests**

```python
def test_persona_alias(session):
    from models.intel import Persona, Alias, PersonaAlias
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
    from models.intel import Persona, Telefono, PersonaTelefono
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
    from models.intel import Persona, CasoPersona
    p = Persona(nombres="Luis", apellidos="Perez", created_by="test")
    session.add(p)
    session.flush()
    cp = CasoPersona(caso_id=999, persona_id=p.id,
                     rol_en_caso="sospechoso", created_by="test")
    session.add(cp)
    session.commit()
    assert cp.caso_id == 999
```

- [ ] **Step 7.2: Ejecutar para confirmar que falla**

```bash
pytest tests/test_intel_models.py::test_persona_alias -v
```

Salida esperada: `FAILED` — `ImportError`

- [ ] **Step 7.3: Agregar clases de relacion a `models/intel.py`**

Anadir al final del archivo (despues de `Organizacion`):

```python
class PersonaAlias(db.Model):
    __tablename__ = "persona_alias"
    __bind_key__ = "intel"

    persona_id   = db.Column(db.Integer, db.ForeignKey("personas.id"), primary_key=True)
    alias_id     = db.Column(db.Integer, db.ForeignKey("alias.id"),    primary_key=True)
    fecha_inicio = db.Column(db.DateTime)
    fecha_fin    = db.Column(db.DateTime)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    created_by   = db.Column(db.String(50))

    persona = db.relationship("Persona", backref="alias_rel")
    alias   = db.relationship("Alias",   backref="personas_rel")


class PersonaTelefono(db.Model):
    __tablename__ = "persona_telefono"
    __bind_key__ = "intel"

    persona_id  = db.Column(db.Integer, db.ForeignKey("personas.id"),  primary_key=True)
    telefono_id = db.Column(db.Integer, db.ForeignKey("telefonos.id"), primary_key=True)
    relacion    = db.Column(db.String(50))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.String(50))

    persona  = db.relationship("Persona",  backref="telefonos_rel")
    telefono = db.relationship("Telefono", backref="personas_rel")


class PersonaCorreo(db.Model):
    __tablename__ = "persona_correo"
    __bind_key__ = "intel"

    persona_id = db.Column(db.Integer, db.ForeignKey("personas.id"), primary_key=True)
    correo_id  = db.Column(db.Integer, db.ForeignKey("correos.id"),  primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))

    persona = db.relationship("Persona", backref="correos_rel")
    correo  = db.relationship("Correo",  backref="personas_rel")


class PersonaDireccion(db.Model):
    __tablename__ = "persona_direccion"
    __bind_key__ = "intel"

    persona_id   = db.Column(db.Integer, db.ForeignKey("personas.id"),    primary_key=True)
    direccion_id = db.Column(db.Integer, db.ForeignKey("direcciones.id"), primary_key=True)
    tipo         = db.Column(db.String(50))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    created_by   = db.Column(db.String(50))

    persona   = db.relationship("Persona",   backref="direcciones_rel")
    direccion = db.relationship("Direccion", backref="personas_rel")


class PersonaVehiculo(db.Model):
    __tablename__ = "persona_vehiculo"
    __bind_key__ = "intel"

    persona_id  = db.Column(db.Integer, db.ForeignKey("personas.id"),  primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey("vehiculos.id"), primary_key=True)
    rol         = db.Column(db.String(50))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.String(50))

    persona  = db.relationship("Persona",  backref="vehiculos_rel")
    vehiculo = db.relationship("Vehiculo", backref="personas_rel")


class PersonaCuenta(db.Model):
    __tablename__ = "persona_cuenta"
    __bind_key__ = "intel"

    persona_id = db.Column(db.Integer, db.ForeignKey("personas.id"),          primary_key=True)
    cuenta_id  = db.Column(db.Integer, db.ForeignKey("cuentas_bancarias.id"), primary_key=True)
    rol        = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))

    persona = db.relationship("Persona",        backref="cuentas_rel")
    cuenta  = db.relationship("CuentaBancaria", backref="personas_rel")


class PersonaRedSocial(db.Model):
    __tablename__ = "persona_red_social"
    __bind_key__ = "intel"

    persona_id    = db.Column(db.Integer, db.ForeignKey("personas.id"),       primary_key=True)
    red_social_id = db.Column(db.Integer, db.ForeignKey("redes_sociales.id"), primary_key=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    created_by    = db.Column(db.String(50))

    persona    = db.relationship("Persona",   backref="redes_rel")
    red_social = db.relationship("RedSocial", backref="personas_rel")


class PersonaOrganizacion(db.Model):
    __tablename__ = "persona_organizacion"
    __bind_key__ = "intel"

    persona_id      = db.Column(db.Integer, db.ForeignKey("personas.id"),       primary_key=True)
    organizacion_id = db.Column(db.Integer, db.ForeignKey("organizaciones.id"), primary_key=True)
    rol_org         = db.Column(db.String(50))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    created_by      = db.Column(db.String(50))

    persona      = db.relationship("Persona",      backref="organizaciones_rel")
    organizacion = db.relationship("Organizacion", backref="personas_rel")


class OrganizacionTelefono(db.Model):
    __tablename__ = "organizacion_telefono"
    __bind_key__ = "intel"

    organizacion_id = db.Column(db.Integer, db.ForeignKey("organizaciones.id"), primary_key=True)
    telefono_id     = db.Column(db.Integer, db.ForeignKey("telefonos.id"),       primary_key=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    created_by      = db.Column(db.String(50))

    organizacion = db.relationship("Organizacion", backref="telefonos_rel")
    telefono     = db.relationship("Telefono",     backref="organizaciones_rel")


class OrganizacionCuenta(db.Model):
    __tablename__ = "organizacion_cuenta"
    __bind_key__ = "intel"

    organizacion_id = db.Column(db.Integer, db.ForeignKey("organizaciones.id"),  primary_key=True)
    cuenta_id       = db.Column(db.Integer, db.ForeignKey("cuentas_bancarias.id"), primary_key=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    created_by      = db.Column(db.String(50))

    organizacion = db.relationship("Organizacion",   backref="cuentas_rel")
    cuenta       = db.relationship("CuentaBancaria", backref="organizaciones_rel")


# Tablas cruzadas nexo147 <-> intel (caso_id sin FK — referencia logica entre bases)

class CasoPersona(db.Model):
    __tablename__ = "caso_persona"
    __bind_key__ = "intel"

    caso_id     = db.Column(db.Integer, primary_key=True)  # nexo147.casos.id, sin FK
    persona_id  = db.Column(db.Integer, db.ForeignKey("personas.id"), primary_key=True)
    rol_en_caso = db.Column(db.String(50))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.String(50))

    persona = db.relationship("Persona", backref="casos_rel")


class CasoTelefono(db.Model):
    __tablename__ = "caso_telefono"
    __bind_key__ = "intel"

    caso_id     = db.Column(db.Integer, primary_key=True)
    telefono_id = db.Column(db.Integer, db.ForeignKey("telefonos.id"), primary_key=True)
    contexto    = db.Column(db.String(100))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    created_by  = db.Column(db.String(50))

    telefono = db.relationship("Telefono", backref="casos_rel")


class CasoUbicacion(db.Model):
    __tablename__ = "caso_ubicacion"
    __bind_key__ = "intel"

    caso_id        = db.Column(db.Integer, primary_key=True)
    ubicacion_id   = db.Column(db.Integer, db.ForeignKey("ubicaciones.id"), primary_key=True)
    tipo_ubicacion = db.Column(db.String(50))
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    created_by     = db.Column(db.String(50))

    ubicacion = db.relationship("Ubicacion", backref="casos_rel")


class CasoCuenta(db.Model):
    __tablename__ = "caso_cuenta"
    __bind_key__ = "intel"

    caso_id   = db.Column(db.Integer, primary_key=True)
    cuenta_id = db.Column(db.Integer, db.ForeignKey("cuentas_bancarias.id"), primary_key=True)
    uso       = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))

    cuenta = db.relationship("CuentaBancaria", backref="casos_rel")
```

- [ ] **Step 7.4: Ejecutar tests**

```bash
pytest tests/test_intel_models.py -v
```

Salida esperada: todos `passed`

- [ ] **Step 7.5: Commit**

```bash
git add models/intel.py tests/test_intel_models.py
git commit -m "feat: agregar tablas M:M de intel.db"
```

---

## Task 8: intel.db — grafo y hallazgos

**Files:**
- Modify: `models/intel.py`
- Modify: `tests/test_intel_models.py`

- [ ] **Step 8.1: Agregar tests**

```python
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
    import pytest
    with pytest.raises(Exception):
        session.commit()


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
```

- [ ] **Step 8.2: Ejecutar para confirmar que falla**

```bash
pytest tests/test_intel_models.py::test_intel_node_creacion -v
```

Salida esperada: `FAILED` — `ImportError`

- [ ] **Step 8.3: Agregar clases a `models/intel.py`**

```python
class IntelNode(db.Model):
    __tablename__ = "intel_nodes"
    __bind_key__ = "intel"
    __table_args__ = (
        db.UniqueConstraint("entity_type", "entity_id", name="uq_node_entity"),
        {},
    )

    id            = db.Column(db.Integer, primary_key=True)
    entity_type   = db.Column(db.String(50), nullable=False)
    entity_id     = db.Column(db.Integer,    nullable=False)
    label         = db.Column(db.String(200))
    nivel_riesgo  = db.Column(db.String(20))
    metadata_json = db.Column(db.Text)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by    = db.Column(db.String(50))
    updated_by    = db.Column(db.String(50))

    edges_out = db.relationship("IntelEdge", foreign_keys="IntelEdge.source_node_id",
                                backref="source_node")
    edges_in  = db.relationship("IntelEdge", foreign_keys="IntelEdge.target_node_id",
                                backref="target_node")


class IntelEdge(db.Model):
    __tablename__ = "intel_edges"
    __bind_key__ = "intel"
    __table_args__ = (
        db.Index("ix_edges_source", "source_node_id"),
        db.Index("ix_edges_target", "target_node_id"),
        db.Index("ix_edges_tipo",   "tipo_relacion"),
        {},
    )

    id              = db.Column(db.Integer, primary_key=True)
    source_node_id  = db.Column(db.Integer, db.ForeignKey("intel_nodes.id"), nullable=False)
    target_node_id  = db.Column(db.Integer, db.ForeignKey("intel_nodes.id"), nullable=False)
    tipo_relacion   = db.Column(db.String(50))
    descripcion     = db.Column(db.String(200))
    confianza       = db.Column(db.Float, default=1.0)
    fuente          = db.Column(db.String(100))
    fecha_deteccion = db.Column(db.DateTime)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by      = db.Column(db.String(50))
    updated_by      = db.Column(db.String(50))


class HallazgoIntel(db.Model):
    __tablename__ = "hallazgos_intel"
    __bind_key__ = "intel"

    id                  = db.Column(db.Integer, primary_key=True)
    titulo              = db.Column(db.String(200))
    descripcion         = db.Column(db.Text)
    nivel_clasificacion = db.Column(db.String(20))
    caso_referencia_id  = db.Column(db.Integer)
    analista_id         = db.Column(db.Integer)
    estado              = db.Column(db.String(20))
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at          = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by          = db.Column(db.String(50))
    updated_by          = db.Column(db.String(50))
```

- [ ] **Step 8.4: Ejecutar todos los tests de intel**

```bash
pytest tests/test_intel_models.py -v
```

Salida esperada: todos `passed`

- [ ] **Step 8.5: Commit**

```bash
git add models/intel.py tests/test_intel_models.py
git commit -m "feat: agregar grafo intel_nodes/intel_edges y hallazgos_intel"
```

---

## Task 9: osint.db — los 5 modelos

**Files:**
- Create: `models/osint.py`
- Create: `tests/test_osint_models.py`

- [ ] **Step 9.1: Escribir tests**

```python
# tests/test_osint_models.py
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
    import pytest
    with pytest.raises(Exception):
        session.commit()


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
```

- [ ] **Step 9.2: Ejecutar para confirmar que falla**

```bash
pytest tests/test_osint_models.py -v
```

Salida esperada: `ERROR` — `ModuleNotFoundError: No module named 'models.osint'`

- [ ] **Step 9.3: Crear `models/osint.py`**

```python
from datetime import datetime
from . import db


class FuenteOsint(db.Model):
    __tablename__ = "fuentes_osint"
    __bind_key__ = "osint"

    id                 = db.Column(db.Integer, primary_key=True)
    nombre             = db.Column(db.String(100), unique=True, nullable=False)
    tipo               = db.Column(db.String(50))
    url_base           = db.Column(db.String(500))
    requiere_key       = db.Column(db.Boolean, default=True)
    activa             = db.Column(db.Boolean, default=True)
    rate_limit_por_min = db.Column(db.Integer)
    descripcion        = db.Column(db.Text)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by         = db.Column(db.String(50))
    updated_by         = db.Column(db.String(50))

    consultas = db.relationship("ConsultaOsint", back_populates="fuente")


class ConsultaOsint(db.Model):
    __tablename__ = "consultas_osint"
    __bind_key__ = "osint"
    __table_args__ = (
        db.Index("ix_consultas_valor",  "valor_consultado"),
        db.Index("ix_consultas_tipo",   "tipo_consulta"),
        db.Index("ix_consultas_fuente", "fuente_id"),
        {},
    )

    id                 = db.Column(db.Integer, primary_key=True)
    fuente_id          = db.Column(db.Integer, db.ForeignKey("fuentes_osint.id"), nullable=False)
    tipo_consulta      = db.Column(db.String(50))
    valor_consultado   = db.Column(db.String(500))
    caso_referencia_id = db.Column(db.Integer)
    entity_type        = db.Column(db.String(50))
    entity_id          = db.Column(db.Integer)
    estado             = db.Column(db.String(20))
    usuario_id         = db.Column(db.Integer)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    created_by         = db.Column(db.String(50))

    fuente     = db.relationship("FuenteOsint",  back_populates="consultas")
    cache      = db.relationship("CacheConsulta",  back_populates="consulta", uselist=False)
    resultados = db.relationship("ResultadoOsint", back_populates="consulta")


class CacheConsulta(db.Model):
    __tablename__ = "cache_consultas"
    __bind_key__ = "osint"

    id             = db.Column(db.Integer, primary_key=True)
    consulta_id    = db.Column(db.Integer, db.ForeignKey("consultas_osint.id"), nullable=False)
    hash_clave     = db.Column(db.String(64), unique=True, nullable=False)
    respuesta_raw  = db.Column(db.Text)
    codigo_http    = db.Column(db.Integer)
    fecha_consulta = db.Column(db.DateTime, default=datetime.utcnow)
    expira_en      = db.Column(db.DateTime)
    hits           = db.Column(db.Integer, default=0)

    consulta = db.relationship("ConsultaOsint", back_populates="cache")


class ResultadoOsint(db.Model):
    __tablename__ = "resultados_osint"
    __bind_key__ = "osint"

    id            = db.Column(db.Integer, primary_key=True)
    consulta_id   = db.Column(db.Integer, db.ForeignKey("consultas_osint.id"), nullable=False)
    tipo_hallazgo = db.Column(db.String(50))
    titulo        = db.Column(db.String(200))
    descripcion   = db.Column(db.Text)
    datos_json    = db.Column(db.Text)
    relevancia    = db.Column(db.Float, default=0.5)
    verificado    = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by    = db.Column(db.String(50))
    updated_by    = db.Column(db.String(50))

    consulta = db.relationship("ConsultaOsint", back_populates="resultados")


class IndicadorRiesgo(db.Model):
    __tablename__ = "indicadores_riesgo"
    __bind_key__ = "osint"
    __table_args__ = (
        db.Index("ix_indicadores_tipo",   "tipo"),
        db.Index("ix_indicadores_valor",  "valor"),
        db.Index("ix_indicadores_riesgo", "nivel_riesgo"),
        db.Index("ix_indicadores_activo", "activo"),
        {},
    )

    id                 = db.Column(db.Integer, primary_key=True)
    tipo               = db.Column(db.String(50))
    valor              = db.Column(db.String(500), nullable=False)
    descripcion        = db.Column(db.String(200))
    nivel_riesgo       = db.Column(db.String(20))
    fuente_origen      = db.Column(db.String(100))
    caso_referencia_id = db.Column(db.Integer)
    activo             = db.Column(db.Boolean, default=True)
    fecha_deteccion    = db.Column(db.DateTime)
    fecha_expiracion   = db.Column(db.DateTime)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime, onupdate=datetime.utcnow)
    created_by         = db.Column(db.String(50))
    updated_by         = db.Column(db.String(50))
```

- [ ] **Step 9.4: Ejecutar todos los tests de osint**

```bash
pytest tests/test_osint_models.py -v
```

Salida esperada: todos `passed`

- [ ] **Step 9.5: Ejecutar suite completa**

```bash
pytest tests/ -v
```

Salida esperada: todos los tests de los tres dominios pasan.

- [ ] **Step 9.6: Commit**

```bash
git add models/osint.py tests/test_osint_models.py
git commit -m "feat: agregar modelos osint.db completos"
```

---

## Task 10: Script de migracion automatica

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/migrate_reportes.py`
- Create: `tests/test_migration.py`

- [ ] **Step 10.1: Escribir test de migracion**

```python
# tests/test_migration.py
import uuid
from models.nexo147 import Caso, Reportante, CasoReportante, EventoCaso, MedioPago, Evidencia
from models.intel import Telefono, Alias


def _seed_old_reporte(session):
    from sqlalchemy import text
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
    rep = Reportante.query.first()
    assert rep.nombre == "Maria Garcia"

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
    migrar_reportes(session)
    assert Caso.query.count() == 1
```

- [ ] **Step 10.2: Ejecutar para confirmar que falla**

```bash
pytest tests/test_migration.py -v
```

Salida esperada: `FAILED` — `ModuleNotFoundError: No module named 'scripts.migrate_reportes'`

- [ ] **Step 10.3: Crear `scripts/__init__.py`**

Archivo vacio (sin contenido).

- [ ] **Step 10.4: Crear `scripts/migrate_reportes.py`**

```python
"""
Script unico de migracion: tabla `reportes_backup` -> nueva estructura normalizada.

Uso desde terminal:
    python scripts/migrate_reportes.py

Uso desde tests (pasa session directamente):
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

        if Caso.query.filter_by(id_caso=row["id_reporte"]).first():
            continue

        unidad = None
        if row.get("unidad_gaula"):
            unidad = UnidadGaula.query.filter_by(nombre=row["unidad_gaula"]).first()
            if not unidad:
                unidad = UnidadGaula(nombre=row["unidad_gaula"], created_by="migration")
                session.add(unidad)
                session.flush()

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

        if row.get("nombre_reportante") or row.get("documento_reportante") or row.get("telefono_reportante"):
            rep = Reportante(
                nombre    = row.get("nombre_reportante"),
                documento = row.get("documento_reportante"),
                telefono  = row.get("telefono_reportante"),
                anonimo   = not bool(row.get("nombre_reportante")),
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

        if row.get("evidencia"):
            session.add(Evidencia(
                caso_id     = caso.id,
                tipo        = "referencia",
                descripcion = row["evidencia"],
                created_by  = "migration",
            ))

        if row.get("numero_extorsivo"):
            if not Telefono.query.filter_by(numero=row["numero_extorsivo"]).first():
                session.add(Telefono(
                    numero     = row["numero_extorsivo"],
                    tipo       = "celular",
                    pais       = "CO",
                    created_by = "migration",
                ))

        if row.get("alias_sospechoso"):
            if not Alias.query.filter_by(valor=row["alias_sospechoso"]).first():
                session.add(Alias(
                    valor      = row["alias_sospechoso"],
                    contexto   = "caso_extorsion",
                    created_by = "migration",
                ))

        session.add(EventoCaso(
            caso_id     = caso.id,
            tipo_evento = "migracion",
            descripcion = "Caso migrado desde esquema anterior.",
            estado_nuevo = caso.estado,
            created_by  = "migration",
        ))

        migrados += 1

    session.commit()
    return migrados


def _renombrar_tabla_original():
    from app import nexo, db
    from sqlalchemy import text, inspect
    with nexo.app_context():
        inspector = inspect(db.engine)
        tablas = inspector.get_table_names()
        if "reportes" in tablas and "reportes_backup" not in tablas:
            db.session.execute(text("ALTER TABLE reportes RENAME TO reportes_backup"))
            db.session.commit()
            print("Tabla `reportes` renombrada a `reportes_backup`.")
        elif "reportes_backup" in tablas:
            print("Ya existe `reportes_backup`. Continuando.")
        else:
            print("No existe tabla `reportes`. Nada que renombrar.")


if __name__ == "__main__":
    from app import nexo, db
    with nexo.app_context():
        _renombrar_tabla_original()
        db.create_all()
        n = migrar_reportes(db.session)
        print(f"Migracion completa: {n} casos migrados.")
```

- [ ] **Step 10.5: Ejecutar tests de migracion**

```bash
pytest tests/test_migration.py -v
```

Salida esperada: `2 passed`

- [ ] **Step 10.6: Ejecutar suite completa**

```bash
pytest tests/ -v
```

Salida esperada: todos los tests pasan.

- [ ] **Step 10.7: Commit**

```bash
git add scripts/__init__.py scripts/migrate_reportes.py tests/test_migration.py
git commit -m "feat: agregar script de migracion automatica reportes -> nueva estructura"
```

---

## Task 11: Actualizar rutas de `app.py`

**Files:**
- Modify: `app.py`

- [ ] **Step 11.1: Eliminar la clase `Reporte` de `app.py`**

Eliminar completamente el bloque de la clase `Reporte` (desde `class Reporte(db.Model):` hasta el ultimo campo `observaciones`).

- [ ] **Step 11.2: Reemplazar la funcion `registrar_reporte`**

```python
@nexo.route("/registrar-reporte", methods=["POST"])
@login_required
def registrar_reporte():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    tipo_caso   = data.get("tipo_reporte", "").strip()
    prioridad   = data.get("prioridad", "").strip()
    descripcion = data.get("descripcion", "").strip()

    if not tipo_caso or not prioridad or not descripcion:
        if request.is_json:
            return {"error": "Debe registrar tipo de reporte, prioridad y descripcion minima."}, 400
        flash("Debe registrar tipo de reporte, prioridad y descripcion minima.", "error")
        return redirect(url_for("home") + "#reporte")

    nombre_unidad = data.get("unidad_gaula", "").strip()
    unidad = None
    if nombre_unidad:
        unidad = UnidadGaula.query.filter_by(nombre=nombre_unidad).first()
        if not unidad:
            unidad = UnidadGaula(nombre=nombre_unidad, created_by=session.get("user"))
            db.session.add(unidad)
            db.session.flush()

    caso = Caso(
        id_caso         = str(uuid.uuid4()),
        estado          = "Recibido",
        prioridad       = prioridad,
        tipo_caso       = tipo_caso,
        canal_recepcion = data.get("canal_recepcion", "").strip(),
        unidad_gaula_id = unidad.id if unidad else None,
        descripcion     = descripcion,
        observaciones   = data.get("observaciones", "").strip(),
        created_by      = session.get("user"),
    )
    db.session.add(caso)
    db.session.flush()

    nombre_rep = data.get("nombre_reportante", "").strip()
    if nombre_rep or data.get("documento_reportante") or data.get("telefono_reportante"):
        rep = Reportante(
            nombre     = nombre_rep,
            documento  = data.get("documento_reportante", "").strip(),
            telefono   = data.get("telefono_reportante", "").strip(),
            anonimo    = not bool(nombre_rep),
            created_by = session.get("user"),
        )
        db.session.add(rep)
        db.session.flush()
        db.session.add(CasoReportante(
            caso_id       = caso.id,
            reportante_id = rep.id,
            rol_en_caso   = "denunciante",
            created_by    = session.get("user"),
        ))

    medio = data.get("medio_pago", "").strip()
    if medio:
        raw = data.get("valor_exigido", "0").strip().replace(",", "").replace("$", "") or "0"
        try:
            valor_decimal = float(raw)
        except ValueError:
            valor_decimal = 0.0
        db.session.add(MedioPago(
            caso_id       = caso.id,
            tipo          = medio,
            valor_exigido = valor_decimal,
            referencia    = data.get("numero_extorsivo", "").strip(),
            created_by    = session.get("user"),
        ))

    evidencia_txt = data.get("evidencia", "").strip()
    if evidencia_txt:
        db.session.add(Evidencia(
            caso_id     = caso.id,
            tipo        = "referencia",
            descripcion = evidencia_txt,
            created_by  = session.get("user"),
        ))

    db.session.add(EventoCaso(
        caso_id      = caso.id,
        tipo_evento  = "creacion",
        descripcion  = "Caso registrado desde formulario.",
        estado_nuevo = "Recibido",
        created_by   = session.get("user"),
    ))

    db.session.commit()

    if request.is_json:
        return {"mensaje": f"Reporte registrado. Codigo: {caso.id_caso}", "id_reporte": caso.id_caso}, 201
    flash(f"Reporte registrado correctamente. Codigo interno: {caso.id_caso}", "ok")
    return redirect(url_for("home") + "#reporte")
```

- [ ] **Step 11.3: Reemplazar la funcion `dashboard`**

```python
@nexo.route("/dashboard")
@director_required
def dashboard():
    casos = Caso.query.order_by(Caso.fecha_registro.desc()).all()

    total          = len(casos)
    casos_criticos = sum(1 for c in casos if (c.prioridad or "").lower() == "critica")

    tipos_conteo = {}
    for c in casos:
        tipo = c.tipo_caso or "Sin clasificar"
        tipos_conteo[tipo] = tipos_conteo.get(tipo, 0) + 1

    if not tipos_conteo:
        tipos_conteo = {
            "Extorsion": 18, "Hurto": 11, "Fraude digital": 9,
            "Amenaza": 7,    "Secuestro": 3,
        }

    max_tipo = max(tipos_conteo.values()) if tipos_conteo else 1
    tipos = [
        {"tipo": t, "cantidad": n, "porcentaje": f"{int((n / max_tipo) * 100)}%"}
        for t, n in tipos_conteo.items()
    ]

    stats = {
        "casos_activos":     total if total else 48,
        "casos_criticos":    casos_criticos if total else 12,
        "gaulas_conectados": 34,
        "tiempo_respuesta":  "08m",
        "reportes_147":      total if total else 124,
        "alertas_osint":     19,
    }

    return render_template("dashboard.html", reportes=casos, stats=stats, tipos=tipos)
```

- [ ] **Step 11.4: Verificar que Flask arranca sin errores**

```bash
python -c "from app import nexo; print('OK')"
```

Salida esperada: `OK`

- [ ] **Step 11.5: Commit**

```bash
git add app.py
git commit -m "feat: actualizar rutas app.py para usar modelo Caso normalizado"
```

---

## Task 12: Actualizar `seed_db` y smoke test final

**Files:**
- Modify: `app.py`

- [ ] **Step 12.1: Reemplazar `seed_db` en `app.py`**

```python
def seed_db():
    with nexo.app_context():
        db.create_all()

        if Usuario.query.count() == 0:
            for username, pwd, nombre, rol in [
                ("admin",    "Admin147*",    "Administrador NEXO-147", "admin"),
                ("director", "Director147*", "Director GAULA",         "director"),
                ("analista", "Analista147*", "Analista Operacional",   "analista"),
                ("operador", "Operador147*", "Operador Linea 147",     "operador"),
            ]:
                db.session.add(Usuario(
                    username=username,
                    password_hash=generate_password_hash(pwd),
                    nombre=nombre,
                    rol=rol,
                    created_by="seed",
                ))
            db.session.commit()

        if UnidadGaula.query.count() == 0:
            for nombre, ciudad, depto in [
                ("GAULA Bogota D.C.",  "Bogota",       "Cundinamarca"),
                ("GAULA Medellin",     "Medellin",     "Antioquia"),
                ("GAULA Cali",         "Cali",         "Valle del Cauca"),
                ("GAULA Barranquilla", "Barranquilla", "Atlantico"),
                ("GAULA Bucaramanga",  "Bucaramanga",  "Santander"),
            ]:
                db.session.add(UnidadGaula(
                    nombre=nombre, ciudad=ciudad,
                    departamento=depto, created_by="seed",
                ))
            db.session.commit()
```

- [ ] **Step 12.2: Verificar arranque completo**

```bash
python -c "
import os
os.makedirs('data', exist_ok=True)
from app import nexo, db, seed_db
seed_db()
print('seed_db OK')
"
```

Salida esperada: `seed_db OK`

- [ ] **Step 12.3: Ejecutar suite completa**

```bash
pytest tests/ -v --tb=short
```

Salida esperada:

```
tests/test_migration.py         2 passed
tests/test_intel_models.py     11 passed
tests/test_nexo147_models.py    9 passed
tests/test_osint_models.py      5 passed
```

- [ ] **Step 12.4: Smoke test manual**

```bash
python app.py
```

Abrir `http://localhost:5000`, ingresar con `operador` / `Operador147*`, registrar un reporte de prueba, luego ingresar con `director` / `Director147*` y verificar que aparece en el dashboard.

- [ ] **Step 12.5: Commit final**

```bash
git add app.py
git commit -m "feat: actualizar seed_db con UnidadGaula y completar rediseno DB NEXO-147"
```

---

## Checklist de requisitos cubiertos

| Requisito del spec | Task |
|---|---|
| SQLALCHEMY_BINDS tres bases | Task 1 |
| nexo147.db 8 tablas normalizadas | Tasks 2-5 |
| intel.db 10 entidades | Task 6 |
| intel.db 14 tablas M:M | Task 7 |
| intel.db grafo nodes/edges + hallazgos | Task 8 |
| osint.db 5 tablas | Task 9 |
| Migracion automatica reportes -> nueva estructura | Task 10 |
| Rutas app.py actualizadas | Task 11 |
| seed_db con UnidadGaula | Task 12 |
| Campos de auditoria en todas las tablas | Tasks 2-9 |
| Indices en campos de busqueda frecuente | Tasks 3, 6, 8, 9 |
