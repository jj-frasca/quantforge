"""OHLCVNormalizer: adj_factor = adj_close/close applied once, split scaling, UTC preserved, non-positive close rejected, empty input."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.data.normalizers.ohlcv import OHLCVNormalizer, RawBar


def _raw(**overrides: object) -> RawBar:
    base: dict[str, object] = {
        "timestamp": datetime(2024, 1, 2, tzinfo=UTC),
        "open": 100.0,
        "high": 110.0,
        "low": 95.0,
        "close": 100.0,
        "adj_close": 100.0,
        "volume": 1000,
    }
    base.update(overrides)
    return RawBar(**base)  # type: ignore[arg-type]


def test_normalizer_unadjusted_bar_keeps_prices_and_factor_one() -> None:
    bars = OHLCVNormalizer().normalize([_raw()], "aapl", "yfinance")
    assert len(bars) == 1
    bar = bars[0]
    assert bar.symbol == "AAPL"
    assert bar.adj_factor == Decimal("1")
    assert bar.open == Decimal("100")
    assert bar.close == Decimal("100")
    assert bar.source == "yfinance"


def test_normalizer_applies_split_adjustment_factor() -> None:
    # 2:1 split: adj_close is half of raw close -> factor 0.5, all OHLC scaled down.
    bars = OHLCVNormalizer().normalize([_raw(adj_close=50.0)], "AAPL", "yfinance")
    bar = bars[0]
    assert bar.adj_factor == Decimal("0.5")
    assert bar.open == Decimal("50")
    assert bar.high == Decimal("55")
    assert bar.low == Decimal("47.5")
    assert bar.close == Decimal("50")  # adjusted close == adj_close


def test_normalizer_preserves_utc_timestamp() -> None:
    bars = OHLCVNormalizer().normalize([_raw()], "AAPL", "yfinance")
    assert bars[0].timestamp_utc == datetime(2024, 1, 2, tzinfo=UTC)


def test_normalizer_non_positive_close_raises() -> None:
    with pytest.raises(ValueError, match="close"):
        OHLCVNormalizer().normalize([_raw(close=0.0)], "AAPL", "yfinance")


def test_normalizer_empty_input_returns_empty() -> None:
    assert OHLCVNormalizer().normalize([], "AAPL", "yfinance") == []
