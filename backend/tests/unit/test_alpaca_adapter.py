"""Alpaca daily-bar data adapter (ADR-019 follow-on). The HTTP glue is injectable so bar-mapping
+ normalization are unit-tested without network; the real pull is a @pytest.mark.live test that
needs Joe's free Alpaca key. Chosen for cloud reliability (yfinance is flaky from cloud IPs)."""

import os
from datetime import UTC, datetime

import pytest

from app.data.models.price_bar import PriceBar
from app.data.sources.alpaca import AlpacaDataAdapter

_BARS = [
    {"t": "2024-01-02T05:00:00Z", "o": 100.0, "h": 102.0, "l": 99.0, "c": 101.0, "v": 1000},
    {"t": "2024-01-03T05:00:00Z", "o": 101.0, "h": 103.5, "l": 100.5, "c": 102.5, "v": 1200},
    {"t": "2024-01-04T05:00:00Z", "o": 102.5, "h": 104.0, "l": 101.0, "c": 103.0, "v": 900},
]


def _fetcher(bars: list[dict]):
    def fetch(symbol: str, start: datetime, end: datetime) -> list[dict]:
        return bars

    return fetch


def test_fetch_price_bars_maps_and_normalizes_alpaca_bars() -> None:
    adapter = AlpacaDataAdapter("key", "secret", fetcher=_fetcher(_BARS))
    bars = adapter.fetch_price_bars(
        "AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)
    )
    assert len(bars) == 3
    assert all(isinstance(b, PriceBar) for b in bars)
    assert float(bars[0].close) == 101.0
    assert float(bars[-1].high) == 104.0
    # Timestamps are UTC and ascending.
    assert [b.timestamp_utc for b in bars] == sorted(b.timestamp_utc for b in bars)
    assert bars[0].timestamp_utc.tzinfo is not None


def test_empty_result_is_empty_list() -> None:
    adapter = AlpacaDataAdapter("key", "secret", fetcher=_fetcher([]))
    assert (
        adapter.fetch_price_bars(
            "AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)
        )
        == []
    )


@pytest.mark.live
def test_live_alpaca_fetch() -> None:
    key, secret = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        pytest.skip("ALPACA_API_KEY / ALPACA_SECRET_KEY not set")
    adapter = AlpacaDataAdapter(key, secret)
    bars = adapter.fetch_price_bars(
        "AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 3, 1, tzinfo=UTC)
    )
    assert len(bars) > 20
    assert all(b.close > 0 for b in bars)
