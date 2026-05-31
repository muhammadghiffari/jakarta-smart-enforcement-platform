# services/api/app/database.py
# SQLAlchemy engine + session factory for JSEP
# Reads all connection params from environment (PRD RULE-01)

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

POSTGRES_URL = (
    os.getenv("DATABASE_URL")
    or "postgresql://{user}:{pw}@{host}:{port}/{db}".format(
        user = os.getenv("POSTGRES_USER",     "jsep_user"),
        pw   = os.getenv("POSTGRES_PASSWORD", "jsep_local_dev"),
        host = os.getenv("POSTGRES_HOST",     "localhost"),
        port = os.getenv("POSTGRES_PORT",     "5432"),
        db   = os.getenv("POSTGRES_DB",       "jsep"),
    )
)

engine = create_engine(
    POSTGRES_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> bool:
    """Health check helper."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
