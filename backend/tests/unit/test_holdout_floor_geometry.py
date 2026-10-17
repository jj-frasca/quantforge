"""ADR-305: original floor evidence and nonempty actual split geometry."""

import warnings
from decimal import Decimal
from fractions import Fraction
from typing import NoReturn

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from pandas.testing import assert_frame_equal

from app.research.cross_sectional import engine as panel_engine
from app.research.cross_sectional.engine import split_panel_holdout
from app.research.lab import holdout
from app.research.lab.holdout import split_holdout

NONEMPTY = "holdout split requires nonempty search and holdout portions"


def _frame(n: int) -> pd.DataFrame:
    return pd.DataFrame({"close": np.arange(n, dtype=float) + 100}, index=pd.RangeIndex(n))


def _split(frame: pd.DataFrame, panel: bool, **kwargs: object) -> tuple[pd.DataFrame, pd.DataFrame]:
    if panel:
        return split_panel_holdout(frame, **kwargs)  # type: ignore[arg-type]
    head, tail = split_holdout(frame, "SYNTHETIC", **kwargs)  # type: ignore[arg-type]
    return head.frame, tail._frame


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize("policy", ["ignore", "warn", "raise"])
@pytest.mark.parametrize("count", [2**64 - 1, np.uint64(2**64 - 1), np.int64(2**63 - 1), 2**100])
def test_huge_original_integral_floor_keeps_exact_size_error_without_warnings(
    panel: bool, policy: str, count: int
) -> None:
    expected = (
        f"insufficient data: {1000 - int(count)} search bars after a {int(count)}-bar holdout "
        "(need >= 252)"
    )
    original_policy = np.geterr()
    with warnings.catch_warnings(record=True) as caught, np.errstate(all=policy):
        warnings.simplefilter("always")
        with pytest.raises(ValueError) as error:
            _split(_frame(1000), panel, min_holdout_bars=count)
        assert str(error.value) == expected
    assert not caught
    assert np.geterr() == original_policy


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize("parameter", ["min_holdout_bars", "min_search_bars"])
@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        np.bool_(True),
        np.bool_(False),
        -1,
        np.int64(-1),
        0.0,
        1.0,
        -0.5,
        np.float64(1),
        float("nan"),
        float("inf"),
        Fraction(1, 1),
        Decimal(1),
        "1",
        None,
        np.array(1),
        [1],
    ],
)
def test_floor_requires_original_nonnegative_nonboolean_integral(
    panel: bool, parameter: str, value: object
) -> None:
    kwargs: dict[str, object] = {"min_holdout_bars": 2, "min_search_bars": 2}
    kwargs[parameter] = value
    with pytest.raises(ValueError) as error:
        _split(_frame(8), panel, **kwargs)
    assert str(error.value) == f"{parameter} must be a nonnegative nonboolean integer"


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize("floor_type", [int, np.int64, np.uint64])
@pytest.mark.parametrize("floors", [(0, 0), (0, 1), (1, 0), (3, 2)])
def test_nonnegative_native_floors_preserve_exact_nonempty_geometry(
    panel: bool, floor_type: type, floors: tuple[int, int]
) -> None:
    source = _frame(8)
    before = source.copy(deep=True)
    head, tail = _split(
        source,
        panel,
        holdout_fraction=0.25,
        min_holdout_bars=floor_type(floors[0]),
        min_search_bars=floor_type(floors[1]),
    )
    cut = 8 - max(2, floors[0])
    assert_frame_equal(head, before.iloc[:cut], check_exact=True)
    assert_frame_equal(tail, before.iloc[cut:], check_exact=True)
    assert_frame_equal(pd.concat([head, tail]), before, check_exact=True)
    assert_frame_equal(source, before, check_exact=True)


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize(
    "n,fraction,holdout_floor,search_floor",
    [(8, 0.01, 0, 1), (8, np.nextafter(0.0, 1.0), 0, 0), (8, 0.5, 8, 0), (0, 0.5, 0, 0)],
)
def test_actual_portions_must_be_nonempty_before_copy_or_slicing(
    panel: bool,
    n: int,
    fraction: float,
    holdout_floor: int,
    search_floor: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NoSliceFrame(pd.DataFrame):
        @property
        def iloc(self) -> NoReturn:
            pytest.fail("empty geometry reached slicing")

    def unexpected(*args: object, **kwargs: object) -> None:
        pytest.fail("empty geometry reached copying")

    monkeypatch.setattr(panel_engine if panel else holdout, "copy_frame", unexpected)
    with pytest.raises(ValueError) as error:
        _split(
            NoSliceFrame(_frame(n)),
            panel,
            holdout_fraction=fraction,
            min_holdout_bars=holdout_floor,
            min_search_bars=search_floor,
        )
    assert str(error.value) == NONEMPTY


@pytest.mark.parametrize("panel", [False, True])
def test_fraction_calendar_floor_and_size_error_precedence(panel: bool) -> None:
    malformed = _frame(3).iloc[::-1]
    for fraction, expected in [
        (1.0, "holdout_fraction must be in (0, 1)"),
        (0.5, "holdout source index must be unique and ascending"),
    ]:
        with pytest.raises(ValueError) as error:
            _split(
                malformed,
                panel,
                holdout_fraction=fraction,
                min_holdout_bars=False,
                min_search_bars=False,
            )
        assert str(error.value) == expected
    with pytest.raises(ValueError, match=r"^min_holdout_bars must"):
        _split(_frame(8), panel, min_holdout_bars=False, min_search_bars=False)
    for n, floor, minimum in [(8, 10, 0), (0, 252, 252), (1, 252, 252)]:
        with pytest.raises(ValueError) as error:
            _split(_frame(n), panel, min_holdout_bars=floor, min_search_bars=minimum)
        assert str(error.value) == (
            f"insufficient data: {n - floor} search bars after a {floor}-bar holdout "
            f"(need >= {minimum})"
        )


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize("parameter", ["min_holdout_bars", "min_search_bars"])
def test_invalid_floor_refuses_before_source_length(panel: bool, parameter: str) -> None:
    class NoLengthFrame(pd.DataFrame):
        def __len__(self) -> int:
            pytest.fail("invalid original floor reached source length")

    kwargs: dict[str, object] = {"min_holdout_bars": 2, "min_search_bars": 2, parameter: False}
    with pytest.raises(ValueError, match=f"^{parameter} must"):
        _split(NoLengthFrame(_frame(8)), panel, **kwargs)


@pytest.mark.parametrize("panel", [False, True])
@given(
    n=st.integers(0, 64),
    fraction=st.floats(0.001, 0.999),
    holdout_floor=st.integers(0, 128),
    search_floor=st.integers(0, 128),
)
@example(n=0, fraction=0.5, holdout_floor=0, search_floor=0)
@example(n=8, fraction=0.01, holdout_floor=0, search_floor=1)
@example(n=8, fraction=0.5, holdout_floor=8, search_floor=0)
@example(n=8, fraction=0.5, holdout_floor=0, search_floor=0)
def test_floor_boundaries_preserve_reconstruction_or_exact_refusal(
    panel: bool, n: int, fraction: float, holdout_floor: int, search_floor: int
) -> None:
    source = _frame(n)
    before = source.copy(deep=True)
    holdout_n = max(int(fraction * n), holdout_floor)
    search_n = n - holdout_n
    expected_error = None
    if search_n < search_floor:
        expected_error = (
            f"insufficient data: {search_n} search bars after a {holdout_n}-bar holdout "
            f"(need >= {search_floor})"
        )
    elif holdout_n < 1 or search_n < 1:
        expected_error = NONEMPTY
    for floor_type in [int, np.int64, np.uint64]:
        kwargs = {
            "holdout_fraction": fraction,
            "min_holdout_bars": floor_type(holdout_floor),
            "min_search_bars": floor_type(search_floor),
        }
        if expected_error is not None:
            with pytest.raises(ValueError) as error:
                _split(source, panel, **kwargs)
            assert str(error.value) == expected_error
        else:
            head, tail = _split(source, panel, **kwargs)
            assert len(head) == search_n > 0
            assert len(tail) == holdout_n > 0
            assert head.index.max() < tail.index.min()
            assert head.index.intersection(tail.index).empty
            assert_frame_equal(pd.concat([head, tail]), before, check_exact=True)
        assert_frame_equal(source, before, check_exact=True)


@pytest.mark.parametrize("panel", [False, True])
def test_ordinary_unsigned_default_floor_preserves_748_252_split(panel: bool) -> None:
    source = _frame(1000)
    head, tail = _split(source, panel, min_holdout_bars=np.uint64(252))
    assert_frame_equal(head, source.iloc[:748], check_exact=True)
    assert_frame_equal(tail, source.iloc[748:], check_exact=True)
