"""Database engine and session management for AstraTrace.

SIH 2026 | Problem ID: SIH26227
Supports PostgreSQL/PostGIS in production and SQLite for offline host testing.
"""
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from apps.backend.app.config import settings
from apps.backend.app.core.logging import logger

Base = declarative_base()


def get_engine(database_url: str = None):
    """Creates SQLAlchemy engine with appropriate dialect configurations."""
    url = database_url or settings.database_url

    # Ensure parent directory exists for SQLite file paths
    if url.startswith("sqlite:///"):
        db_path = url.replace("sqlite:///", "")
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

        # Enforce foreign key constraints and WAL mode in SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        return engine

    # PostgreSQL configuration
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,
    )


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine_instance=None):
    """Initializes all registered declarative tables in the database."""
    target_engine = engine_instance or engine
    logger.info(f"Initializing catalog database tables on engine: {target_engine.url.render_as_string(hide_password=True)}")
    # Ensure all declarative models are imported and registered with Base.metadata
    import apps.backend.app.models  # noqa: F401
    Base.metadata.create_all(bind=target_engine)
