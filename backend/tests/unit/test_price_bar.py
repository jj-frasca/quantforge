"""PriceBar model: UTC coercion (naive rejected), positive prices, OHLC ordering, and the Hypothesis invariant that valid prices are finite and positive."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.data.models.price_bar import PriceBar


def _bar(**overrides: object) -> PriceBar:
    base: dict[str, object] = {
        "symbol": "AAPL",
        "timestamp_utc": datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
        "open": Decimal("100.0"),
        "high": Decimal("105.0"),
        "low": Decimal("99.0"),
        "close": Decimal("104.0"),
        "volume": 1_000_000,
        "adj_factor": Decimal("1.0"),
        "source": "yfinance",
    }
    base.update(overrides)
    return PriceBar(**base)  # type: ignore[arg-type]


def test_price_bar_valid_bar_constructs() -> None:
    bar = _bar()
    assert bar.symbol == "AAPL"
    assert bar.quality_flags is None


def test_price_bar_symbol_is_uppercased_and_stripped() -> None:
    assert _bar(symbol="  aapl ").symbol == "AAPL"


def test_price_bar_empty_symbol_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _bar(symbol="   ")


def test_price_bar_naive_timestamp_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _bar(timestamp_utc=datetime(2024, 1, 2, 14, 30))


def test_price_bar_non_utc_timestamp_is_coerced_to_utc() -> None:
    est = timezone(timedelta(hours=-5))
    bar = _bar(timestamp_utc=datetime(2024, 1, 2, 9, 30, tzinfo=est))
    assert bar.timestamp_utc.utcoffset() == timedelta(0)
    assert bar.timestamp_utc == datetime(2024, 1, 2, 14, 30, tzinfo=UTC)


def test_price_bar_negative_price_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _bar(open=Decimal("-1.0"))


def test_price_bar_zero_price_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _bar(close=Decimal("0"))


def test_price_bar_nan_price_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _bar(high=Decimal("NaN"))


def test_price_bar_high_below_open_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _bar(high=Decimal("103.0"), open=Decimal("104.0"))


def test_price_bar_low_above_close_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _bar(low=Decimal("104.5"), close=Decimal("104.0"))


def test_price_bar_negative_volume_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _bar(volume=-1)


def test_price_bar_non_positive_adj_factor_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        _bar(adj_factor=Decimal("0"))


_valid_price = st.decimals(
    min_value=Decimal("0.000001"),
    max_value=Decimal("100000"),
    allow_nan=False,
    allow_infinity=False,
    places=6,
)


@given(
    p1=_valid_price,
    p2=_valid_price,
    vol=st.integers(min_value=0, max_value=10**12),
    adj=_valid_price,
)
def test_price_bar_valid_ohlc_prices_are_finite_and_positive(
    p1: Decimal, p2: Decimal, vol: int, adj: Decimal
) -> None:
    # §8 invariant #1: all normalized prices are finite and positive.
    low, high = sorted((p1, p2))
    bar = _bar(open=p1, high=high, low=low, close=p2, volume=vol, adj_factor=adj)
    for px in (bar.open, bar.high, bar.low, bar.close, bar.adj_factor):
        assert px.is_finite()
        assert px > 0
    assert bar.low <= bar.open <= bar.high
    assert bar.low <= bar.close <= bar.high


@given(bad=st.decimals(max_value=Decimal("0"), allow_nan=False, allow_infinity=False, places=6))
def test_price_bar_non_positive_price_is_always_rejected(bad: Decimal) -> None:
    with pytest.raises(ValidationError):
        _bar(open=bad, high=Decimal("10"), low=Decimal("1"), close=Decimal("5"))
