"""Integration fixtures: a session factory bound to the real TimescaleDB (skips if absent)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.data.storage.db import create_db_engine, create_session_factory
from app.data.storage.orm import Base


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_db_engine()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("TimescaleDB not reachable — start it with `make dev`")

    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:  # start each test from a clean slate
        session.execute(text("TRUNCATE price_bars, fundamentals, data_quality_reports"))
        session.commit()

    yield factory
    engine.dispose()
