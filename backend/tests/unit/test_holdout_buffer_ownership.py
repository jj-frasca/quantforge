"""ADR-304: split numeric owners and axes cannot retain another portion's data."""

from typing import Literal

import numpy as np
import numpy.typing as npt
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pandas.testing import assert_frame_equal, assert_index_equal

from app.research.cross_sectional.engine import split_panel_holdout
from app.research.lab.holdout import split_holdout


def _root(array: npt.NDArray[np.generic]) -> npt.NDArray[np.generic]:
    while isinstance(array.base, np.ndarray):
        array = array.base
    return array


def _source() -> pd.DataFrame:
    return pd.DataFrame(
        {
            name: np.arange(8, dtype=float) + offset
            for name, offset in [
                ("open", 2000),
                ("high", 3000),
                ("low", 500),
                ("close", 1000),
                ("volume", 10000),
            ]
        },
        index=pd.date_range("2020-01-01", periods=8, tz="UTC"),
    )


def _split(source: pd.DataFrame, panel: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    if panel:
        return split_panel_holdout(
            source, holdout_fraction=0.5, min_holdout_bars=2, min_search_bars=2
        )
    head, tail = split_holdout(
        source, "SYNTHETIC", holdout_fraction=0.5, min_holdout_bars=2, min_search_bars=2
    )
    return head.frame, tail._frame


def _snapshot(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy(deep=True)
    result.index = frame.index.copy(deep=True)
    result.columns = frame.columns.copy(deep=True)
    return result


@pytest.mark.parametrize("panel", [False, True])
def test_holdout_search_public_numeric_owner_contains_no_future_prices(panel: bool) -> None:
    source = _source()
    head, tail = _split(source, panel)
    values = head["close"].to_numpy(copy=False)
    # CoW read-only views alone were insufficient: their writable .base held the entire source.
    assert not values.flags.writeable
    owner = _root(values)
    assert owner.flags.writeable
    assert not any(np.any(owner == price) for price in [1004.0, 1005.0, 1006.0, 1007.0])
    assert not np.shares_memory(owner, tail["close"].to_numpy(copy=False))
    assert not np.shares_memory(owner, source["close"].to_numpy(copy=False))


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize("actor", [0, 1, 2])
def test_holdout_source_and_returned_numeric_owner_writes_are_isolated(
    panel: bool, actor: int
) -> None:
    source = _source()
    head, tail = _split(source, panel)
    frames = [source, head, tail]
    snapshots = [_snapshot(frame) for frame in frames]
    owner = _root(frames[actor]["close"].to_numpy(copy=False))
    original = frames[actor]["close"].iloc[0]
    coordinate = tuple(np.argwhere(owner == original)[0])
    owner[coordinate] = 123456.0
    assert frames[actor]["close"].iloc[0] == 123456.0
    for index, frame in enumerate(frames):
        if index != actor:
            assert_frame_equal(frame, snapshots[index], check_exact=True)


@pytest.mark.parametrize("panel", [False, True])
def test_holdout_datetime_asi8_owner_has_only_its_own_calendar(panel: bool) -> None:
    source = _source()
    head, tail = _split(source, panel)
    assert _root(head.index.asi8).size == len(head)
    assert _root(tail.index.asi8).size == len(tail)
    for first, second in [(source, head), (source, tail), (head, tail)]:
        assert not np.shares_memory(first.index.asi8, second.index.asi8)
        assert not np.shares_memory(
            first.columns.to_numpy(copy=False), second.columns.to_numpy(copy=False)
        )


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize("actor", [0, 1, 2])
@pytest.mark.parametrize("axis", ["index", "columns"])
def test_holdout_source_and_returned_axis_owner_writes_are_isolated(
    panel: bool, actor: int, axis: str
) -> None:
    source = _source()
    head, tail = _split(source, panel)
    frames = [source, head, tail]
    snapshots = [_snapshot(frame) for frame in frames]
    if axis == "index":
        index_owner = _root(frames[actor].index.asi8).view(np.int64)
        index_owner.flat[0] = int(index_owner.flat[0]) + 1
    else:
        column_owner = _root(frames[actor].columns.to_numpy(copy=False))
        column_owner.flat[0] = "changed"
    for index, frame in enumerate(frames):
        if index != actor:
            assert_index_equal(frame.index, snapshots[index].index)
            assert_index_equal(frame.columns, snapshots[index].columns)


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize("layout", ["C", "F", "strided", "mixed"])
def test_holdout_numeric_layouts_preserve_exact_values_dtypes_axes(
    panel: bool, layout: Literal["C", "F", "strided", "mixed"]
) -> None:
    if layout == "mixed":
        source = pd.DataFrame(
            {
                "close": np.arange(8, dtype=np.longdouble) + 100,
                "unsigned": np.arange(8, dtype=np.uint64) + 2**63,
                "small": np.arange(8, dtype=np.float32),
                "nullable": pd.array(range(8), dtype="Int64"),
            },
            index=pd.date_range("2020-01-01", periods=8),
        )
    else:
        array = np.arange(64.0, dtype=float).reshape(16, 4) + 100
        array = array[::2] if layout == "strided" else np.array(array[:8], order=layout)
        source = pd.DataFrame(array, columns=["close", "a", "b", "c"], copy=False)
    before = _snapshot(source)
    head, tail = _split(source, panel)
    assert_frame_equal(head, before.iloc[:4], check_exact=True)
    assert_frame_equal(tail, before.iloc[4:], check_exact=True)
    assert_frame_equal(source, before, check_exact=True)
    assert_frame_equal(pd.concat([head, tail]), before, check_exact=True)
    for column in source.columns:
        for returned in [head, tail]:
            assert not np.shares_memory(
                source[column].to_numpy(copy=False), returned[column].to_numpy(copy=False)
            )


@pytest.mark.parametrize("panel", [False, True])
@given(st.lists(st.integers(100000, 10000000), min_size=4, max_size=4))
def test_holdout_future_tail_cannot_change_reachable_search_numeric_owner(
    panel: bool, future: list[int]
) -> None:
    source = _source()
    changed = _snapshot(source)
    changed.loc[changed.index[4:], "close"] = future
    first_head, _ = _split(source, panel)
    second_head, _ = _split(changed, panel)
    assert_frame_equal(first_head, second_head, check_exact=True)
    np.testing.assert_array_equal(
        _root(first_head["close"].to_numpy(copy=False)),
        _root(second_head["close"].to_numpy(copy=False)),
    )
