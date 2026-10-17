from typing import Any

import pandas as pd

from app.data.models import PriceBar

_COLUMNS = ["open", "high", "low", "close", "volume"]


def _copy_axis(axis: "pd.Index[Any]") -> "pd.Index[Any]":
    """Copy numeric axis storage, including categorical definitions (ADR-306)."""
    if isinstance(axis, pd.CategoricalIndex):
        categorical = pd.Categorical.from_codes(
            axis.codes.copy(), categories=_copy_axis(axis.categories), ordered=axis.ordered
        )
        return pd.CategoricalIndex(categorical, name=axis.name)
    if isinstance(axis, pd.MultiIndex):
        return axis.copy(deep=True).set_levels(
            [_copy_axis(level) for level in axis.levels], verify_integrity=False
        )
    return axis.copy(deep=True)


def copy_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Isolate canonical numeric data and axes, including pandas' shared index storage."""
    copied = frame.copy(deep=True)
    copied.index = _copy_axis(frame.index)
    copied.columns = _copy_axis(frame.columns)
    return copied


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
