"""Bootstrap draws keep one ordered source observation identity (ADR-244)."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import bootstrap_null


def source(index: pd.Index) -> pd.DataFrame:
    close = np.array([100.0, 110.0, 99.0, 118.8])[: len(index)]
    return pd.DataFrame(
        {
            "open": close * np.array([1.0, 1.01, 1.02, 1.03])[: len(index)],
            "high": close * 1.1,
            "low": close * 0.9,
            "close": close,
            "volume": np.arange(len(index), dtype=float) + 100,
        },
        index=index,
    )


@pytest.mark.parametrize(
    "index",
    [
        pd.Index([0, 1, 1, 2]),
        pd.Index([0, 0]),
        pd.Index([3, 2, 1, 0]),
        pd.Index([0, 2, 1, 3]),
        pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-02", "2020-01-04"]),
        pd.to_datetime(["2020-01-04", "2020-01-03", "2020-01-02", "2020-01-01"]),
    ],
)
def test_bootstrap_refuses_ambiguous_or_reordered_source_calendar(index: pd.Index) -> None:
    frame = source(index)
    original = frame.copy(deep=True)
    with pytest.raises(ValueError, match=r"calendar|index"):
        bootstrap_null(frame, 20, seed=11)
    pd.testing.assert_frame_equal(frame, original)


def test_calendar_refusal_precedes_price_access_and_rng(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame(index=pd.Index([0, 0]))

    def unexpected_rng(*_: object) -> None:
        pytest.fail("malformed source cannot reach RNG")

    monkeypatch.setattr(np.random, "default_rng", unexpected_rng)
    with pytest.raises(ValueError, match=r"calendar|index"):
        bootstrap_null(frame, 20, seed=11)


@pytest.mark.parametrize(
    "index",
    [
        pd.RangeIndex(4),
        pd.Index([0, 2, 10, 20]),
        pd.Index(["a", "b", "c", "d"]),
        pd.date_range("2020-01-01", periods=4),
        pd.date_range("2020-01-01", periods=4, tz="UTC"),
        pd.date_range("2020-01-01", periods=4, tz="US/Eastern"),
        pd.to_datetime(["2020-01-01", "2020-01-03", "2020-02-01", "2020-03-01"]),
    ],
)
@pytest.mark.parametrize("start_price", [None, 50.0])
def test_ordered_calendars_preserve_exact_native_paired_draws(
    index: pd.Index, start_price: float | None
) -> None:
    frame = source(index)
    original = frame.copy(deep=True)
    returns = frame["close"].pct_change().dropna()
    bars = frame.iloc[1:]
    draw = np.random.default_rng(11).integers(0, 3, 20)
    base = 100.0 if start_price is None else start_price
    closes = base * np.cumprod(1.0 + returns.to_numpy()[draw])
    result = bootstrap_null(frame, 20, seed=11, start_price=start_price)
    np.testing.assert_array_equal(result["close"], closes)
    for column in ("open", "high", "low"):
        expected = closes * (bars[column] / bars["close"]).to_numpy()[draw]
        np.testing.assert_array_equal(result[column], expected)
    np.testing.assert_array_equal(result["volume"], bars["volume"].to_numpy()[draw])
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("length", [0, 1])
def test_ordered_empty_and_singleton_sources_keep_no_returns_refusal(length: int) -> None:
    with pytest.raises(ValueError, match="no returns"):
        bootstrap_null(source(pd.RangeIndex(length)), 20, seed=11)


def test_invalid_requested_length_keeps_existing_precedence() -> None:
    with pytest.raises(ValueError, match="n_bars"):
        bootstrap_null(pd.DataFrame(index=pd.Index([0, 0])), 0, seed=11)


@given(st.permutations((0, 1, 2, 3)).filter(lambda order: tuple(order) != (0, 1, 2, 3)))
def test_nonidentity_source_permutations_cannot_define_bootstrap_adjacency(
    order: list[int],
) -> None:
    frame = source(pd.RangeIndex(4)).iloc[list(order)]
    with pytest.raises(ValueError, match=r"calendar|index"):
        bootstrap_null(frame, 20, seed=11)
