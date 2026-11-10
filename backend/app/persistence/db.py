"""SQLAlchemy engine (SQLite WAL, Postgres-compatible types)."""

from typing import Any

from sqlalchemy import Engine
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker


def get_engine(url: str = "sqlite:///data/vendorgate.db") -> Engine:
    engine = create_engine(url, future=True)

    @event.listens_for(engine, "connect")
    def _wal(dbapi_conn: Any, _rec: Any) -> None:
        try:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()
        except Exception:
            pass

    return engine


SessionLocal = sessionmaker(future=True)
