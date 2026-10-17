"""ADR-310: full-price posterior checked by independent joint conditioning."""

from fractions import Fraction
from importlib import import_module
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

LAW = {"rho": 0.5, "level_vol": 0.01, "deviation_vol": 0.02, "drift": 0.0, "start_price": 1.0}


def _posterior(source: Any, **changes: Any) -> Any:
    try:
        module = import_module("app.research.lab.band_posterior")
    except ModuleNotFoundError:
        pytest.fail("ADR-310 posterior implementation is missing")
    return module.band_price_posterior(source, **(LAW | changes))


def _solve(matrix: list[list[Fraction]], values: list[Fraction]) -> list[Fraction]:
    rows = [[*row, value] for row, value in zip(matrix, values, strict=True)]
    for column in range(len(rows)):
        pivot = next(i for i in range(column, len(rows)) if rows[i][column])
        rows[column], rows[pivot] = rows[pivot], rows[column]
        divisor = rows[column][column]
        rows[column] = [value / divisor for value in rows[column]]
        for i in range(len(rows)):
            if i != column:
                multiplier = rows[i][column]
                rows[i] = [
                    left - multiplier * right
                    for left, right in zip(rows[i], rows[column], strict=True)
                ]
    return [row[-1] for row in rows]


def _joint_oracle(
    observations: list[Fraction],
    rho: Fraction,
    level: Fraction,
    deviation: Fraction,
    drift: Fraction,
) -> tuple[list[float], list[float]]:
    q, noise = deviation**2 * (1 - rho**2), level**2

    def covariance(i: int, j: int) -> Fraction:
        return q * sum((rho ** (i + j - 2 * k) for k in range(min(i, j) + 1)), Fraction(0))

    means, variances = [], []
    for i in range(len(observations)):
        matrix = [
            [covariance(j, k) + noise * (min(j, k) + 1) for k in range(i + 1)] for j in range(i + 1)
        ]
        cross = [covariance(i, j) for j in range(i + 1)]
        centered = [observations[j] - (j + 1) * drift for j in range(i + 1)]
        means.append(
            float(sum(a * b for a, b in zip(cross, _solve(matrix, centered), strict=True)))
        )
        variances.append(
            float(
                covariance(i, i)
                - sum(a * b for a, b in zip(cross, _solve(matrix, cross), strict=True))
            )
        )
    return means, variances


def test_posterior_assimilates_first_price_and_full_information_gain() -> None:
    result = _posterior(np.array([0.0, 0.01]))
    np.testing.assert_allclose(result.deviation_mean, [0.0, 0.01 * 45 / 67], rtol=1e-14)
    assert result.deviation_variance[0] == pytest.approx(0.000075)
    assert result.deviation_mean[1] != pytest.approx(0.004)
    first = _posterior(np.array([0.01]))
    assert first.deviation_mean[0] == pytest.approx(0.0075)


@pytest.mark.parametrize("rho", [-0.5, 0.0, 0.5, 0.9])
@pytest.mark.parametrize("level", [0.0, 0.01, 0.02])
def test_posterior_matches_exact_full_joint_gaussian_oracle(rho: float, level: float) -> None:
    observations = [Fraction(0), Fraction(1, 100), Fraction(-1, 250), Fraction(7, 1000)]
    drift = Fraction(3, 10000)
    expected = _joint_oracle(
        observations, Fraction(str(rho)), Fraction(str(level)), Fraction(1, 50), drift
    )
    result = _posterior(
        np.array([float(y) for y in observations]), rho=rho, level_vol=level, drift=float(drift)
    )
    np.testing.assert_allclose(result.deviation_mean, expected[0], rtol=1e-12, atol=1e-16)
    np.testing.assert_allclose(result.deviation_variance, expected[1], rtol=1e-12, atol=1e-18)


@given(
    st.lists(st.integers(-20, 20), min_size=1, max_size=5),
    st.integers(-8, 8),
    st.sampled_from([0, 1, 2]),
    st.integers(-3, 3),
)
def test_posterior_joint_oracle_prefix_and_path_independent_variance_properties(
    values: list[int],
    coefficient: int,
    noise: int,
    drift_units: int,
) -> None:
    rho, level, drift = (
        Fraction(coefficient, 10),
        Fraction(noise, 100),
        Fraction(drift_units, 10000),
    )
    observations = [Fraction(value, 1000) for value in values]
    source = np.array([float(value) for value in observations])
    law = {"rho": float(rho), "level_vol": float(level), "drift": float(drift)}
    result = _posterior(source, **law)
    oracle = _joint_oracle(observations, rho, level, Fraction(1, 50), drift)
    np.testing.assert_allclose(result.deviation_mean, oracle[0], rtol=1e-11, atol=1e-16)
    np.testing.assert_allclose(result.deviation_variance, oracle[1], rtol=1e-11, atol=1e-18)
    other = _posterior(source + 0.123, **law)
    np.testing.assert_array_equal(result.deviation_variance, other.deviation_variance)
    assert np.isfinite(result.deviation_mean).all()
    assert np.all(result.deviation_variance >= 0)
    for end in range(1, len(source) + 1):
        prefix = _posterior(source[:end], **law)
        np.testing.assert_array_equal(prefix.deviation_mean, result.deviation_mean[:end])
        np.testing.assert_array_equal(prefix.deviation_variance, result.deviation_variance[:end])


@pytest.mark.parametrize("drift", [-0.001, 0.0, 0.001])
def test_posterior_zero_level_noise_is_exactly_observable_with_known_start(drift: float) -> None:
    log_start = np.log(100.0)
    source = log_start + np.array([0.01, -0.003, 0.02, 0.0])
    result = _posterior(source, level_vol=0.0, drift=drift, start_price=100.0)
    np.testing.assert_allclose(
        result.deviation_mean, source - log_start - np.arange(1, 5) * drift, atol=1e-15
    )
    np.testing.assert_array_equal(result.deviation_variance, np.zeros(4))


@pytest.mark.parametrize("source", [np.array([]), np.array([0.01])])
def test_posterior_small_sources_have_owned_finite_float64_outputs(source: Any) -> None:
    result = _posterior(source)
    for output in result:
        assert output.shape == source.shape and output.dtype == np.float64
        assert output.flags.owndata and np.isfinite(output).all()
        assert not np.shares_memory(output, source)
    assert not np.shares_memory(result.deviation_mean, result.deviation_variance)


@pytest.mark.parametrize(
    "source",
    [
        [0.0, 0.1],
        (0.0, 0.1),
        np.array(0.0),
        np.zeros((2, 2)),
        np.array([True]),
        np.array(["0.1"]),
        np.array([0.1], dtype=object),
        np.array([1 + 0j]),
        np.array([np.nan]),
        np.array([np.inf]),
        np.ma.array([0.1], mask=[True]),
    ],
)
def test_posterior_refuses_original_invalid_observations(source: Any) -> None:
    with pytest.raises(ValueError):
        _posterior(source)


@pytest.mark.parametrize("field", list(LAW))
@pytest.mark.parametrize(
    "value", [True, np.bool_(False), "0.1", float("nan"), float("inf"), 10**400]
)
def test_posterior_refuses_original_invalid_law_even_empty(field: str, value: Any) -> None:
    with pytest.raises(ValueError):
        _posterior(np.array([]), **{field: value})


@pytest.mark.parametrize(
    "changes",
    [
        {"rho": 1.0},
        {"rho": -1.0},
        {"level_vol": -0.1},
        {"deviation_vol": 0.0},
        {"start_price": 0.0},
        {"start_price": -1.0},
        {"rho": Fraction(1) - Fraction(1, 10**100)},
        {"level_vol": Fraction(1, 10**400)},
        {"deviation_vol": Fraction(1, 10**400)},
        {"start_price": Fraction(1, 10**400)},
        {"level_vol": 1e-200},
        {"deviation_vol": 1e-200},
        {"deviation_vol": 1e200},
        {"level_vol": 1e200},
        {"level_vol": 1e-100, "deviation_vol": 1e-100},
        {"level_vol": 1e100, "deviation_vol": 1e100},
    ],
)
def test_posterior_refuses_original_or_derived_law_arithmetic_even_empty(changes: Any) -> None:
    with pytest.raises(ValueError):
        _posterior(np.array([]), **changes)


@pytest.mark.parametrize(
    "source,changes",
    [
        (np.array([-1e308, 1e308]), {}),
        (np.array([1e308]), {"drift": -1e308, "start_price": 0.5}),
    ],
)
def test_posterior_refuses_unmeasurable_state_arithmetic(source: Any, changes: Any) -> None:
    with pytest.raises(ValueError):
        _posterior(source, **changes)


@pytest.mark.parametrize(
    "source",
    [
        np.array([0, 1, 2], dtype=np.int64),
        np.array([0, 1, 2], dtype=np.uint64),
        np.arange(6, dtype=float)[::2],
        np.ma.array([0.0, 1.0, 2.0], mask=False),
    ],
)
def test_posterior_supported_source_families_match_snapshot_and_preserve_inputs(
    source: Any,
) -> None:
    before = source.copy()
    result = _posterior(source)
    expected = _posterior(np.array(source, dtype=float, copy=True))
    np.testing.assert_array_equal(result.deviation_mean, expected.deviation_mean)
    np.testing.assert_array_equal(source, before)
    result.deviation_mean[:] = 99
    result.deviation_variance[:] = 99
    again = _posterior(source)
    np.testing.assert_array_equal(again.deviation_mean, expected.deviation_mean)
    np.testing.assert_array_equal(source, before)


def test_posterior_preserves_numpy_error_policy_on_success_and_failure() -> None:
    original = np.geterr()
    with np.errstate(all="raise"):
        strict = np.geterr()
        _posterior(np.array([0.0, 0.01]))
        assert np.geterr() == strict
        with pytest.raises(ValueError):
            _posterior(np.array([]), deviation_vol=1e200)
        assert np.geterr() == strict
    assert np.geterr() == original


def test_posterior_original_negative_level_rounding_to_zero_is_refused() -> None:
    level = -Fraction(1, 10**400)
    assert level < 0 and float(level) == -0.0
    with pytest.raises(ValueError):
        _posterior(np.array([]), level_vol=level)


def test_posterior_positive_deviation_variance_with_underflowed_q_is_refused() -> None:
    rho = float(np.nextafter(1.0, 0.0))
    deviation = 1e-160
    assert deviation * deviation > 0
    assert deviation * deviation * (1 - rho * rho) == 0
    with pytest.raises(ValueError):
        _posterior(np.array([]), rho=rho, deviation_vol=deviation)


@pytest.mark.parametrize("scalar", [Fraction, np.float32, np.float64, np.longdouble])
def test_posterior_valid_scalar_families_match_normalized_first_price_law(scalar: Any) -> None:
    law = {key: scalar(value) for key, value in LAW.items()}
    source = np.array([0.01, 0.02])
    result = _posterior(source, **law)
    normalized = {key: float(value) for key, value in law.items()}
    oracle = _joint_oracle(
        [Fraction(float(value)) for value in source],
        Fraction(normalized["rho"]),
        Fraction(normalized["level_vol"]),
        Fraction(normalized["deviation_vol"]),
        Fraction(normalized["drift"]),
    )
    np.testing.assert_allclose(result.deviation_mean, oracle[0], rtol=1e-13, atol=1e-17)
    np.testing.assert_allclose(result.deviation_variance, oracle[1], rtol=1e-13, atol=1e-19)


def test_posterior_wider_finite_observation_cast_obeys_platform_range() -> None:
    maximum = np.finfo(np.longdouble).max
    source = np.array([maximum], dtype=np.longdouble)
    assert np.isfinite(source).all()
    with np.errstate(over="ignore"):
        cast = np.array(source, dtype=np.float64)
    if not np.isfinite(cast).all():
        with pytest.raises(ValueError, match="normalized log_prices"):
            _posterior(source)
    else:
        result = _posterior(source)
        normalized = _posterior(cast)
        np.testing.assert_array_equal(result.deviation_mean, normalized.deviation_mean)
        np.testing.assert_array_equal(result.deviation_variance, normalized.deviation_variance)


def test_posterior_readonly_source_retains_ownership_and_nonmutation() -> None:
    source = np.array([0.0, 0.01, -0.02])
    before = source.copy()
    source.flags.writeable = False
    result = _posterior(source)
    for output in result:
        assert output.flags.owndata and output.flags.writeable
        assert not np.shares_memory(output, source)
        output[:] = 99
    np.testing.assert_array_equal(source, before)
    assert not source.flags.writeable
    again = _posterior(source)
    assert not np.any(again.deviation_mean == 99)
    assert not np.any(again.deviation_variance == 99)
