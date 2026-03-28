"""
db/session.py

Sets up the SQLAlchemy engine and session factory.
Import `get_db` in routers to get a database session per request.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

# The engine is the core interface to the database.
# check_same_thread=False is required for SQLite to work with FastAPI.
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

# Each request gets its own session, which is closed when the request ends.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class that all database models will inherit from."""
    pass


def get_db():
    """
    FastAPI dependency that provides a database session per request.
    Usage in a router:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
