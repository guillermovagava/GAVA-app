import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _get_db_path() -> str:
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller .exe — store DB next to the executable
        return os.path.join(os.path.dirname(sys.executable), 'gava_leads.db')
    # Development — store in the backend/ directory
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gava_leads.db')


SQLALCHEMY_DATABASE_URL = f"sqlite:///{_get_db_path()}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
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
