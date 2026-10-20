import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Railway sets DATABASE_URL automatically for PostgreSQL.
# Local dev falls back to SQLite.
_DATABASE_URL = os.getenv("DATABASE_URL")

if _DATABASE_URL:
    # Railway sometimes uses postgres:// — SQLAlchemy requires postgresql://
    if _DATABASE_URL.startswith("postgres://"):
        _DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(_DATABASE_URL)
else:
    def _get_db_path() -> str:
        if getattr(sys, 'frozen', False):
            return os.path.join(os.path.dirname(sys.executable), 'gava_leads.db')
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gava_leads.db')

    engine = create_engine(
        f"sqlite:///{_get_db_path()}",
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
