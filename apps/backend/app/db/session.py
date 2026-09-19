"""Database engine and session management for AstraTrace.

SIH 2026 | Problem ID: SIH26227
Supports PostgreSQL/PostGIS in production and SQLite for offline host testing.
"""
import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from apps.backend.app.config import settings
from apps.backend.app.core.logging import logger

Base = declarative_base()


def get_engine(database_url: str = None, is_readonly: bool = False):
    """Creates SQLAlchemy engine with appropriate dialect configurations."""
    url = database_url or settings.database_url

    # PostgreSQL dialect normalization (e.g. Vercel Postgres provides postgres:// or postgresql://)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    # SQLite configuration
    if url.startswith("sqlite:///"):
        import sqlite3
        import shutil
        from sqlalchemy.pool import StaticPool

        db_path = url.replace("sqlite:///", "").split("?")[0]
        is_ro = is_readonly or "mode=ro" in url or "immutable=1" in url or bool(os.environ.get("VERCEL"))

        found_path = None
        if db_path != ":memory:":
            p = Path(db_path)
            if not p.is_absolute():
                candidates = [
                    Path.cwd() / p,
                    Path(__file__).resolve().parents[2] / p,
                    Path(__file__).resolve().parents[3] / p,
                    Path(__file__).resolve().parents[4] / p,
                    Path("/var/task") / p,
                    Path("/var/task") / "apps" / "backend" / p,
                    Path("/var/task/..") / p,
                    Path.cwd() / "apps" / "backend" / p,
                    Path("/tmp") / p.name,
                ]
                for c in candidates:
                    try:
                        if c.is_file():
                            found_path = c.resolve()
                            break
                    except Exception:
                        pass
            elif p.is_file():
                found_path = p.resolve()

            if is_ro and found_path:
                tmp_db = Path("/tmp") / found_path.name
                try:
                    if not tmp_db.exists() or tmp_db.stat().st_size != found_path.stat().st_size:
                        shutil.copy2(found_path, tmp_db)
                    found_path = tmp_db
                except Exception:
                    pass
            elif not is_ro and not found_path and db_path != ":memory:":
                try:
                    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                except (OSError, PermissionError):
                    pass

        if found_path:
            posix_path = found_path.as_posix()
            conn_target = f"file:{posix_path}?mode=ro&immutable=1" if is_ro else posix_path
            use_uri = is_ro

            engine = create_engine(
                "sqlite://",
                creator=lambda: sqlite3.connect(conn_target, uri=use_uri, check_same_thread=False),
                echo=False,
            )
        else:
            # Fallback to shared in-memory SQLite database
            engine = create_engine(
                "sqlite://",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,
            )
            try:
                import apps.backend.app.models  # noqa: F401
                Base.metadata.create_all(bind=engine)
            except Exception:
                pass

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if not is_ro:
                try:
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.close()
                except Exception:
                    pass

        return engine

    # PostgreSQL configuration
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,
    )


# Catalog Engine (Read-only on Vercel/production when configured)
_catalog_url = settings.catalog_database_url or settings.database_url
catalog_engine = get_engine(_catalog_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=catalog_engine)

# State Engine (Durable PostgreSQL in production, falls back to catalog engine locally)
_state_url = settings.state_database_url.strip()
if _state_url:
    state_engine = get_engine(_state_url)
else:
    state_engine = catalog_engine
StateSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=state_engine)

# Backwards compatibility alias
engine = catalog_engine


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding catalog database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_state_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding persistent state database sessions."""
    db = StateSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine_instance=None):
    """Initializes all registered declarative tables in the database."""
    target_engine = engine_instance or state_engine
    logger.info(f"Initializing catalog database tables on engine: {target_engine.url.render_as_string(hide_password=True)}")
    # Ensure all declarative models are imported and registered with Base.metadata
    import apps.backend.app.models  # noqa: F401
    try:
        Base.metadata.create_all(bind=target_engine)
    except Exception as e:
        logger.warning(f"Database table initialization notice: {e}")

