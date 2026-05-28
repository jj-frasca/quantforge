from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.data.models import PriceBar
from app.data.sources.base import DataSourceAdapter


class _StubAdapter(DataSourceAdapter):
    source = "yfinance"
    adapter_version = "stub-1"

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        return [
            PriceBar(
                symbol=symbol,
                timestamp_utc=start,
                open=Decimal("10"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10.5"),
                volume=100,
                adj_factor=Decimal("1"),
                source=self.source,
            )
        ]


def test_data_source_adapter_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        DataSourceAdapter()  # type: ignore[abstract]


def test_concrete_adapter_returns_canonical_price_bars() -> None:
    adapter = _StubAdapter()
    start = datetime(2024, 1, 2, tzinfo=UTC)
    bars = adapter.fetch_price_bars("aapl", start, datetime(2024, 1, 3, tzinfo=UTC))
    assert len(bars) == 1
    assert isinstance(bars[0], PriceBar)
    assert bars[0].symbol == "AAPL"
    assert bars[0].source == "yfinance"


def test_concrete_adapter_exposes_source_and_version() -> None:
    adapter = _StubAdapter()
    assert adapter.source == "yfinance"
    assert adapter.adapter_version == "stub-1"
