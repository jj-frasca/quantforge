"""Unit coverage for the /backtest benchmark-comparison helper (ADR-013): the degenerate
paths that the endpoint's happy-path integration tests can't reach."""

from datetime import datetime

import pandas as pd

from app.api.v1.backtest import _benchmark_comparison
from app.data.models import PriceBar
from app.data.sources.base import DataSourceAdapter
from app.data.storage.memory import InMemoryPriceBarRepository

_START = datetime(2024, 1, 1)
_END = datetime(2024, 6, 1)


class _NeverCalledAdapter(DataSourceAdapter):
    source = "yfinance"
    adapter_version = "unit-1"

    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        raise AssertionError("adapter should not be called on the SPY-reuse path")


def test_benchmark_comparison_none_when_series_do_not_overlap() -> None:
    # symbol == SPY reuses the passed close series (no fetch). Disjoint indices -> the
    # inner-join excess series is empty -> no meaningful comparison -> None.
    strategy_returns = pd.Series(0.001, index=pd.date_range("2024-01-01", periods=30, freq="B"))
    spy_close = pd.Series(100.0, index=pd.date_range("2025-01-01", periods=30, freq="B"))
    result = _benchmark_comparison(
        "SPY",
        _START,
        _END,
        _NeverCalledAdapter(),
        InMemoryPriceBarRepository(),
        strategy_returns,
        spy_close,
    )
    assert result is None
