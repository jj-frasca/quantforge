"""Integer observations cannot wrap into false measurable innovations (ADR-238)."""

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import filtered_deviation


def _filter(source):
    return filtered_deviation(source, rho=0.5, level_vol=0.01, deviation_vol=0.02)


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.uint32, np.uint64])
@pytest.mark.parametrize("policy", ["ignore", "raise"])
def test_filter_unsigned_decrease_refuses_before_wrapped_estimates(dtype, policy):
    with np.errstate(all=policy), pytest.raises(ValueError, match="integer differences"):
        _filter(np.array([5, 4, 5], dtype=dtype))


@pytest.mark.parametrize("dtype", [np.int8, np.int16, np.int32, np.int64])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("policy", ["ignore", "raise"])
def test_filter_signed_overflow_refuses_before_wrapped_estimates(dtype, reverse, policy):
    limits = np.iinfo(dtype)
    source = np.array([limits.min, limits.max], dtype=dtype)
    if reverse:
        source = source[::-1]
    with np.errstate(all=policy), pytest.raises(ValueError, match="integer differences"):
        _filter(source)


@pytest.mark.parametrize(
    "dtype", [np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64]
)
@pytest.mark.parametrize("n", [0, 1, 3])
def test_filter_valid_integer_source_retains_native_estimates_and_ownership(dtype, n):
    source = np.array([4, 5, 6], dtype=dtype)[:n]
    before = source.copy()
    actual = _filter(source)
    expected = _filter(source.astype(float))
    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(source, before)
    assert not np.shares_memory(actual, source)


@pytest.mark.parametrize("dtype", [np.int8, np.int16, np.int32, np.int64])
def test_filter_valid_signed_decrease_retains_measured_state(dtype):
    np.testing.assert_array_equal(
        _filter(np.array([5, 4, 5], dtype=dtype)), _filter(np.array([5.0, 4.0, 5.0]))
    )


def test_filter_adjacent_large_unsigned_values_retain_original_difference():
    maximum = np.iinfo(np.uint64).max
    source = np.array([maximum - 1, maximum], dtype=np.uint64)
    assert np.diff(source).item() == 1
    assert np.diff(source.astype(float)).item() == 0
    np.testing.assert_array_equal(_filter(source), _filter(np.array([0, 1], dtype=np.uint64)))


@pytest.mark.parametrize("dtype", [">i2", ">u2"])
def test_filter_native_byte_order_and_all_false_mask_are_preserved(dtype):
    source = np.array([4, 5, 6], dtype=dtype)
    np.testing.assert_array_equal(_filter(np.ma.array(source, mask=False)), _filter(source))


def test_filter_original_parameter_error_precedes_integer_arithmetic():
    with pytest.raises(ValueError, match="rho must be"):
        filtered_deviation(
            np.array([5, 4], dtype=np.uint8), rho=1.0, level_vol=0.01, deviation_vol=0.02
        )


@given(right=st.integers(min_value=0, max_value=254))
def test_filter_unsigned_unrepresentable_difference_cannot_publish_states(right):
    with pytest.raises(ValueError, match="integer differences"):
        _filter(np.array([255, right], dtype=np.uint8))


@pytest.mark.parametrize("dtype", [np.int8, np.int16, np.int32, np.int64])
@pytest.mark.parametrize("boundary", ["min", "max"])
def test_filter_signed_difference_at_dtype_boundary_remains_measurable(dtype, boundary):
    value = getattr(np.iinfo(dtype), boundary)
    source = np.array([0, value], dtype=dtype)
    np.testing.assert_array_equal(_filter(source), _filter(source.astype(float)))


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.uint32, np.uint64])
@pytest.mark.parametrize("boundary", ["min", "max"])
def test_filter_unsigned_difference_at_dtype_boundary_remains_measurable(dtype, boundary):
    value = getattr(np.iinfo(dtype), boundary)
    source = np.array([0, value], dtype=dtype)
    np.testing.assert_array_equal(_filter(source), _filter(source.astype(float)))
