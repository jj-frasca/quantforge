"""Per-period long/short ranker (ADR-024). Each date's cross-section of signals becomes
dollar-neutral target weights: the top `quantile` fraction share +1, the bottom fraction share -1.
NaN signals (an unscorable name that day) are excluded; a date with <2 valid names trades flat."""

from decimal import Decimal
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

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
    # All-equal signals: rank(method="first") is reproducible for this fixed column order.
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


@pytest.mark.parametrize("value", [np.inf, -np.inf])
@pytest.mark.parametrize("kind", ["float64", "Float64", "longdouble", "decimal"])
@pytest.mark.parametrize("other", [1.0, np.nan])
def test_long_short_weights_refuses_infinite_scores(value: float, kind: str, other: float) -> None:

    if kind == "decimal":
        signals = pd.DataFrame({"A": [Decimal(str(value))], "B": [Decimal(str(other))]})
    else:
        signals = pd.DataFrame({"A": [value], "B": [other]}).astype(kind)
    with pytest.raises(ValueError, match="infinite"):
        long_short_weights(signals, quantile=0.5)


def test_long_short_weights_refuses_infinite_score_before_ranking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbid_rank(*_: object, **__: object) -> None:
        pytest.fail("ranking must not consume infinite scores")

    monkeypatch.setattr(pd.DataFrame, "rank", forbid_rank)
    with pytest.raises(ValueError, match="infinite"):
        long_short_weights(pd.DataFrame({"A": [np.inf], "B": [1.0]}))


@pytest.mark.parametrize("kind", ["nullable", "wide", "fraction", "decimal", "bool", "empty"])
def test_long_short_weights_preserves_native_finite_and_missing_scores(kind: str) -> None:

    signals = pd.DataFrame({"A": [1.0, np.nan], "B": [2.0, np.nan]})
    if kind == "nullable":
        signals = signals.astype("Float64")
    elif kind == "wide":
        signals = signals.astype(np.longdouble)
        signals.iloc[0] = [np.longdouble("1e400"), np.longdouble("2e400")]
    elif kind == "fraction":
        signals = pd.DataFrame({"A": [Fraction(10**400), None], "B": [Fraction(2 * 10**400), None]})
    elif kind == "decimal":
        signals = pd.DataFrame({"A": [Decimal("1e400"), None], "B": [Decimal("2e400"), None]})
    elif kind == "bool":
        signals = pd.DataFrame({"A": [False], "B": [True]})
    elif kind == "empty":
        signals = signals.iloc[:0]
    expected = pd.DataFrame({"A": [-1.0, 0.0], "B": [1.0, 0.0]})
    if kind == "bool":
        expected = expected.iloc[:1]
    elif kind == "empty":
        expected = expected.iloc[:0]
    pd.testing.assert_frame_equal(long_short_weights(signals, 0.5), expected, check_exact=True)


@given(value=st.sampled_from([np.inf, -np.inf]), rows=st.integers(1, 8), missing=st.booleans())
def test_long_short_weights_never_ranks_an_infinite_factor_score(
    value: float, rows: int, missing: bool
) -> None:
    signals = pd.DataFrame({"A": [value] * rows, "B": [np.nan if missing else 1.0] * rows})
    with pytest.raises(ValueError, match="infinite"):
        long_short_weights(signals, 0.5)
