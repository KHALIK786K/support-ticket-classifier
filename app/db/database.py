"""
SQLAlchemy engine + session factory.

Production note: connection pooling matters — see `pool_size` and
`max_overflow`. The values below are tuned for ~4 Gunicorn workers per pod.
"""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()

engine = create_engine(
    settings.mysql_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
