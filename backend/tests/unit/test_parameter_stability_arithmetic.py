"""ADR-324: native nonfinite moments cannot become finite stability evidence."""

import math
from dataclasses import asdict

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.parameter_stability import parameter_stability
from app.validation.report import ValidationReport


@pytest.mark.parametrize("values", [[1e155, 2e155], [-1e155, -2e155], [-1e155, 1e155]])
def test_overflowed_dispersion_cannot_publish_report_accepted_zero(values: list[float]) -> None:
    with (
        np.errstate(over="ignore", invalid="ignore"),
        pytest.raises(ValueError, match=r"stability reductions.*finite"),
    ):
        result = parameter_stability(values)
        # Before the guard this real report accepted the finite score from stdInf.
        ValidationReport(
            strategy_name="witness",
            observed_sharpe=1.0,
            deflated_sharpe=0.5,
            pbo=0.1,
            parameter_stability_score=result.stability_score,
            n_walk_forward_splits=0,
            n_purged_folds=0,
        )


@pytest.mark.parametrize(
    "values",
    [[1e308, 1e308], [-1e308, -1e308], [1e308, -1e308], [1e155, 2e155]],
)
@pytest.mark.parametrize("policy", ["ignore", "warn"])
def test_nonfinite_native_reductions_refuse_without_changing_policy(
    values: list[float], policy: str
) -> None:
    with np.errstate(all=policy):
        before = np.geterr().copy()
        if policy == "warn":
            with (
                pytest.warns(RuntimeWarning),
                pytest.raises(ValueError, match=r"stability reductions.*finite"),
            ):
                parameter_stability(values)
        else:
            with pytest.raises(ValueError, match=r"stability reductions.*finite"):
                parameter_stability(values)
        assert np.geterr() == before


@pytest.mark.parametrize("values", [[1e155, 2e155], [1e308, 1e308], [1e308, -1e308]])
def test_native_raise_policy_keeps_floating_point_exception(values: list[float]) -> None:
    with np.errstate(all="raise"):
        before = np.geterr().copy()
        with pytest.raises(FloatingPointError):
            parameter_stability(values)
        assert np.geterr() == before


def test_original_minimum_and_leaf_validation_precedence_remains() -> None:
    with np.errstate(all="raise"):
        with pytest.raises(ValueError, match="need >= 2"):
            parameter_stability([math.inf])
        with pytest.raises(ValueError, match=r"Sharpe observations.*finite real"):
            parameter_stability([math.inf, 1e308])


@pytest.mark.parametrize("values", [[0.0, 0.0], [1.0, 1.0], [-1.0, -1.0], [1e100, 1e100]])
def test_measurable_exact_constants_keep_the_original_summary(values: list[float]) -> None:
    result = parameter_stability(values)
    assert result.mean_sharpe == values[0]
    assert result.std_sharpe == 0.0
    assert result.min_sharpe == result.max_sharpe == values[0]
    assert result.fraction_profitable == float(values[0] > 0)
    assert result.stability_score == 1.0


def test_ordinary_finite_reductions_keep_native_operations() -> None:
    values = [0.1, 0.4, -0.2, 0.8]
    arr = np.asarray(values, dtype=np.float64)
    expected_mean = float(arr.mean())
    expected_std = float(arr.std(ddof=1))
    expected_cv = expected_std / (abs(expected_mean) + 1e-9)
    result = parameter_stability(values)
    assert result.mean_sharpe == expected_mean
    assert result.std_sharpe == expected_std
    assert result.stability_score == float(np.clip(1.0 / (1.0 + expected_cv), 0.0, 1.0))


@given(exponent=st.integers(155, 300))
def test_finite_input_does_not_certify_overflowed_sample_dispersion(exponent: int) -> None:
    value = 10.0**exponent
    values = [value, 2 * value]
    assert all(math.isfinite(observation) for observation in values)
    with np.errstate(over="ignore", invalid="ignore"):
        before = np.geterr().copy()
        with pytest.raises(ValueError, match=r"stability reductions.*finite"):
            parameter_stability(values)
        assert np.geterr() == before


@given(
    numerators=st.lists(st.integers(-16, 16), min_size=2, max_size=32),
    exponent=st.integers(-20, 20),
)
def test_measurable_dyadic_summaries_remain_finite_and_bounded(
    numerators: list[int], exponent: int
) -> None:
    values = [math.ldexp(numerator, exponent) for numerator in numerators]
    result = parameter_stability(values)
    assert all(math.isfinite(value) for value in asdict(result).values())
    assert min(values) <= result.mean_sharpe <= max(values)
    assert result.std_sharpe >= 0
    assert result.min_sharpe == min(values) and result.max_sharpe == max(values)
    assert result.fraction_profitable == sum(value > 0 for value in values) / len(values)
    assert 0 <= result.stability_score <= 1
