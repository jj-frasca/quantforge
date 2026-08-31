"""Per-period long/short ranker (ADR-024). Each date's cross-section of signals becomes
dollar-neutral target weights: the top `quantile` fraction share +1, the bottom fraction share -1.
NaN signals (an unscorable name that day) are excluded; a date with <2 valid names trades flat."""

import numpy as np
import pandas as pd
import pytest

from app.research.cross_sectional.panel import long_short_weights


def _panel(rows: dict[str, list[float]], n_dates: int) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=n_dates, freq="B", tz="UTC")
    return pd.DataFrame(rows, index=idx)


def test_long_short_weights_longs_the_top_and_shorts_the_bottom() -> None:
    signals = _panel({"A": [1.0], "B": [2.0], "C": [3.0], "D": [4.0]}, 1)
    w = long_short_weights(signals, quantile=0.25)
    row = w.iloc[0]
    assert row["D"] == pytest.approx(1.0)  # highest signal -> full long leg
    assert row["A"] == pytest.approx(-1.0)  # lowest signal -> full short leg
    assert row["B"] == 0.0 and row["C"] == 0.0


def test_long_short_weights_are_dollar_neutral_each_date() -> None:
    signals = _panel({"A": [1.0], "B": [2.0], "C": [3.0], "D": [4.0], "E": [5.0]}, 1)
    w = long_short_weights(signals, quantile=0.4)
    assert w.iloc[0].sum() == pytest.approx(0.0)  # net exposure zero


def test_long_short_weights_split_leg_shares_equally() -> None:
    signals = _panel({"A": [1.0], "B": [2.0], "C": [3.0], "D": [4.0]}, 1)
    w = long_short_weights(signals, quantile=0.5)  # k=2 per leg
    row = w.iloc[0]
    assert row["C"] == pytest.approx(0.5) and row["D"] == pytest.approx(0.5)
    assert row["A"] == pytest.approx(-0.5) and row["B"] == pytest.approx(-0.5)


def test_long_short_weights_excludes_nan_signals() -> None:
    signals = _panel({"A": [np.nan], "B": [2.0], "C": [3.0], "D": [4.0]}, 1)
    w = long_short_weights(signals, quantile=0.34)  # 3 valid -> k=1
    row = w.iloc[0]
    assert row["A"] == 0.0  # unscorable name never held
    assert row["D"] == pytest.approx(1.0) and row["B"] == pytest.approx(-1.0)


def test_long_short_weights_flat_when_fewer_than_two_valid_names() -> None:
    signals = _panel({"A": [np.nan], "B": [1.0]}, 1)
    w = long_short_weights(signals, quantile=0.5)
    assert (w.iloc[0] == 0.0).all()  # cannot form both legs -> flat


def test_long_short_weights_rejects_out_of_range_quantile() -> None:
    signals = _panel({"A": [1.0], "B": [2.0]}, 1)
    with pytest.raises(ValueError, match="quantile"):
        long_short_weights(signals, quantile=0.6)
    with pytest.raises(ValueError, match="quantile"):
        long_short_weights(signals, quantile=0.0)


def test_long_short_weights_breaks_ties_deterministically() -> None:
    # All-equal signals: rank(method="first") makes the choice reproducible, not order-dependent.
    signals = _panel({"A": [1.0], "B": [1.0], "C": [1.0], "D": [1.0]}, 1)
    w1 = long_short_weights(signals, quantile=0.25)
    w2 = long_short_weights(signals, quantile=0.25)
    pd.testing.assert_frame_equal(w1, w2)
    assert w1.iloc[0].sum() == pytest.approx(0.0)


def test_long_short_weights_sizes_each_date_from_that_date_own_valid_count() -> None:
    """The per-leg size k is a function of the valid names ON THAT DATE, not of the panel.

    This is the invariant a vectorised ranker is most likely to get wrong — it is easy to compute
    one k for the whole frame — and it was untested while the implementation was a row loop.
    """
    signals = _panel(
        {
            "A": [1.0, 1.0, 1.0],
            "B": [2.0, 2.0, np.nan],
            "C": [3.0, 3.0, np.nan],
            "D": [4.0, np.nan, np.nan],
        },
        3,
    )
    w = long_short_weights(signals, quantile=0.5)

    # date 0: 4 valid, k=2 -> C,D long at 1/2 each; A,B short at -1/2 each
    assert w.iloc[0].to_dict() == {"A": -0.5, "B": -0.5, "C": 0.5, "D": 0.5}
    # date 1: 3 valid, k=int(1.5)=1 -> C long, A short, B flat
    assert w.iloc[1].to_dict() == {"A": -1.0, "B": 0.0, "C": 1.0, "D": 0.0}
    # date 2: 1 valid -> cannot form both legs, trades flat
    assert w.iloc[2].to_dict() == {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}


def test_long_short_weights_are_flat_where_a_date_has_no_valid_names_at_all() -> None:
    signals = _panel({"A": [np.nan, 1.0], "B": [np.nan, 2.0]}, 2)
    w = long_short_weights(signals, quantile=0.5)

    assert w.iloc[0].to_dict() == {"A": 0.0, "B": 0.0}
    assert w.iloc[1].to_dict() == {"A": -1.0, "B": 1.0}
