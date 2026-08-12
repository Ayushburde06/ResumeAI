import os
import ssl
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# Ensure the database is created in the backend directory regardless of cwd
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "resumeai.db"
_is_production = os.environ.get("ENV", "development").lower() == "production"
_database_mode = os.environ.get(
    "DATABASE_MODE",
    "postgres" if _is_production else "sqlite",
).strip().lower()

if _database_mode == "sqlite":
    # Local development remains usable even when .env contains a production
    # DATABASE_URL. PostgreSQL is opt-in outside production.
    DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH}"
elif _database_mode in {"postgres", "postgresql"}:
    DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required when DATABASE_MODE=postgres.")
else:
    raise RuntimeError("DATABASE_MODE must be 'sqlite' or 'postgres'.")

# ── Production-grade connection pooling ─────────────────────────────────────
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30.0,
        },
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30.0,
        pool_recycle=1800,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()

else:
    # PostgreSQL — pg8000 requires an actual ssl.SSLContext for Aiven / managed PG
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE

    engine = create_engine(
        DATABASE_URL,
        connect_args={"ssl_context": _ssl_ctx},
        pool_pre_ping=True,
        pool_size=20 if _is_production else 10,
        max_overflow=30 if _is_production else 20,
        pool_timeout=30.0,
        pool_recycle=1800,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
