"""_trade_markers: direction follows the SIGN of position.diff (positive=buy,
negative=sell); flat regions emit no markers; the first bar is treated as zero-prior
(no spurious 'buy from nothing'); equity at each marker matches the bar's equity."""

import pandas as pd

from app.api.v1.backtest import _trade_markers


def _series(values: list[float], start: str = "2024-01-01") -> pd.Series:
    index = pd.date_range(start=start, periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=index, dtype="float64")


def test_flat_position_yields_no_markers() -> None:
    position = _series([0.0, 0.0, 0.0, 0.0])
    equity = _series([100.0, 100.0, 100.0, 100.0])
    assert _trade_markers(position, equity) == []


def test_entering_long_from_flat_emits_a_buy() -> None:
    position = _series([0.0, 0.0, 1.0, 1.0])
    equity = _series([100.0, 100.0, 105.0, 110.0])
    markers = _trade_markers(position, equity)
    assert len(markers) == 1
    assert markers[0].direction == "buy"
    assert markers[0].equity == 105.0


def test_exiting_long_to_flat_emits_a_sell() -> None:
    position = _series([1.0, 1.0, 0.0, 0.0])
    equity = _series([100.0, 110.0, 108.0, 108.0])
    markers = _trade_markers(position, equity)
    assert len(markers) == 1
    assert markers[0].direction == "sell"
    assert markers[0].equity == 108.0


def test_flipping_long_to_short_emits_a_sell() -> None:
    # position drops from +1 to -1: a "sell" event by our diff-sign rule (collapses
    # closing the long AND opening the short into one marker — matches a trader's view).
    position = _series([1.0, 1.0, -1.0])
    equity = _series([100.0, 105.0, 102.0])
    markers = _trade_markers(position, equity)
    assert len(markers) == 1
    assert markers[0].direction == "sell"


def test_first_bar_with_nonzero_position_does_not_emit_a_marker() -> None:
    # The engine fills the diff of bar 0 with NaN -> filled to 0 by our helper. A strategy
    # that "starts long" should not appear to BUY out of nothing; the marker fires on the
    # first SIGNAL CHANGE, not on the first non-zero position.
    position = _series([1.0, 1.0, 1.0])
    equity = _series([100.0, 105.0, 110.0])
    markers = _trade_markers(position, equity)
    assert markers == []


def test_duplicate_timestamps_do_not_crash() -> None:
    # Real yfinance data has produced a duplicated bar timestamp; a label-based
    # equity.loc[ts] then returns a Series and float() raises TypeError -> a 500 that
    # browser-driving the Compare Configs page surfaced. The helper must iterate
    # positionally so a non-unique index never breaks it.
    idx = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"], utc=True)
    position = pd.Series([0.0, 1.0, 1.0, 0.0], index=idx)
    equity = pd.Series([100.0, 101.0, 101.0, 102.0], index=idx)
    markers = _trade_markers(position, equity)
    assert [m.direction for m in markers] == ["buy", "sell"]
    assert markers[0].equity == 101.0
    assert markers[1].equity == 102.0
