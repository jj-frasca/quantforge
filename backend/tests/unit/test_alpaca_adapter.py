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


def test_fetch_price_bars_excludes_a_bar_at_or_after_the_exclusive_end() -> None:
    # FINDING-055/ADR-127: Alpaca's `end` query param is documented as INCLUSIVE, but
    # DataSourceAdapter.fetch_price_bars promises the half-open [start, end) contract every other
    # adapter and DataQualityEngine's range_mismatch check (ADR-119) enforce. `_fetch_bars` passes
    # `end.date().isoformat()` straight through with no adjustment, so a real Alpaca response can
    # include a bar dated ON the caller's exclusive `end` boundary. Simulate that vendor behavior
    # via the injected fetcher (which bypasses the untested network glue) and assert the adapter's
    # OWN output still honors the documented contract regardless of what the vendor returns.
    bars_including_end_boundary = [
        *_BARS,
        {"t": "2024-02-01T05:00:00Z", "o": 103.0, "h": 105.0, "l": 102.0, "c": 104.0, "v": 800},
    ]
    adapter = AlpacaDataAdapter("key", "secret", fetcher=_fetcher(bars_including_end_boundary))
    bars = adapter.fetch_price_bars(
        "AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)
    )
    assert len(bars) == 3
    assert all(b.timestamp_utc < datetime(2024, 2, 1, tzinfo=UTC) for b in bars)


def test_a_vendor_fetch_error_is_normalized_to_oserror() -> None:
    # FINDING-056/ADR-128: this adapter's own docstring claims "same pattern as YFinanceAdapter",
    # but had no exception normalization at all — any vendor-specific fetch/parse error (a
    # urllib.error.HTTPError, a malformed payload's KeyError on a missing "t"/"o" field, a
    # decimal.InvalidOperation from a NaN price) would propagate as-is instead of becoming the
    # OSError the rest of this codebase's resilient callers are written to expect. Mirrors
    # test_yfinance_adapter.py's equivalent regression test.
    class _AlpacaRateLimitError(Exception):
        pass

    def _raises(symbol: str, start: datetime, end: datetime) -> list[dict]:
        raise _AlpacaRateLimitError("429 Too Many Requests")

    adapter = AlpacaDataAdapter("key", "secret", fetcher=_raises)
    with pytest.raises(OSError, match="fetch failed"):
        adapter.fetch_price_bars(
            "AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)
        )


def test_a_malformed_vendor_payload_is_not_double_wrapped() -> None:
    # A missing field is a KeyError, which — like ValueError/OSError — is already "a kind the
    # resilient hunt handles" per this codebase's convention (mirrors yfinance's equivalent test);
    # it propagates as-is rather than getting wrapped a second time into OSError.
    def _missing_field(symbol: str, start: datetime, end: datetime) -> list[dict]:
        return [
            {"t": "2024-01-02T05:00:00Z", "o": 100.0, "h": 101.0, "l": 99.0, "v": 1000}
        ]  # no "c"

    adapter = AlpacaDataAdapter("key", "secret", fetcher=_missing_field)
    with pytest.raises(KeyError):
        adapter.fetch_price_bars(
            "AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)
        )


def test_a_value_error_from_the_fetcher_is_not_double_wrapped() -> None:
    def _raises(symbol: str, start: datetime, end: datetime) -> list[dict]:
        raise ValueError("no data for symbol")

    adapter = AlpacaDataAdapter("key", "secret", fetcher=_raises)
    with pytest.raises(ValueError, match="no data for symbol"):
        adapter.fetch_price_bars(
            "AAPL", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC)
        )


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
