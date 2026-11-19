"""SQLAlchemy engine / session factory cho SQLite."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BASE_DIR, settings

_url = settings.resolved_database_url
_connect_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}

engine: Engine = create_engine(
    _url,
    connect_args=_connect_args,
    future=True,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record) -> None:  # pragma: no cover - hạ tầng
    """Bật khóa ngoại + WAL để đảm bảo toàn vẹn dữ liệu và đọc/ghi song song."""
    if not _url.startswith("sqlite"):
        return
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: một session cho mỗi request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_path_from_url(url: str | None = None) -> Path | None:
    url = url or _url
    if not url.startswith("sqlite"):
        return None
    raw = url.split("///", 1)[-1]
    p = Path(raw)
    return p if p.is_absolute() else (BASE_DIR / p)
