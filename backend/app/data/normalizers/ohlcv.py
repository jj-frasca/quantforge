from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.data.models import PriceBar, Source

_Q6 = Decimal("0.000001")


@dataclass(frozen=True)
class RawBar:
    """Vendor-agnostic raw OHLCV row, before adjustment to the canonical PriceBar.

    Adapters produce these (the only place vendor wire formats live); the normalizer turns
    them into canonical PriceBars. ``close``/``adj_close`` are the unadjusted and
    adjusted closes — their ratio is the cumulative split/dividend factor.
    """

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int


def _to_decimal(value: float) -> Decimal:
    # via str so we don't inherit binary-float artifacts
    return Decimal(str(value))


def _scaled(raw_price: float, factor: Decimal) -> Decimal:
    return (_to_decimal(raw_price) * factor).quantize(_Q6)


class OHLCVNormalizer:
    """Converts raw OHLCV rows into canonical, split/dividend-adjusted PriceBars (ADR-004).

    Notes:
        The adjustment factor is adj_close / close, applied once here at ingestion. The
        adjusted close equals adj_close by construction; O/H/L are scaled by the same factor,
        so OHLC ordering is preserved.
    """

    def normalize(self, raw: list[RawBar], symbol: str, source: Source) -> list[PriceBar]:
        bars: list[PriceBar] = []
        for row in raw:
            if row.close <= 0:
                raise ValueError("raw close must be > 0 to compute the adjustment factor")
            factor = (_to_decimal(row.adj_close) / _to_decimal(row.close)).quantize(_Q6)
            bars.append(
                PriceBar(
                    symbol=symbol,
                    timestamp_utc=row.timestamp,
                    open=_scaled(row.open, factor),
                    high=_scaled(row.high, factor),
                    low=_scaled(row.low, factor),
                    close=_to_decimal(row.adj_close).quantize(_Q6),
                    volume=row.volume,
                    adj_factor=factor,
                    source=source,
                )
            )
        return bars
