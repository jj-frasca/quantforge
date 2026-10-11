"""Observed filter sources cannot disappear into missing forecasts (ADR-234)."""

import numpy as np
import numpy.typing as npt
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.lab.calibration import filtered_deviation


def estimate(source: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    return filtered_deviation(source, rho=0.5, level_vol=0.01, deviation_vol=0.02, drift=0.0003)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("location", [0, 2, 4])
def test_filter_nonfinite_source_is_refused_before_recursion(bad: float, location: int) -> None:
    source = np.array([4.6, 4.61, 4.6, 4.6, 4.61])
    source[location] = bad
    with pytest.raises(ValueError, match="log prices must be complete and finite"):
        estimate(source)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_filter_nonfinite_singleton_is_refused(bad: float) -> None:
    with pytest.raises(ValueError, match="log prices must be complete and finite"):
        estimate(np.array([bad]))


@pytest.mark.parametrize("dtype", ["complex128", "bool", "object", "str", "datetime64[ns]"])
@pytest.mark.parametrize("n", [0, 1, 5])
def test_filter_nonreal_original_dtype_is_refused_before_shortcut(dtype: str, n: int) -> None:
    source = np.array([1] * n, dtype=dtype)
    with pytest.raises(ValueError, match="log prices must be real nonboolean numeric"):
        estimate(source)


@pytest.mark.parametrize("shape", [(), (0, 1), (1, 1), (5, 1), (1, 5)])
def test_filter_source_must_be_one_dimensional(shape: tuple[int, ...]) -> None:
    with pytest.raises(ValueError, match="log prices must be one-dimensional"):
        estimate(np.ones(shape))


@pytest.mark.parametrize("n", [1, 5])
@pytest.mark.parametrize("location", [0, -1])
def test_filter_masked_observation_is_missing_source(n: int, location: int) -> None:
    source = np.ma.array(np.arange(n, dtype=float), mask=[False] * n)
    source.mask[location] = True
    with pytest.raises(ValueError, match="log prices must be complete and finite"):
        estimate(source)


@pytest.mark.parametrize("dtype", ["float16", "float32", "float64", "int64", "uint64"])
@pytest.mark.parametrize("n", [0, 1])
def test_filter_complete_short_numeric_history_retains_startup(dtype: str, n: int) -> None:
    actual = estimate(np.array([0] * n, dtype=dtype))
    assert actual.shape == (n,)
    if n:
        assert np.isnan(actual[0])


@pytest.mark.parametrize(
    ("dtype", "hex_values"),
    [
        (
            "float32",
            [
                "0x1.c26fe9999999ap-2",
                "-0x1.794f36aaaaaa8p-5",
                "0x1.98df099426995p-1",
                "0x1.90aef9b3c3f77p-3",
            ],
        ),
        (
            "float64",
            [
                "0x1.c26fe718a86d8p-2",
                "-0x1.794f536bff748p-5",
                "0x1.98df0c31c7cd6p-1",
                "0x1.90aefdabb8605p-3",
            ],
        ),
        (
            "int64",
            [
                "0x1.997a24894c448p-2",
                "-0x1.55cb4c5277546p-3",
                "0x1.b60c1e0498eabp-1",
                "0x1.18aa2628f8e46p-3",
            ],
        ),
    ],
)
def test_filter_original_native_dtype_arithmetic_is_preserved(
    dtype: str, hex_values: list[str]
) -> None:
    # Captured on 325a8337 before ADR-234; float32 must not become float64 np.diff.
    source = np.array([2.1, 3.2, 2.4, 4.1, 3.3], dtype=dtype)
    before = source.copy()
    actual = estimate(source)
    np.testing.assert_allclose(
        actual, [np.nan, *map(float.fromhex, hex_values)], rtol=1e-13, atol=1e-15, equal_nan=True
    )
    np.testing.assert_array_equal(source, before)


def test_filter_all_false_mask_preserves_original_native_estimates() -> None:
    source = np.array([-2.1, -1.7, 0.2, -0.8, 1.2])
    np.testing.assert_array_equal(estimate(np.ma.array(source, mask=False)), estimate(source))


def test_filter_invalid_parameter_error_precedes_invalid_source() -> None:
    with pytest.raises(ValueError, match="rho must be"):
        filtered_deviation(np.array([np.nan]), rho=1.0, level_vol=0.01, deviation_vol=0.02)


@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
def test_filter_float64_source_representation_preserves_numpy_error_state(mode: str) -> None:
    source = np.array([np.finfo(np.longdouble).max], dtype=np.longdouble)
    with np.errstate(all=mode):
        before = np.geterr().copy()
        if np.finfo(np.longdouble).max > np.finfo(np.float64).max:
            with pytest.raises(ValueError, match="log prices must be complete and finite"):
                estimate(source)
        else:
            # Some platforms have no wider real dtype; the representable singleton stays valid.
            assert np.isnan(estimate(source)[0])
        assert np.geterr() == before


@settings(max_examples=30)
@given(st.lists(st.floats(min_value=-10, max_value=10, allow_nan=False), min_size=2, max_size=20))
def test_filter_missing_source_cannot_become_flat_reference(values: list[float]) -> None:
    source = np.array(values)
    source[len(source) // 2] = np.nan
    with pytest.raises(ValueError, match="log prices must be complete and finite"):
        estimate(source)


@settings(max_examples=30)
@given(st.lists(st.floats(min_value=-10, max_value=10, allow_nan=False), min_size=4, max_size=20))
def test_filter_finite_signed_source_preserves_causal_prefix(values: list[float]) -> None:
    source = np.array(values)
    stop = len(source) // 2
    np.testing.assert_array_equal(estimate(source)[:stop], estimate(source[:stop]))
