"""ADR291: represented dispersion with the original one-dimensional native mean."""

import math
from decimal import Decimal, localcontext
from fractions import Fraction
from types import ModuleType
from unittest.mock import patch

import numpy as np
import numpy.typing as npt
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from app.research.lab import calibration
from app.research.lab.gate import GateConfig
from app.validation import purged_cv, walk_forward
from app.validation.purged_cv import PurgedCVFoldResult, PurgedCVResult
from app.validation.walk_forward import WalkForwardResult, WalkForwardSplitResult

_V13 = "whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-sharpe-exact-translation-v13"
_V14 = _V13.removesuffix("-v13") + "-oos-exact-translation-v14"
_MODULES = [walk_forward, purged_cv]
_HELPER = "_certified_float64_sharpe"


def _native(values: npt.NDArray[np.float64]) -> float:
    if len(values) < 2 or np.all(values == values[0]):
        return 0.0
    with np.errstate(all="ignore"):
        std = float(values.std(ddof=1))
        mean = float(values.mean())
        if not math.isfinite(mean) or not math.isfinite(std) or std <= 0:
            raise ValueError("measurable")
        score = float(np.sqrt(252) * mean / std)
    if not math.isfinite(score):
        raise ValueError("measurable")
    return score


def _oracle(values: npt.NDArray[np.float64], precision: int = 800) -> float:
    original = [Fraction(float(v)) for v in values]
    center = sum(original) / len(original)
    variance = sum((v - center) ** 2 for v in original) / (len(original) - 1)
    numerator = Fraction(float(values.mean()))
    with localcontext() as context:
        context.prec = precision
        return float(
            Decimal(252).sqrt()
            * (Decimal(numerator.numerator) / Decimal(numerator.denominator))
            / (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
        )


def _evaluate(
    module: ModuleType,
    performance: npt.NDArray,
    splits: list[tuple[npt.NDArray, npt.NDArray]],
    benchmark: npt.NDArray | None = None,
) -> WalkForwardResult | PurgedCVResult:
    kwargs = {"benchmark": benchmark}
    if module is purged_cv:
        return module.purged_cv_evaluate(performance, splits, embargo=0, **kwargs)
    return module.walk_forward_evaluate(performance, splits, **kwargs)


def _record(
    result: WalkForwardResult | PurgedCVResult,
) -> WalkForwardSplitResult | PurgedCVFoldResult:
    return result.splits[0] if hasattr(result, "splits") else result.folds[0]


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
def test_oos_frozen_train_argmax_uses_represented_variance(module: ModuleType, mode: str) -> None:
    offsets = np.array([[5, 5], [6, 9], [14, 13], [7, 14], [7, 10], [6, 12], [3, 9], [15, 4]])
    matrix = 0.01 + offsets * math.ulp(0.01)
    before = matrix.copy()
    splits = [(np.arange(4), np.arange(4, 8))]
    expected_train = [_oracle(matrix[:4, c]) for c in range(2)]
    assert expected_train[0] > expected_train[1]
    with np.errstate(all=mode):
        state = np.geterr()
        result = _evaluate(module, matrix, splits, matrix[:, 0])
        assert np.geterr() == state
    record = _record(result)
    assert record.selected_config == 0
    assert record.oos_sharpe == pytest.approx(_oracle(matrix[4:, 0]), rel=5e-14, abs=0)
    assert result.mean_oos_hold_sharpe == pytest.approx(_oracle(matrix[4:, 0]), rel=5e-14, abs=0)
    if module is walk_forward:
        assert record.is_sharpe == pytest.approx(expected_train[0], rel=5e-14, abs=0)
        assert result.efficiency == pytest.approx(record.oos_sharpe / record.is_sharpe)
    np.testing.assert_array_equal(matrix, before)


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize("base,n", [(1e-100, 3), (0.01, 4), (0.1, 7), (1.0, 9)])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
def test_oos_scalar_centering_matches_exact_variance(
    module: ModuleType, base: float, n: int, sign: int, mode: str
) -> None:
    values = sign * (base + np.arange(n) * math.ulp(base))
    expected = _oracle(values)
    assert expected == _oracle(values, 200)
    with np.errstate(all=mode):
        state = np.geterr()
        actual = module._sharpe(values)
        assert np.geterr() == state
    assert actual == pytest.approx(expected, rel=5e-14, abs=0)


@pytest.mark.parametrize("module", _MODULES)
@settings(max_examples=60, deadline=None)
@example(exponent=-333, sign=1, offsets=[0, 1, 2])
@given(
    exponent=st.integers(-450, 450),
    sign=st.sampled_from([-1, 1]),
    offsets=st.lists(st.integers(0, 64), min_size=2, max_size=30),
)
def test_oos_binary_grid_retains_exact_variance_property(
    module: ModuleType, exponent: int, sign: int, offsets: list[int]
) -> None:
    base = math.ldexp(1.0, exponent)
    values = sign * (base + np.array(offsets) * math.ulp(base))
    with np.errstate(all="raise"):
        actual = module._sharpe(values)
    if len(set(offsets)) == 1:
        assert actual == 0
    else:
        assert actual == pytest.approx(_oracle(values), rel=5e-14, abs=0)


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize(
    "values",
    [[1.0, 2.0], [-1.0, -2.0], [1.0, math.nextafter(2.0, 0)], [1.0, 1.125, 1.75]],
)
def test_oos_certified_boundary_retains_actual_native_mean(
    module: ModuleType, values: list[float]
) -> None:
    observations = np.array(values)
    mean = float(observations.mean())
    with patch.object(module, _HELPER, create=True, return_value=17.0) as helper:
        actual = module._sharpe(observations)
    assert actual == 17.0
    helper.assert_called_once()
    np.testing.assert_array_equal(helper.call_args.args[0], observations)
    assert helper.call_args.args[1] == mean
    assert helper.call_args.args[2] == _native(observations)


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize(
    "values",
    [
        [1.0, math.nextafter(2.0, math.inf)],
        [-1.0, -math.nextafter(2.0, math.inf)],
        [0.0, 1.0, 2.0],
        [-1.0, 1.0, 2.0],
        [1.0, 2.0, 4.0],
        [-1.0, 0.0, 1.0],
    ],
)
def test_oos_outside_certificate_retains_native_exact(
    module: ModuleType, values: list[float]
) -> None:
    observations = np.array(values)
    assert module._sharpe(observations) == _native(observations)


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize(
    "dtype",
    [np.float16, np.float32, np.float64, np.longdouble, np.int64, np.uint64, ">f8"],
)
@pytest.mark.parametrize("role", ["matrix", "benchmark"])
def test_oos_original_source_provenance_survives_conversion(
    module: ModuleType, dtype: str | type, role: str
) -> None:
    matrix = np.tile(np.array([[1.0, 1.5], [1.125, 1.25], [1.5, 1.875]]), (2, 1))
    benchmark = matrix[:, 0].copy()
    if role == "matrix":
        matrix = matrix.astype(dtype)
    else:
        benchmark = benchmark.astype(dtype)
    with patch.object(module, "_sharpe", wraps=module._sharpe) as scorer:
        _evaluate(module, matrix, [(np.arange(3), np.arange(3, 6))], benchmark)
    matrix_flag = matrix.dtype.kind == "f" and matrix.dtype.itemsize == 8
    benchmark_flag = benchmark.dtype.kind == "f" and benchmark.dtype.itemsize == 8
    flags = [call.kwargs.get("exact_translation") for call in scorer.call_args_list]
    # WF holds are scored last; purged holds precede train selection.
    expected = (
        [matrix_flag] * 3 + [benchmark_flag]
        if module is walk_forward
        else [benchmark_flag] + [matrix_flag] * 3
    )
    assert flags == expected


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize("dtype", [np.float32, np.int64, np.uint64, np.longdouble])
def test_oos_non64_source_retains_complete_public_native_result(
    module: ModuleType, dtype: type
) -> None:
    matrix = np.tile(np.array([[2, 3], [3, 4], [4, 5]]), (2, 1)).astype(dtype)
    materialized = matrix.astype(np.float64)
    benchmark = matrix[:, 0]
    result = _evaluate(module, matrix, [(np.arange(3), np.arange(3, 6))], benchmark)
    best = int(np.argmax([_native(materialized[:3, c]) for c in range(2)]))
    assert _record(result).selected_config == best
    assert result.mean_oos_sharpe == _native(materialized[3:, best])
    assert result.mean_oos_hold_sharpe == _native(materialized[3:, 0])


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize(
    "values",
    [
        [1e200, 1.5e200, 1.25e200],
        [1e-200, 1.5e-200, 1.25e-200],
        [1e308, 1.5e308],
        [math.ulp(0.0), 2 * math.ulp(0.0)],
    ],
)
def test_oos_original_native_failure_precedes_translation(
    module: ModuleType, values: list[float]
) -> None:
    with (
        patch.object(
            module, _HELPER, create=True, side_effect=AssertionError("must not recover")
        ) as helper,
        np.errstate(all="raise"),
        pytest.raises(ValueError, match="measurable"),
    ):
        module._sharpe(np.array(values))
    helper.assert_not_called()


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize("values", [[1.0], [0.1, 0.1, 0.1], [1e308, 1e308], [1e-300, 1e-300]])
def test_oos_short_and_constant_precede_translation(
    module: ModuleType, values: list[float]
) -> None:
    with patch.object(
        module, _HELPER, create=True, side_effect=AssertionError("must not translate")
    ) as helper:
        assert module._sharpe(np.array(values)) == 0
    helper.assert_not_called()


def test_oos_translation_advances_identity_and_restores_historical_v13(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert calibration._TRIAL_ACCOUNTING_VERSION == _V14
    kwargs = {
        "n_per_param": 3,
        "config": GateConfig(),
        "refine": True,
        "refine_span": 0.25,
    }
    current = calibration.calibration_search_version(["sma", "momentum"], **kwargs)
    assert current == "ece94d5f4a3d9713249f42ab7764128b348415487bdc411b608c2dc93f930080"
    monkeypatch.setattr(calibration, "_TRIAL_ACCOUNTING_VERSION", _V13)
    historical = calibration.calibration_search_version(["sma", "momentum"], **kwargs)
    assert historical == "d89985d6dc2affeceff9e72c73a9e07ecd76508b43e5948a5a1ac865c491648d"
    assert current != historical


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize("sign", [-1, 1])
def test_oos_positive_partial_underflow_std_uses_translation(module: ModuleType, sign: int) -> None:
    values = sign * np.array([1e-160, 1.5e-160, 1.25e-160])
    with np.errstate(all="ignore"):
        assert values.std(ddof=1) > 0
    expected = _oracle(values)
    assert expected == _oracle(values, 200)
    with np.errstate(all="raise"):
        state = np.geterr()
        actual = module._sharpe(values)
        assert np.geterr() == state
    assert actual == pytest.approx(expected, rel=5e-14, abs=0)


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize(
    "endpoint,eligible",
    [
        (2.0, True),
        (math.nextafter(2.0, 0), True),
        (math.nextafter(2.0, math.inf), False),
    ],
)
def test_oos_shared_certificate_inclusive_endpoint(
    module: ModuleType, sign: int, endpoint: float, eligible: bool
) -> None:
    values = sign * np.array([1.0, endpoint])
    with np.errstate(all="raise"):
        actual = getattr(module, _HELPER)(values, float(values.mean()), 123.0)
    if eligible:
        assert actual == pytest.approx(_oracle(values), rel=5e-14, abs=0)
    else:
        assert actual == 123.0


@pytest.mark.parametrize("module", _MODULES)
@pytest.mark.parametrize(
    "matrix_dtype,benchmark_dtype",
    [
        (np.float64, np.longdouble),
        (np.longdouble, np.float64),
        (np.float32, np.float64),
        (np.float64, np.float32),
    ],
)
def test_oos_sensitive_matrix_and_benchmark_sources_are_independent(
    module: ModuleType, matrix_dtype: type, benchmark_dtype: type
) -> None:
    offsets = np.array([[5, 5], [6, 9], [14, 13], [7, 14], [7, 10], [6, 12], [3, 9], [15, 4]])
    original = 0.01 + offsets * math.ulp(0.01)
    matrix = original.astype(matrix_dtype)
    benchmark = original[:, 0].astype(benchmark_dtype)
    converted = matrix.astype(np.float64)
    hold = benchmark.astype(np.float64)[4:]
    use_matrix = matrix.dtype.kind == "f" and matrix.dtype.itemsize == 8
    train_scores = [
        _oracle(converted[:4, c]) if use_matrix else _native(converted[:4, c]) for c in range(2)
    ]
    best = int(np.argmax(train_scores))
    use_hold = benchmark.dtype.kind == "f" and benchmark.dtype.itemsize == 8
    expected_hold = _oracle(hold) if use_hold else _native(hold)
    test = converted[4:, best]
    expected_oos = _oracle(test) if use_matrix else _native(test)
    result = _evaluate(module, matrix, [(np.arange(4), np.arange(4, 8))], benchmark)
    assert _record(result).selected_config == best
    if use_matrix:
        assert result.mean_oos_sharpe == pytest.approx(expected_oos, rel=5e-14, abs=0)
    else:
        assert result.mean_oos_sharpe == expected_oos
    if use_hold:
        assert result.mean_oos_hold_sharpe == pytest.approx(expected_hold, rel=5e-14, abs=0)
    else:
        assert result.mean_oos_hold_sharpe == expected_hold
