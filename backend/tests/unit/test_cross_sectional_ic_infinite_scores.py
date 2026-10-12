"""Infinite original factor evidence cannot publish a finite IC (ADR-265)."""

from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.cross_sectional.ic import rank_ic


def _prices(rows: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "A": 100 * 1.2 ** np.arange(rows),
            "B": 100 * 1.1 ** np.arange(rows),
            "C": np.full(rows, 100.0),
        }
    )


@pytest.mark.parametrize("value", [np.inf, -np.inf])
@pytest.mark.parametrize("kind", ["float64", "Float64", "longdouble", "decimal"])
@pytest.mark.parametrize("placement", ["all", "last", "singleton"])
def test_rank_ic_refuses_original_infinite_scores_even_when_unscorable(
    value: float, kind: str, placement: str
) -> None:
    rows = 1 if placement == "singleton" else 3
    signals = pd.DataFrame({"A": [3.0] * rows, "B": [2.0] * rows, "C": [1.0] * rows})
    if kind == "decimal":
        signals = signals.map(lambda score: Decimal(str(score)))
        signals.loc[rows - 1 if placement != "all" else slice(None), "A"] = Decimal(str(value))
    else:
        signals = signals.astype(kind)
        signals.loc[rows - 1 if placement != "all" else slice(None), "A"] = value
    before = signals.copy(deep=True)
    state = np.geterr()
    with (
        np.errstate(all="raise"),
        pytest.raises(ValueError, match="signals must not contain infinite scores"),
    ):
        rank_ic(signals, _prices(rows))
    pd.testing.assert_frame_equal(signals, before, check_exact=True)
    assert np.geterr() == state


def test_rank_ic_refuses_infinite_evidence_before_ranking(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbid_rank(*_: object, **__: object) -> None:
        pytest.fail("infinite factor evidence must not enter rank computation")

    monkeypatch.setattr(pd.DataFrame, "rank", forbid_rank)
    signals = pd.DataFrame({"A": [np.inf] * 3, "B": [np.inf] * 3, "C": [0.0] * 3})
    with pytest.raises(ValueError, match="signals must not contain infinite scores"):
        rank_ic(signals, _prices(3))


@pytest.mark.parametrize("source", ["columns", "calendar", "prices"])
def test_rank_ic_preserves_existing_source_refusal_precedence(source: str) -> None:
    signals = pd.DataFrame({"A": [np.inf] * 3, "B": [2.0] * 3, "C": [1.0] * 3})
    prices = _prices(3)
    if source == "columns":
        prices = prices[["B", "A", "C"]]
        message = "same symbol columns"
    elif source == "calendar":
        prices.index = [2, 1, 0]
        message = "price index must be unique and ascending"
    else:
        prices.iat[0, 0] = 0.0
        message = "prices must be finite and strictly positive"
    with pytest.raises(ValueError, match=message):
        rank_ic(signals, prices)


@pytest.mark.parametrize("kind", ["float64", "Float64", "longdouble", "object", "bool"])
def test_rank_ic_preserves_finite_missing_and_empty_score_behavior(kind: str) -> None:
    signals = pd.DataFrame({"A": [3.0, 3.0, 3.0], "B": [2.0, 2.0, 2.0], "C": [1.0, 1.0, 1.0]})
    if kind == "bool":
        signals = pd.DataFrame({"A": [True] * 3, "B": [False] * 3, "C": [False] * 3})
    else:
        signals = signals.astype(kind)
        signals.iloc[0] = np.nan
    actual = rank_ic(signals, _prices(3))
    expected_value = np.sqrt(3) / 2 if kind == "bool" else 1.0
    np.testing.assert_allclose(actual, expected_value, rtol=1e-14, atol=0)
    assert actual.index.tolist() == ([0, 1] if kind == "bool" else [1])
    assert rank_ic(signals.iloc[:0], _prices(0)).empty


@given(
    rows=st.integers(1, 8),
    value=st.sampled_from([np.inf, -np.inf]),
    position=st.integers(0, 7),
    missing=st.booleans(),
)
def test_rank_ic_never_ranks_original_infinite_factor_evidence(
    rows: int, value: float, position: int, missing: bool
) -> None:
    signals = pd.DataFrame(
        {"A": [3.0] * rows, "B": [2.0] * rows, "C": [np.nan if missing else 1.0] * rows}
    )
    signals.iat[position % rows, 0] = value
    with pytest.raises(ValueError, match="signals must not contain infinite scores"):
        rank_ic(signals, _prices(rows))
