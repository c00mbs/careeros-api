"""Database configuration with safe SQLite defaults."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from modules.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./careeros.db")
url = make_url(DATABASE_URL)
connect_args = {"check_same_thread": False} if url.get_backend_name() == "sqlite" else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Keep SQLite foreign-key cascades enabled for each connection.
if url.get_backend_name() == "sqlite":
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
