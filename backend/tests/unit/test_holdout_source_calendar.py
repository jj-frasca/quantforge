"""Whole-source chronology precedes positional holdout slicing (ADR-302)."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pandas.testing import assert_frame_equal

from app.research.cross_sectional.engine import split_panel_holdout
from app.research.lab.holdout import split_holdout
from app.research.lab.search import run_search


def _split(frame: pd.DataFrame, panel: bool, **kwargs: object) -> tuple[pd.DataFrame, pd.DataFrame]:
    if panel:
        return split_panel_holdout(frame, **kwargs)  # type: ignore[arg-type]
    handle, sealed = split_holdout(frame, "SYNTHETIC", **kwargs)  # type: ignore[arg-type]
    return handle.frame, sealed._frame


def _frame(index: pd.Index) -> pd.DataFrame:
    return pd.DataFrame({"close": np.arange(len(index), dtype=float) + 100}, index=index)


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize(
    "positions",
    [
        [4, 5, 6, 7, 0, 1, 2, 3],
        [0, 1, 2, 3, 3, 4, 5, 6],
        [7, 6, 5, 4, 3, 2, 1, 0],
        [0, 2, 1, 3, 4, 5, 6, 7],
    ],
)
def test_holdout_split_original_malformed_calendar_refuses_without_mutation(
    panel: bool, positions: list[int]
) -> None:
    dates = pd.date_range("2020-01-01", periods=8, tz="UTC")
    source = _frame(dates[positions])
    before = source.copy(deep=True)
    with pytest.raises(ValueError, match="unique and ascending"):
        _split(source, panel, holdout_fraction=0.5, min_holdout_bars=2, min_search_bars=2)
    assert_frame_equal(source, before)


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize(
    "index", [pd.DatetimeIndex([pd.NaT]), pd.DatetimeIndex([pd.Timestamp("2020-01-01"), pd.NaT])]
)
def test_holdout_split_missing_calendar_identity_refuses_before_size(
    panel: bool, index: pd.Index
) -> None:
    with pytest.raises(ValueError, match="unique and ascending"):
        _split(_frame(index), panel)


@pytest.mark.parametrize("panel", [False, True])
def test_holdout_split_fraction_validation_remains_first(panel: bool) -> None:
    with pytest.raises(ValueError, match="holdout_fraction"):
        _split(_frame(pd.Index([3, 2, 1])), panel, holdout_fraction=1.0)


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize(
    "index",
    [
        pd.Index([]),
        pd.Index([1]),
        pd.DatetimeIndex([], tz="UTC"),
        pd.DatetimeIndex([pd.Timestamp("2020-01-01", tz="UTC")]),
    ],
)
def test_holdout_split_valid_short_calendar_keeps_size_refusal(
    panel: bool, index: pd.Index
) -> None:
    with pytest.raises(ValueError, match="insufficient data"):
        _split(_frame(index), panel)


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize(
    "index",
    [
        pd.RangeIndex(8),
        pd.Index(list("abcdefgh")),
        pd.MultiIndex.from_product([[1, 2], [1, 2, 3, 4]]),
        pd.date_range("2020-01-01", periods=8),
        pd.date_range("2020-01-01", periods=8, tz="UTC"),
        pd.date_range("2020-01-01", periods=8, tz="America/New_York"),
    ],
)
def test_holdout_split_valid_ordered_calendar_preserves_exact_source_slices(
    panel: bool, index: pd.Index
) -> None:
    source = _frame(index)
    before = source.copy(deep=True)
    head, tail = _split(source, panel, holdout_fraction=0.25, min_holdout_bars=3, min_search_bars=2)
    assert_frame_equal(head, source.iloc[:5])
    assert_frame_equal(tail, source.iloc[5:])
    assert_frame_equal(pd.concat([head, tail]), before)
    assert_frame_equal(source, before)
    assert head.index.max() < tail.index.min()


def test_run_search_malformed_whole_calendar_refuses_before_candidate_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.research.lab import search

    dates = pd.date_range("2020-01-01", periods=1000, freq="B", tz="UTC")
    source = _frame(dates)
    rotated = pd.concat([source.iloc[252:], source.iloc[:252]])

    def unexpected(*args: object, **kwargs: object) -> None:
        pytest.fail("malformed calendar reached candidate allocation")

    monkeypatch.setattr(search, "allocate_catalog_candidate_budget", unexpected)
    with pytest.raises(ValueError, match="unique and ascending"):
        run_search(rotated, "SYNTHETIC", ["sma"], n_per_param=2)


@pytest.mark.parametrize("panel", [False, True])
@given(
    st.lists(st.integers(-100000, 100000), min_size=4, max_size=30, unique=True),
    st.floats(0.1, 0.8, allow_nan=False, allow_infinity=False),
)
def test_holdout_split_ordered_source_strict_boundary_and_exact_reconstruction(
    panel: bool, positions: list[int], fraction: float
) -> None:
    source = _frame(pd.Index(sorted(positions)))
    before = source.copy(deep=True)
    head, tail = _split(
        source, panel, holdout_fraction=fraction, min_holdout_bars=1, min_search_bars=1
    )
    assert len(head) + len(tail) == len(source)
    assert head.index.max() < tail.index.min()
    assert head.index.intersection(tail.index).empty
    assert_frame_equal(pd.concat([head, tail]), before)
    assert_frame_equal(source, before)


@pytest.mark.parametrize("panel", [False, True])
@given(st.permutations(tuple(range(6))))
def test_holdout_split_refuses_arbitrary_nonchronological_permutations(
    panel: bool, positions: list[int]
) -> None:
    source = _frame(pd.Index(positions))
    if list(positions) == list(range(6)):
        head, tail = _split(source, panel, min_holdout_bars=2, min_search_bars=2)
        assert head.index.max() < tail.index.min()
    else:
        with pytest.raises(ValueError, match="unique and ascending"):
            _split(source, panel, min_holdout_bars=2, min_search_bars=2)
