"""Timescale repository validation behavior that does not require a database."""

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from pydantic import ValidationError
from tests.fixtures.synthetic import builders

from app.data.models import DataQualityReport
from app.data.storage.timescale import TimescaleDBPriceBarRepository


def test_save_quality_report_revalidates_before_opening_session() -> None:
    def unexpected_session() -> None:
        raise AssertionError("database session opened before report validation")

    repo = TimescaleDBPriceBarRepository(cast(Any, unexpected_session))
    report = DataQualityReport(symbol="AAPL", checked_at=datetime(2024, 1, 2, tzinfo=UTC))
    invalid = report.model_copy(update={"symbol": " "})

    with pytest.raises(ValidationError):
        repo.save_quality_report(invalid)


def test_save_bars_revalidates_complete_batch_before_opening_session() -> None:
    def unexpected_session() -> None:
        raise AssertionError("database session opened before complete batch validation")

    repo = TimescaleDBPriceBarRepository(cast(Any, unexpected_session))
    valid = builders.clean_series(n=1)[0]
    invalid = valid.model_copy(update={"volume": -1})

    with pytest.raises(ValidationError):
        repo.save_bars([valid, invalid])
