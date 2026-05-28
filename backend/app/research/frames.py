import pandas as pd

from app.data.models import PriceBar

_COLUMNS = ["open", "high", "low", "close", "volume"]


def bars_to_frame(bars: list[PriceBar]) -> pd.DataFrame:
    """Convert canonical PriceBars to a price frame for the research engine.

    Index is a tz-aware UTC DatetimeIndex (ascending); columns are float OHLCV. The
    Decimal -> float conversion happens here, once: the vectorized engine works in float,
    while Decimal remains the storage/contract type (backtesting-spec.md §1).
    """
    if not bars:
        return pd.DataFrame(
            {col: pd.Series(dtype="float64") for col in _COLUMNS},
            index=pd.DatetimeIndex([], tz="UTC"),
        )

    ordered = sorted(bars, key=lambda b: b.timestamp_utc)
    return pd.DataFrame(
        {
            "open": [float(b.open) for b in ordered],
            "high": [float(b.high) for b in ordered],
            "low": [float(b.low) for b in ordered],
            "close": [float(b.close) for b in ordered],
            "volume": [float(b.volume) for b in ordered],
        },
        index=pd.DatetimeIndex([b.timestamp_utc for b in ordered], name="timestamp_utc"),
    )
