"""Deterministic synthetic PriceBar series for exercising the DataQualityEngine.

Each builder returns canonical PriceBars (no network). `clean_series` is a healthy
business-day series; the mutators inject one specific defect that maps to a quality check
(see ARCHITECTURE.md §8). Determinism: fixed start date, fixed drift, no RNG.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.data.models import PriceBar, Source

_START = datetime(2024, 1, 2, tzinfo=UTC)


def _bar(
    symbol: str,
    ts: datetime,
    close: Decimal,
    adj_factor: Decimal = Decimal("1"),
    source: Source = "yfinance",
    volume: int = 1_000_000,
) -> PriceBar:
    return PriceBar(
        symbol=symbol,
        timestamp_utc=ts,
        open=close,
        high=(close * Decimal("1.01")).quantize(Decimal("0.000001")),
        low=(close * Decimal("0.99")).quantize(Decimal("0.000001")),
        close=close,
        volume=volume,
        adj_factor=adj_factor,
        source=source,
    )


def clean_series(
    symbol: str = "AAPL",
    n: int = 30,
    start: datetime = _START,
    start_price: Decimal = Decimal("100"),
) -> list[PriceBar]:
    """Healthy series: consecutive business days, mild upward drift, no defects."""
    bars: list[PriceBar] = []
    day = start
    price = start_price
    while len(bars) < n:
        if day.weekday() < 5:  # Mon-Fri
            bars.append(_bar(symbol, day, price.quantize(Decimal("0.000001"))))
            price = price * Decimal("1.001")
        day += timedelta(days=1)
    return bars


def with_missing_bars(
    bars: list[PriceBar], start_index: int = 10, length: int = 3
) -> list[PriceBar]:
    """Drop `length` consecutive bars -> a gap in the trading-day sequence (check 4)."""
    return bars[:start_index] + bars[start_index + length :]


def with_stale_prices(
    bars: list[PriceBar], start_index: int = 10, length: int = 5
) -> list[PriceBar]:
    """Freeze `length` consecutive closes to the same value (check 6)."""
    out = list(bars)
    frozen = out[start_index].close
    for i in range(start_index, min(start_index + length, len(out))):
        b = out[i]
        out[i] = _bar(b.symbol, b.timestamp_utc, frozen, b.adj_factor, b.source, b.volume)
    return out


def with_extreme_move(
    bars: list[PriceBar], index: int = 15, pct: Decimal = Decimal("-0.40")
) -> list[PriceBar]:
    """Replace one bar's close with a `pct` move from the prior close (check 5)."""
    out = list(bars)
    prev_close = out[index - 1].close
    new_close = (prev_close * (Decimal("1") + pct)).quantize(Decimal("0.000001"))
    b = out[index]
    out[index] = _bar(b.symbol, b.timestamp_utc, new_close, b.adj_factor, b.source, b.volume)
    return out


def with_split(
    bars: list[PriceBar], index: int = 15, factor: Decimal = Decimal("0.25")
) -> list[PriceBar]:
    """Set one bar's adj_factor far from its neighbour's -> an adj_factor jump (check 2)."""
    out = list(bars)
    b = out[index]
    out[index] = _bar(b.symbol, b.timestamp_utc, b.close, factor, b.source, b.volume)
    return out
