"""NarrowRangeBreakoutStrategy: param validation; volatility-contraction breakout — after the
narrowest-range bar in N, trade the direction it breaks; signals in {-1, 0, 1}; no look-ahead."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.narrow_range_breakout import NarrowRangeBreakoutStrategy


def _ohlc(highs: list[float], lows: list[float], closes: list[float]) -> pd.DataFrame:
    idx = pd.RangeIndex(len(closes))
    return pd.DataFrame(
        {
            "open": pd.Series(closes, index=idx, dtype="float64"),
            "high": pd.Series(highs, index=idx, dtype="float64"),
            "low": pd.Series(lows, index=idx, dtype="float64"),
            "close": pd.Series(closes, index=idx, dtype="float64"),
            "volume": pd.Series(1_000_000.0, index=idx),
        },
        index=idx,
    )


def _wide(n: int) -> tuple[list[float], list[float], list[float]]:
    # n wide-range bars (range 4) around a flat 100 close.
    return [102.0] * n, [98.0] * n, [100.0] * n


def test_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="window"):
        NarrowRangeBreakoutStrategy(window=1)


def test_has_real_citation() -> None:
    assert any("Crabel" in c for c in NarrowRangeBreakoutStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert NarrowRangeBreakoutStrategy(window=7).parameters == {"window": 7}


def test_long_on_upside_break_after_narrow_bar() -> None:
    highs, lows, closes = _wide(8)
    highs += [100.2, 103.5]  # bar 8 narrow (range 0.4), bar 9 breaks up
    lows += [99.8, 102.5]
    closes += [100.0, 103.0]  # close[9]=103 > narrow bar high 100.2 -> long
    signals = NarrowRangeBreakoutStrategy(window=7).generate_signals(_ohlc(highs, lows, closes))
    assert signals.iloc[-1] == 1.0


def test_short_on_downside_break_after_narrow_bar() -> None:
    highs, lows, closes = _wide(8)
    highs += [100.2, 97.5]
    lows += [99.8, 96.5]
    closes += [100.0, 97.0]  # close[9]=97 < narrow bar low 99.8 -> short
    signals = NarrowRangeBreakoutStrategy(window=7).generate_signals(_ohlc(highs, lows, closes))
    assert signals.iloc[-1] == -1.0


def test_flat_when_no_break_after_narrow_bar() -> None:
    highs, lows, closes = _wide(8)
    highs += [100.2, 100.1]  # bar 9 closes inside the narrow bar's range -> no break
    lows += [99.8, 99.9]
    closes += [100.0, 100.0]
    signals = NarrowRangeBreakoutStrategy(window=7).generate_signals(_ohlc(highs, lows, closes))
    assert signals.iloc[-1] == 0.0


def test_flat_when_all_ranges_equal() -> None:
    # No bar is uniquely narrowest -> no setup -> flat throughout.
    highs, lows, closes = _wide(20)
    signals = NarrowRangeBreakoutStrategy(window=7).generate_signals(_ohlc(highs, lows, closes))
    assert (signals == 0.0).all()


def test_signal_values_are_in_minus_one_zero_one() -> None:
    rng = np.random.default_rng(seed=6)
    close = 100 + rng.standard_normal(200).cumsum() * 0.5
    spread = np.abs(rng.normal(1.0, 0.5, 200)) + 0.1  # varying ranges
    frame = _ohlc(list(close + spread), list(close - spread), list(close))
    signals = NarrowRangeBreakoutStrategy(window=7).generate_signals(frame)
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})


def test_no_lookahead_truncation_invariant() -> None:
    rng = np.random.default_rng(4)
    close = 100 + rng.standard_normal(150).cumsum() * 0.5
    spread = np.abs(rng.normal(1.0, 0.5, 150)) + 0.1
    frame = _ohlc(list(close + spread), list(close - spread), list(close))
    s = NarrowRangeBreakoutStrategy(window=7)
    full = s.generate_signals(frame)
    trunc = s.generate_signals(frame.iloc[:110])
    pd.testing.assert_series_equal(full.iloc[:110], trunc, check_names=False)


@given(n=st.integers(min_value=12, max_value=60), seed=st.integers(min_value=0, max_value=9999))
def test_signals_in_range(n: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    close = 100 + rng.standard_normal(n).cumsum() * 0.5
    spread = np.abs(rng.normal(1.0, 0.5, n)) + 0.1
    frame = _ohlc(list(close + spread), list(close - spread), list(close))
    signals = NarrowRangeBreakoutStrategy(window=5).generate_signals(frame)
    assert signals.between(-1.0, 1.0).all()
    assert signals.index.equals(frame.index)
