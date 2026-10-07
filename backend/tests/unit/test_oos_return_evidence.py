"""Original real numeric and complete finite evidence at both OOS diagnostic boundaries."""

import math
from functools import partial

import numpy as np
import pytest

from app.validation.purged_cv import purged_cv_evaluate
from app.validation.walk_forward import walk_forward_evaluate


@pytest.fixture(params=[walk_forward_evaluate, partial(purged_cv_evaluate, embargo=0)])
def evaluate(request):
    return request.param


@pytest.mark.parametrize("role", ["train", "test", "benchmark"])
@pytest.mark.parametrize("scale", [1e200, 1e-200])
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
def test_oos_refuses_unmeasurable_native_dispersion(evaluate, role, scale, error_mode) -> None:
    positive = np.tile([0.01, 0.02, 0.03], 4)
    performance = np.column_stack((positive, -positive))
    benchmark = positive.copy()
    if role == "benchmark":
        benchmark[6:] *= scale
    elif role == "train":
        performance[:6] *= scale
    else:
        performance[6:] *= scale
    with np.errstate(all=error_mode), pytest.raises(ValueError, match="measurable"):
        evaluate(performance, [(np.arange(6), np.arange(6, 12))], benchmark=benchmark)


@pytest.mark.parametrize("role", ["train", "test", "benchmark"])
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
def test_oos_refuses_nonconstant_native_mean_overflow(evaluate, role, error_mode) -> None:
    positive = np.tile([0.01, 0.02, 0.03], 4)
    performance = np.column_stack((positive, -positive))
    benchmark = positive.copy()
    large = np.tile([1e308, 1.5e308], 3)
    if role == "train":
        performance[:6, 0] = large
    elif role == "test":
        performance[6:, 0] = large
    else:
        benchmark[6:] = large
    with np.errstate(all=error_mode), pytest.raises(ValueError, match="measurable"):
        evaluate(performance, [(np.arange(6), np.arange(6, 12))], benchmark=benchmark)


@pytest.mark.parametrize("constants", [[0.1, 0.3], [1e308, -1e308], [1e-200, -1e-200], [0.0, 0.0]])
@pytest.mark.parametrize("error_mode", ["ignore", "raise"])
def test_oos_exact_constant_evidence_retains_defined_zero(evaluate, constants, error_mode) -> None:
    with np.errstate(all=error_mode):
        result = evaluate(
            np.tile(constants, (12, 1)),
            [(np.arange(6), np.arange(6, 12))],
            benchmark=np.full(12, constants[0]),
        )
    assert result.mean_oos_sharpe == 0.0
    assert result.mean_oos_hold_sharpe == 0.0


def test_oos_exact_constant_selection_matches_independent_score(evaluate) -> None:
    performance = np.column_stack((np.full(12, 0.1), np.tile([0.01, 0.02, 0.03], 4)))
    result = evaluate(performance, [(np.arange(6), np.arange(6, 12))])
    # Correct constant score zero loses to the variable positive IS candidate.
    expected = math.sqrt(252) * 0.02 / math.sqrt(0.00008)
    assert result.mean_oos_sharpe == pytest.approx(expected)


def test_oos_nearly_constant_evidence_retains_native_arithmetic(evaluate) -> None:
    positive = np.tile([0.1, np.nextafter(0.1, 1), 0.1], 4)
    performance = np.column_stack((positive, -positive))
    expected = float(np.sqrt(252) * positive[6:].mean() / positive[6:].std(ddof=1))
    assert expected > 0
    with np.errstate(all="raise"):
        result = evaluate(performance, [(np.arange(6), np.arange(6, 12))])
    assert result.mean_oos_sharpe == expected


@pytest.mark.parametrize("role", ["performance", "benchmark"])
@pytest.mark.parametrize("kind", ["boolean", "string", "complex", "object", "temporal"])
def test_oos_refuses_original_nonreal_numeric_sources(evaluate, role, kind) -> None:
    performance = np.column_stack((np.arange(1, 5) / 100, -np.arange(1, 5) / 100))
    benchmark = np.arange(1, 5) / 100
    source = performance if role == "performance" else benchmark
    if kind == "boolean":
        source = source > 0
    elif kind == "string":
        source = source.astype(str)
    elif kind == "complex":
        source = source + 1j
    elif kind == "object":
        source = source.astype(object)
    else:
        source = np.arange(source.size).reshape(source.shape).astype("datetime64[D]")
    if role == "performance":
        performance = source
    else:
        benchmark = source
    with pytest.raises(ValueError, match=f"{role} must carry real numeric returns"):
        evaluate(performance, [(np.array([0, 1]), np.array([2, 3]))], benchmark=benchmark)


@pytest.mark.parametrize("role", ["performance", "benchmark"])
@pytest.mark.parametrize("row", [0, 2])
@pytest.mark.parametrize("missing", [np.nan, np.inf, -np.inf])
def test_oos_refuses_incomplete_evidence_before_selection(evaluate, role, row, missing) -> None:
    performance = np.column_stack((np.arange(1, 5) / 100, -np.arange(1, 5) / 100))
    benchmark = np.arange(1, 5) / 100
    if role == "performance":
        performance[row, 0] = missing
    else:
        benchmark[row] = missing
    with (
        np.errstate(all="raise"),
        pytest.raises(ValueError, match=f"{role} returns must be finite"),
    ):
        evaluate(performance, [(np.array([0, 1]), np.array([2, 3]))], benchmark=benchmark)


@pytest.mark.parametrize("dtype", [np.int16, np.uint16, np.float32, np.float64])
def test_oos_preserves_complete_numeric_source_oracle(evaluate, dtype) -> None:
    performance = np.array([[1, 2], [2, 1], [3, 4], [4, 3]], dtype=dtype)
    benchmark = np.array([1, 2, 3, 4], dtype=dtype)
    result = evaluate(performance, [(np.array([0, 1]), np.array([2, 3]))], benchmark=benchmark)
    expected = 7 / math.sqrt(2) * math.sqrt(252)
    assert result.mean_oos_sharpe == pytest.approx(expected)
    assert result.mean_oos_hold_sharpe == pytest.approx(expected)


def test_oos_preserves_finite_flat_singletons_and_absent_benchmark(evaluate) -> None:
    result = evaluate(np.zeros((2, 2)), [(np.array([0]), np.array([1]))])
    assert result.mean_oos_sharpe == 0
    assert result.mean_oos_hold_sharpe is None


@pytest.mark.parametrize("role", ["performance", "benchmark"])
def test_oos_refuses_masked_missing_observations(evaluate, role) -> None:
    performance = np.column_stack((np.arange(1, 5) / 100, -np.arange(1, 5) / 100))
    benchmark = np.arange(1, 5) / 100
    if role == "performance":
        performance = np.ma.array(performance, mask=[[True, False], [False, False]] * 2)
    else:
        benchmark = np.ma.array(benchmark, mask=[True, False, False, False])
    with pytest.raises(ValueError, match=f"{role} returns must be finite"):
        evaluate(performance, [(np.array([0, 1]), np.array([2, 3]))], benchmark=benchmark)


def test_oos_preserves_masked_array_without_missing_observations(evaluate) -> None:
    result = evaluate(
        np.ma.array(np.zeros((2, 2)), mask=False),
        [(np.array([0]), np.array([1]))],
        benchmark=np.ma.array(np.zeros(2), mask=False),
    )
    assert result.mean_oos_sharpe == 0 and result.mean_oos_hold_sharpe == 0


@pytest.mark.parametrize("role", ["performance", "benchmark"])
def test_oos_float_kernel_conversion_has_explicit_strict_mode_limit(evaluate, role) -> None:
    performance = np.zeros((2, 2))
    benchmark = np.zeros(2)
    source = np.full(
        performance.shape if role == "performance" else benchmark.shape,
        np.finfo(np.longdouble).max,
        dtype=np.longdouble,
    )
    if role == "performance":
        performance = source
    else:
        benchmark = source
    with np.errstate(all="raise"):
        if np.finfo(np.longdouble).max > np.longdouble(np.finfo(np.float64).max):
            with pytest.raises(ValueError, match=f"{role} returns must be finite"):
                evaluate(performance, [(np.array([0]), np.array([1]))], benchmark=benchmark)
        else:
            # Platforms with float64 longdouble have no conversion overflow; singleton scores stay valid.
            result = evaluate(performance, [(np.array([0]), np.array([1]))], benchmark=benchmark)
            assert result.mean_oos_sharpe == 0 and result.mean_oos_hold_sharpe == 0
