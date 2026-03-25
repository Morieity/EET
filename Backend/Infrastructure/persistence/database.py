"""SQLAlchemy engine, declarative Base, and scoped session factory."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    scoped_session,
    sessionmaker,
)

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///db/diagnosis.db",
)

_is_sqlite = DATABASE_URL.startswith("sqlite")

# Ensure parent directory exists for SQLite file-based databases
if _is_sqlite:
    db_path = DATABASE_URL.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

# Enable WAL mode and foreign keys for SQLite
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionFactory = sessionmaker(bind=engine)
ScopedSession = scoped_session(SessionFactory)


class Base(DeclarativeBase):
    pass


def get_session() -> Session:
    """返回一个新的数据库 session。"""
    return ScopedSession()


def init_db() -> None:
    """创建所有表（开发便捷方法，生产环境应使用 Alembic）。"""
    import Backend.Infrastructure.persistence.models.session_model  # noqa: F401
    import Backend.Infrastructure.persistence.models.fault_tree_model  # noqa: F401
    Base.metadata.create_all(bind=engine)
