# modules/extensions.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

db = SQLAlchemy()


def _set_sqlite_pragmas(dbapi_conn, _):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.fetchone()  # consume result row; WAL silently ignored on :memory: databases
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA cache_size=10000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


if not event.contains(Engine, "connect", _set_sqlite_pragmas):
    event.listen(Engine, "connect", _set_sqlite_pragmas)
