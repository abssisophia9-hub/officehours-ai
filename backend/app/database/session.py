"""
SQLAlchemy engine/session setup.
"""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./officehours.db")

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if DATABASE_URL == "sqlite:///:memory:":
        engine_kwargs["poolclass"] = StaticPool
else:
    # Postgres / other hosts: recycle dead connections.
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = int(os.getenv("OFFICEHOURS_DB_POOL_SIZE") or "5")
    engine_kwargs["max_overflow"] = int(os.getenv("OFFICEHOURS_DB_MAX_OVERFLOW") or "10")

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
