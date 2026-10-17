"""ADR-306: numeric categorical axis definitions own independent buffers."""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pandas.testing import assert_frame_equal, assert_index_equal

from app.research.cross_sectional.engine import split_panel_holdout
from app.research.frames import copy_frame
from app.research.lab.holdout import split_holdout


def _root(array: npt.NDArray[Any]) -> npt.NDArray[Any]:
    while isinstance(array.base, np.ndarray):
        array = array.base
    return array


def _axis(kind: str) -> pd.Index[Any]:
    categories = pd.Index(np.arange(10), name="category_domain")
    if kind == "date":
        categories = pd.date_range("2020-01-01", periods=10, tz="UTC", name="category_domain")
    category = pd.CategoricalIndex(
        pd.Categorical.from_codes(np.arange(8), categories=categories, ordered=True), name="first"
    )
    if kind == "multi":
        second = pd.CategoricalIndex(
            pd.Categorical.from_codes(
                np.arange(8),
                categories=pd.Index(np.arange(10) + 100, name="second_domain"),
                ordered=False,
            ),
            name="second",
        )
        return pd.MultiIndex.from_arrays([category, second], names=["first", "second"])
    return category


def _owners(axis: pd.Index[Any]) -> list[npt.NDArray[Any]]:
    if isinstance(axis, pd.MultiIndex):
        return [owner for level in axis.levels for owner in _owners(level)]
    assert isinstance(axis, pd.CategoricalIndex)
    categories = axis.categories
    values = categories.asi8 if isinstance(categories, pd.DatetimeIndex) else categories.to_numpy()
    return [_root(values)]


def _portions(source: pd.DataFrame, boundary: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if boundary == "copy":
        return copy_frame(source.iloc[:4]), copy_frame(source.iloc[4:])
    kwargs = {"holdout_fraction": 0.5, "min_holdout_bars": 2, "min_search_bars": 2}
    if boundary == "panel":
        return split_panel_holdout(source, **kwargs)  # type: ignore[arg-type]
    head, tail = split_holdout(source, "SYNTHETIC", **kwargs)  # type: ignore[arg-type]
    return head.frame, tail._frame


@pytest.mark.parametrize("boundary", ["copy", "single", "panel"])
@pytest.mark.parametrize("axis_name", ["index", "columns"])
@pytest.mark.parametrize("kind,level", [("numeric", 0), ("date", 0), ("multi", 0), ("multi", 1)])
@pytest.mark.parametrize("actor", [0, 1, 2])
def test_category_owner_mutation_cannot_change_another_frame_axis(
    boundary: str, axis_name: str, kind: str, level: int, actor: int
) -> None:
    source = pd.DataFrame(np.arange(64.0).reshape(8, 8) + 100)
    setattr(source, axis_name, _axis(kind))
    head, tail = _portions(source, boundary)
    assert_frame_equal(head, source.iloc[:4], check_exact=True)
    assert_frame_equal(tail, source.iloc[4:], check_exact=True)
    frames = [source, head, tail]
    axes = [getattr(frame, axis_name) for frame in frames]
    owners = [_owners(axis)[level] for axis in axes]
    before = [owner.copy() for owner in owners]
    prices = [frame.to_numpy(copy=True) for frame in frames]
    storage = owners[actor]
    if storage.dtype.kind == "M":
        storage = storage.view(np.int64)
    storage.flat[4] = int(storage.flat[4]) + 123456
    for index, owner in enumerate(owners):
        if index != actor:
            np.testing.assert_array_equal(owner, before[index])
            assert not np.shares_memory(owner, owners[actor])
    for index, frame in enumerate(frames):
        np.testing.assert_array_equal(frame.to_numpy(), prices[index])


@pytest.mark.parametrize("boundary", ["copy", "single", "panel"])
def test_search_category_owner_cannot_mutate_actual_heldout_scalar_label(boundary: str) -> None:
    source = pd.DataFrame({"close": np.arange(8.0) + 100}, index=_axis("numeric"))
    head, tail = _portions(source, boundary)
    _owners(head.index)[0][4] = 123456
    assert tail.index[0] == 4
    assert source.index[4] == 4


@pytest.mark.parametrize("ordered", [False, True])
@pytest.mark.parametrize("codes", [[0, 1, -1, 2, 0, -1, 1, 2], [-1] * 8])
@pytest.mark.parametrize("multi", [False, True])
@pytest.mark.parametrize("axis_name", ["index", "columns"])
def test_copy_preserves_na_codes_unused_categories_names_and_order(
    ordered: bool, codes: list[int], multi: bool, axis_name: str
) -> None:
    category = pd.CategoricalIndex(
        pd.Categorical.from_codes(
            codes, categories=pd.Index([10, 20, 30, 40], name="domain"), ordered=ordered
        ),
        name="label",
    )
    axis = (
        pd.MultiIndex.from_arrays([category, category], names=["first", "second"])
        if multi
        else category
    )
    source = pd.DataFrame(np.arange(64.0).reshape(8, 8))
    setattr(source, axis_name, axis)
    copied = copy_frame(source)
    assert_frame_equal(copied, source, check_exact=True)
    copied_axis = getattr(copied, axis_name)
    assert_index_equal(copied_axis, axis, exact=True, check_exact=True)
    levels = copied_axis.levels if multi else [copied_axis]
    original_levels = axis.levels if multi else [axis]
    for original, level in zip(original_levels, levels, strict=True):
        assert_index_equal(level.categories, original.categories, exact=True, check_exact=True)
        np.testing.assert_array_equal(level.codes, original.codes)
    for original, owner in zip(_owners(axis), _owners(copied_axis), strict=True):
        assert not np.shares_memory(original, owner)


@pytest.mark.parametrize("axis_name", ["index", "columns"])
@pytest.mark.parametrize(
    "axis",
    [
        pd.RangeIndex(8),
        pd.date_range("2020-01-01", periods=8, tz="UTC"),
        pd.timedelta_range("0D", periods=8),
        pd.period_range("2020-01", periods=8, freq="M"),
        pd.IntervalIndex.from_breaks(np.arange(9)),
        pd.MultiIndex.from_arrays([np.arange(8), pd.date_range("2020-01-01", periods=8)]),
    ],
)
def test_other_axis_families_preserve_exact_metadata(axis_name: str, axis: pd.Index[Any]) -> None:
    source = pd.DataFrame(np.arange(64.0).reshape(8, 8))
    setattr(source, axis_name, axis)
    copied = copy_frame(source)
    assert_frame_equal(copied, source, check_exact=True)
    assert_index_equal(getattr(copied, axis_name), axis, exact=True, check_exact=True)


@pytest.mark.parametrize("boundary", ["copy", "single", "panel"])
@given(
    labels=st.lists(st.integers(-100000, 100000), min_size=8, max_size=8, unique=True),
    actor=st.integers(0, 2),
    coordinate=st.integers(0, 9),
)
def test_arbitrary_category_owner_writes_preserve_other_axes_and_reconstruction(
    boundary: str, labels: list[int], actor: int, coordinate: int
) -> None:
    categories = [*sorted(labels), 100001, 100002]
    axis = pd.CategoricalIndex(
        pd.Categorical.from_codes(np.arange(8), categories=categories, ordered=True)
    )
    source = pd.DataFrame({"close": np.arange(8.0) + 100}, index=axis)
    head, tail = _portions(source, boundary)
    assert_frame_equal(pd.concat([head, tail]), source, check_exact=True)
    axes = [frame.index for frame in [source, head, tail]]
    owners = [_owners(index)[0] for index in axes]
    before = [owner.copy() for owner in owners]
    owners[actor][coordinate] = 123456
    for index, owner in enumerate(owners):
        if index != actor:
            np.testing.assert_array_equal(owner, before[index])
