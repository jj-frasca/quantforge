"""Exact-translation PBO: literal gate failure, independent CSCV and provenance."""

import math
from decimal import Decimal, localcontext
from fractions import Fraction
from functools import cmp_to_key
from itertools import combinations
from typing import Literal
from unittest.mock import patch

import numpy as np
import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st
from numpy.typing import NDArray

from app.research.lab import calibration
from app.research.lab.gate import GateConfig
from app.validation import pbo

_V11 = "whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-v11"
_V12 = "whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-v12"
_V13 = "whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-sharpe-exact-translation-v13"
_V14 = _V13.removesuffix("-v13") + "-oos-exact-translation-v14"


def test_pbo_translation_advances_identity_and_preserves_historical_v11(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert calibration._TRIAL_ACCOUNTING_VERSION == _V14
    kwargs = {"n_per_param": 3, "config": GateConfig(), "refine": True, "refine_span": 0.25}
    current = calibration.calibration_search_version(["sma", "momentum"], **kwargs)
    assert current == "ece94d5f4a3d9713249f42ab7764128b348415487bdc411b608c2dc93f930080"
    monkeypatch.setattr(calibration, "_TRIAL_ACCOUNTING_VERSION", _V11)
    historical = calibration.calibration_search_version(["sma", "momentum"], **kwargs)
    assert historical == "8e2982a4d8fdbe76472df8cc9faeedf28d3b1e8a127cbf94b4ff40d0dfe5f175"
    assert current != historical


FloatArray = NDArray[np.float64]
Score = tuple[int, Fraction]
Record = tuple[tuple[int, ...], list[int], list[Fraction], Fraction]

_OFFSETS = np.array([[7, 10], [6, 12], [5, 5], [6, 9], [3, 9], [15, 4], [14, 13], [7, 14]])


def _moments(col: FloatArray) -> tuple[Fraction, Fraction]:
    x = [Fraction(float(v)) for v in col]
    mean = sum(x) / len(x)
    variance = sum((v - mean) ** 2 for v in x) / (len(x) - 1)
    return mean, variance


def _signed_squared_score(col: FloatArray) -> Score:
    mean, variance = _moments(col)
    if variance == 0:
        return (0, Fraction(0))
    return (int(mean > 0) - int(mean < 0), mean**2 / variance)


def _compare(a: Score, b: Score) -> int:
    if a[0] != b[0]:
        return int(a[0] > b[0]) - int(a[0] < b[0])
    if a[0] == 0:
        return 0
    return a[0] * (int(a[1] > b[1]) - int(a[1] < b[1]))


def _exact_cscv(matrix: FloatArray, n_splits: int = 4) -> tuple[Fraction, list[Record]]:
    groups = np.array_split(np.arange(len(matrix)), n_splits)
    records = []
    for ins in combinations(range(n_splits), n_splits // 2):
        outs = tuple(i for i in range(n_splits) if i not in ins)
        scores = []
        for subset in [ins, outs]:
            rows = np.concatenate([groups[i] for i in subset])
            scores.append([_signed_squared_score(c) for c in matrix[rows].T])
        maximum = max(scores[0], key=cmp_to_key(_compare))
        best = [i for i, s in enumerate(scores[0]) if _compare(s, maximum) == 0]
        indicators = []
        ranks = []
        for i in best:
            less = sum(_compare(s, scores[1][i]) < 0 for s in scores[1])
            equal = sum(_compare(s, scores[1][i]) == 0 for s in scores[1])
            rank = Fraction(less) + Fraction(equal + 1, 2)
            indicators.append(rank <= Fraction(len(scores[1]) + 1, 2))
            ranks.append(rank)
        records.append((ins, best, ranks, Fraction(sum(indicators), len(indicators))))
    return sum(record[3] for record in records) / len(records), records


def _score_oracle(block: FloatArray, col: int, precision: int = 800) -> float:
    native_mean = float(block.mean(axis=0)[col])
    _, variance = _moments(block[:, col])
    if variance == 0:
        return 0.0
    mean = Fraction(native_mean)
    with localcontext() as c:
        c.prec = precision
        return float(
            (Decimal(mean.numerator) / Decimal(mean.denominator))
            / (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
        )


@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
@pytest.mark.parametrize("permutation", [[0, 1], [1, 0]])
def test_public_literal_native_centering_false_gate_pass(mode: str, permutation: list[int]) -> None:
    matrix = (0.01 + _OFFSETS * math.ulp(0.01))[:, permutation]
    before = matrix.copy()
    expected, records = _exact_cscv(matrix)
    assert expected == Fraction(2, 3)
    assert [r[3] for r in records] == [1, 1, 0, 0, 1, 1]
    with np.errstate(all=mode):
        state = np.geterr()
        actual = pbo.probability_of_backtest_overfitting(matrix, n_splits=4)
        assert np.geterr() == state
    assert actual == float(expected)
    assert not actual < 0.5
    np.testing.assert_array_equal(matrix, before)


def test_literal_exact_split_winners_and_midpoint_ranks() -> None:
    matrix = 0.01 + _OFFSETS * math.ulp(0.01)
    _, records = _exact_cscv(matrix)
    assert [r[1] for r in records] == [[0], [1], [1], [1], [0], [1]]
    assert [r[2] for r in records] == [
        [Fraction(1)],
        [Fraction(1)],
        [Fraction(2)],
        [Fraction(2)],
        [Fraction(1)],
        [Fraction(1)],
    ]


@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("base", [0.01, 1e-100, 1.0, 1e100])
def test_original_native_mean_and_exact_translation_variance(sign: int, base: float) -> None:
    block = sign * (base + np.array([[0, 2], [1, 4], [2, 1], [4, 3], [8, 5]]) * math.ulp(base))
    before = block.copy()
    with np.errstate(all="raise"):
        state = np.geterr()
        actual = pbo._sharpe_per_config(block)
        assert np.geterr() == state
    for col in range(block.shape[1]):
        expected = _score_oracle(block, col)
        assert expected == _score_oracle(block, col, 200)
        assert actual[col] == pytest.approx(expected, rel=5e-14, abs=0)
    np.testing.assert_array_equal(block, before)


@settings(max_examples=60, deadline=None)
@example(offsets=_OFFSETS.tolist(), sign=1)
@given(
    offsets=st.lists(st.lists(st.integers(0, 15), min_size=2, max_size=2), min_size=8, max_size=8),
    sign=st.sampled_from([-1, 1]),
)
def test_public_exact_cscv_distinct_variances_property(offsets: list[list[int]], sign: int) -> None:
    matrix = sign * (0.01 + np.array(offsets) * math.ulp(0.01))
    groups = np.array_split(np.arange(8), 4)
    # Distinct exact variances certify ranks are separated; arbitrary rounded ties
    # and native numerator precision are outside this correction's universal claims.
    for subset in combinations(range(4), 2):
        block = matrix[np.concatenate([groups[i] for i in subset])]
        variances = [_moments(c)[1] for c in block.T]
        assume(all(v > 0 for v in variances) and variances[0] != variances[1])
    expected, _ = _exact_cscv(matrix)
    with np.errstate(all="raise"):
        actual = pbo.probability_of_backtest_overfitting(matrix, n_splits=4)
    assert actual == float(expected)
    assert 0 <= actual <= 1
    assert pbo.probability_of_backtest_overfitting(matrix[:, ::-1], n_splits=4) == actual


@pytest.mark.parametrize(
    "dtype", [np.float16, np.float32, np.float64, np.longdouble, np.int64, np.uint64]
)
def test_public_original_source_provenance_reaches_every_cached_half(
    dtype: type | str,
) -> None:
    matrix = np.array([[1, 2], [2, 1], [3, 3], [4, 2], [2, 4], [3, 1], [1, 3], [4, 4]], dtype=dtype)
    with patch.object(pbo, "_sharpe_per_config", wraps=pbo._sharpe_per_config) as helper:
        pbo.probability_of_backtest_overfitting(matrix, n_splits=4)
    assert helper.call_count == 6
    expected = np.dtype(dtype).kind == "f" and np.dtype(dtype).itemsize == 8
    assert all(call.kwargs == {"exact_translation": expected} for call in helper.call_args_list)


@pytest.mark.parametrize(
    "values",
    [
        [1.0, math.nextafter(2.0, math.inf)],
        [-1.0, -math.nextafter(2.0, math.inf)],
        [0.0, 1.0, 2.0],
        [-1.0, 1.0, 2.0],
        [1.0, 2.0, 4.0],
    ],
)
def test_outside_sterbenz_columns_remain_native_exact(values: list[float]) -> None:
    block = np.column_stack([values, np.zeros(len(values))])
    mean = block.mean(axis=0)
    std = block.std(axis=0, ddof=1)
    expected = np.array([mean[0] / std[0], 0.0])
    actual = pbo._sharpe_per_config(block)
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("sign", [-1, 1])
def test_two_min_inclusive_boundary_retains_sample_definition(sign: int) -> None:
    block = sign * np.array([[1.0, 1.0], [2.0, math.nextafter(2.0, 0.0)], [1.25, 1.75]])
    actual = pbo._sharpe_per_config(block)
    for col in range(2):
        assert actual[col] == pytest.approx(_score_oracle(block, col), rel=5e-14, abs=0)


@pytest.mark.parametrize("base,n", [(0.01, 4), (1e-100, 3), (1.0, 7)])
def test_explicit_original_source_exclusion_retains_native_exact(base: float, n: int) -> None:
    block = np.column_stack([base + np.arange(n) * math.ulp(base), np.zeros(n)])
    expected = np.array([block.mean(axis=0)[0] / block.std(axis=0, ddof=1)[0], 0.0])
    actual = pbo._sharpe_per_config(block, exact_translation=False)
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("scale", [1e-200, 1e200])
@pytest.mark.parametrize("mode", ["ignore", "raise"])
def test_existing_unmeasurable_native_refusal_precedes_translation(scale: float, mode: str) -> None:
    block = np.array([[1.0, 2.0], [2.0, 1.0], [3.0, 4.0], [4.0, 3.0]]) * scale
    with np.errstate(all=mode), pytest.raises(ValueError, match="measurable"):
        pbo._sharpe_per_config(block)


@pytest.mark.parametrize("value", [0.0, 0.1, 1e-200, 1e200, np.finfo(float).max])
def test_exact_constant_columns_retain_zero_before_moments(value: float) -> None:
    block = np.full((8, 2), value)
    with np.errstate(all="raise"):
        np.testing.assert_array_equal(pbo._sharpe_per_config(block), [0.0, 0.0])
        assert pbo.probability_of_backtest_overfitting(block, n_splits=4) == 1.0


@pytest.mark.parametrize("dtype", [bool, object, complex, "U8"])
def test_original_bad_source_refuses_before_cached_scoring(dtype: type | str) -> None:
    matrix = np.ones((8, 2), dtype=dtype)
    with (
        patch.object(
            pbo,
            "_sharpe_per_config",
            side_effect=AssertionError("original evidence guard"),
        ),
        pytest.raises(ValueError),
    ):
        pbo.probability_of_backtest_overfitting(matrix, n_splits=4)


def test_source_mask_guard_precedes_translation() -> None:
    matrix = np.ma.array(np.ones((8, 2)), mask=False)
    matrix.mask[0, 0] = True
    with (
        patch.object(pbo, "_sharpe_per_config", side_effect=AssertionError("mask guard")),
        pytest.raises(ValueError),
    ):
        pbo.probability_of_backtest_overfitting(matrix, n_splits=4)


def test_duplicate_and_constant_candidates_preserve_tie_extension() -> None:
    original = 0.01 + _OFFSETS * math.ulp(0.01)
    matrix = np.column_stack([original, original[:, 0], np.zeros(len(original))])
    expected, _ = _exact_cscv(matrix)
    actual = pbo.probability_of_backtest_overfitting(matrix, n_splits=4)
    assert actual == float(expected)
    assert pbo.probability_of_backtest_overfitting(matrix[:, [3, 2, 1, 0]], n_splits=4) == actual


@pytest.mark.parametrize("layout", ["C", "F"])
def test_original_full_block_reduction_layout_mean_retained(
    layout: Literal["C", "F"],
) -> None:
    block = np.array(0.01 + _OFFSETS[:4] * math.ulp(0.01), order=layout)
    native_mean = block.mean(axis=0)
    actual = pbo._sharpe_per_config(block)
    for col in range(2):
        assert actual[col] == pytest.approx(_score_oracle(block, col), rel=5e-14, abs=0)
    assert np.array_equal(native_mean, block.mean(axis=0))


@pytest.mark.parametrize("layout", ["C", "F"])
def test_native_full_block_mean_reaches_translation_without_reduction(
    layout: Literal["C", "F"],
) -> None:
    block = np.array(0.01 + _OFFSETS[:4] * math.ulp(0.01), order=layout)
    original_mean = block.mean(axis=0)
    with patch.object(
        pbo,
        "_sharpe_from_exact_float64_translation",
        create=True,
        return_value=np.array([17.0, 23.0]),
    ) as helper:
        actual = pbo._sharpe_per_config(block)
    np.testing.assert_array_equal(actual, [17.0, 23.0])
    helper.assert_called_once()
    np.testing.assert_array_equal(helper.call_args.args[0], block)
    np.testing.assert_array_equal(helper.call_args.args[1], original_mean)


def test_two_min_boundary_selected_before_any_new_ratio() -> None:
    block = np.array([[1.0, 1.0], [2.0, math.nextafter(2.0, 0.0)]])
    with patch.object(
        pbo,
        "_sharpe_from_exact_float64_translation",
        create=True,
        return_value=np.array([17.0, 23.0]),
    ) as helper:
        np.testing.assert_array_equal(pbo._sharpe_per_config(block), [17.0, 23.0])
    helper.assert_called_once()


@pytest.mark.parametrize(
    "block",
    [
        np.ones((4, 2)),
        np.array([[-1.0, 0.0], [1.0, 1.0], [2.0, 2.0]]),
        np.array(
            [
                [1.0, -1.0],
                [math.nextafter(2.0, math.inf), -math.nextafter(2.0, math.inf)],
            ]
        ),
    ],
)
def test_constant_or_outside_columns_do_not_call_translation(block: FloatArray) -> None:
    with patch.object(
        pbo,
        "_sharpe_from_exact_float64_translation",
        create=True,
        side_effect=AssertionError("outside or constant"),
    ):
        pbo._sharpe_per_config(block)


@pytest.mark.parametrize("base,n", [(0.01, 4), (1e-100, 3), (1.0, 7)])
@pytest.mark.parametrize("sign", [-1, 1])
def test_native_positive_column_variance_literal_displacement(
    base: float, n: int, sign: int
) -> None:
    offsets = np.arange(n)
    block = sign * (base + np.column_stack([offsets, 3 * offsets]) * math.ulp(base))
    with np.errstate(all="raise"):
        assert np.all(block.std(axis=0, ddof=1) > 0)
        actual = pbo._sharpe_per_config(block)
    for col in range(2):
        assert actual[col] == pytest.approx(_score_oracle(block, col), rel=5e-14, abs=0)


def test_frozen_fixture_rejects_actual_gate_pbo_component() -> None:
    from app.research.lab.gate import GateConfig, GateResult, GraduationGate
    from app.research.lab.holdout import HoldoutScore
    from app.validation.report import ValidationReport

    matrix = 0.01 + _OFFSETS * math.ulp(0.01)
    measured = pbo.probability_of_backtest_overfitting(matrix, n_splits=4)
    exact, _ = _exact_cscv(matrix)
    config = GateConfig()
    assert config.pbo_max == 0.5
    holdout = HoldoutScore(sharpe=0.8, total_return=0.1, n_bars=252, buy_and_hold_sharpe=0.0)

    def evaluate(value: float) -> GateResult:
        report = ValidationReport(
            strategy_name="sma_crossover",
            observed_sharpe=1.5,
            deflated_sharpe=1.0,
            pbo=value,
            parameter_stability_score=0.8,
            n_walk_forward_splits=5,
            n_purged_folds=5,
        )
        return GraduationGate().evaluate(
            report=report,
            track_record_years=12.0,
            n_trials=50,
            holdout=holdout,
            config=config,
        )

    reference = evaluate(float(exact))
    actual = evaluate(measured)
    # Other report evidence is deliberately synthetic and positive. This proves
    # the live PBO component's arithmetic, not an actual historical graduation.
    assert reference.pbo_ok is False
    assert actual.pbo_ok is reference.pbo_ok
    assert actual.passed is False
    assert all(
        getattr(actual, key)
        for key in [
            "dsr_ok",
            "stability_ok",
            "mintrl_ok",
            "holdout_ok",
            "beats_buy_and_hold_ok",
        ]
    )
    assert actual.gate_config_version == config.version_hash
    assert any("pbo" in reason.lower() for reason in actual.reasons)


@settings(max_examples=60, deadline=None)
@example(exponent=-333, sign=1, offsets=[[0, 0], [1, 3], [2, 6]])
@given(
    exponent=st.integers(-450, 490),
    sign=st.sampled_from([-1, 1]),
    offsets=st.lists(st.lists(st.integers(0, 64), min_size=2, max_size=2), min_size=2, max_size=20),
)
def test_translated_column_variance_known_native_mean_property(
    exponent: int, sign: int, offsets: list[list[int]]
) -> None:
    base = math.ldexp(1.0, exponent)
    block = sign * (base + np.array(offsets) * math.ulp(base))
    before = block.copy()
    with np.errstate(all="raise"):
        state = np.geterr()
        actual = pbo._sharpe_per_config(block)
        assert np.geterr() == state
    for col in range(2):
        expected = _score_oracle(block, col)
        if np.all(block[:, col] == block[0, col]):
            assert actual[col] == 0
        else:
            assert actual[col] == pytest.approx(expected, rel=5e-14, abs=0)
    np.testing.assert_array_equal(block, before)


@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
def test_positive_partial_underflow_native_std_remains_eligible(mode: str) -> None:
    block = np.array([[1.0, 1.2], [1.1, 1.3], [1.5, 1.4]]) * 1e-160
    with np.errstate(all="ignore"):
        assert np.all(block.std(axis=0, ddof=1) > 0)
    with np.errstate(all=mode):
        actual = pbo._sharpe_per_config(block)
    for col in range(2):
        assert actual[col] == pytest.approx(_score_oracle(block, col), rel=5e-14, abs=0)


def test_accepted_native_zero_mean_keeps_zero_without_translation() -> None:
    class ZeroMeanArray(np.ndarray):
        def mean(self, *args: object, **kwargs: object) -> FloatArray:
            return np.zeros(self.shape[1], dtype=np.float64)

    block = np.array([[1.0, 1.0], [1.25, 1.5], [1.5, 2.0]]).view(ZeroMeanArray)
    with patch.object(
        pbo,
        "_sharpe_from_exact_float64_translation",
        create=True,
        side_effect=AssertionError("zero native mean stays native"),
    ):
        np.testing.assert_array_equal(pbo._sharpe_per_config(block), [0.0, 0.0])
