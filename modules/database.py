"""Database configuration with safe SQLite defaults."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from modules.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./careeros.db")
url = make_url(DATABASE_URL)
is_sqlite = url.get_backend_name() == "sqlite"

# FastAPI runs sync endpoints in a threadpool, so SQLite connections cross
# threads. `timeout` is SQLite's busy handler: how many seconds a writer waits
# for the lock before raising "database is locked".
connect_args = {"check_same_thread": False, "timeout": 15} if is_sqlite else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


if is_sqlite:

    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, connection_record) -> None:
        """Per-connection pragmas, applied once per new DBAPI connection."""
        cursor = dbapi_connection.cursor()
        # Foreign keys default to OFF in SQLite and are per-connection, so
        # cascades only work if this runs on every connection.
        cursor.execute("PRAGMA foreign_keys=ON")
        # WAL lets readers proceed while a write is in flight. Persists in the
        # database file; re-asserting is idempotent. Drop this line on network
        # filesystems (NFS/SMB), where WAL is unsafe.
        cursor.execute("PRAGMA journal_mode=WAL")
        # Standard WAL companion: durable across app crashes, not power loss.
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
