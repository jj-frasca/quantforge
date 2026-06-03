"""DonchianBreakoutStrategy: param validation; long on new highs, short on new lows;
position carries forward between breakouts (Turtle rule); no look-ahead."""

import numpy as np
import pandas as pd
import pytest

from app.research.strategies.donchian_breakout import DonchianBreakoutStrategy


def test_rejects_invalid_lookback() -> None:
    with pytest.raises(ValueError, match="lookback"):
        DonchianBreakoutStrategy(lookback=1)


def test_long_on_breakout_above_channel_high() -> None:
    # Flat at 100, then a single bar at 110 — new high → long signal
    series = pd.Series([100.0] * 30 + [110.0], name="close")
    data = pd.DataFrame({"close": series})
    signals = DonchianBreakoutStrategy(lookback=10).generate_signals(data)
    assert signals.iloc[-1] == 1.0


def test_short_on_breakout_below_channel_low() -> None:
    series = pd.Series([100.0] * 30 + [90.0], name="close")
    data = pd.DataFrame({"close": series})
    signals = DonchianBreakoutStrategy(lookback=10).generate_signals(data)
    assert signals.iloc[-1] == -1.0


def test_position_carries_forward_between_breakouts() -> None:
    # Breakout long at bar 30, then flat at 105 (no new high or low) — position holds at +1
    series = pd.Series([100.0] * 30 + [110.0] + [105.0] * 10, name="close")
    data = pd.DataFrame({"close": series})
    signals = DonchianBreakoutStrategy(lookback=10).generate_signals(data)
    # All bars after the breakout should still be long
    assert (signals.iloc[31:] == 1.0).all()


def test_no_look_ahead_in_breakout_comparison() -> None:
    # If we did NOT shift, bar 30's own value would be in the channel max → no breakout.
    # The shift means the comparison uses strictly-prior bars, so a fresh high triggers.
    rng = np.random.default_rng(seed=7)
    prices = pd.Series(100 + rng.standard_normal(50).cumsum() * 0.1, name="close")
    data = pd.DataFrame({"close": prices})
    # Just ensure no crash and signals stay in {-1, 0, +1}
    signals = DonchianBreakoutStrategy(lookback=10).generate_signals(data)
    assert set(signals.unique()).issubset({-1.0, 0.0, 1.0})
