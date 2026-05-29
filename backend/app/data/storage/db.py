from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def create_db_engine(url: str | None = None) -> Engine:
    """Sync SQLAlchemy engine on the psycopg3 driver (ADR-009)."""
    return create_engine(url or get_settings().database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=engine or create_db_engine(), expire_on_commit=False)
