"""Finite cohort means survive native sum overflow (ADR-367)."""

import json
import math
import sys
from datetime import UTC, datetime

import pytest
from fastapi.encoders import jsonable_encoder
from hypothesis import given, settings
from hypothesis import strategies as st
from starlette.responses import JSONResponse

from app.research.lab.paper import ForwardScore, PaperPosition
from app.research.lab.portfolio_manager import DeflationCohorts, deflation_cohorts

_MAX = sys.float_info.max
_SMALLEST = math.ulp(0.0)


def _summary(values: list[float], survives: bool = True) -> DeflationCohorts:
    positions = [
        PaperPosition(
            symbol=f"S{i}",
            strategy_name="momentum",
            parameters={"lookback": 3},
            frozen_at=datetime(2026, 1, 1, tzinfo=UTC),
            survives_universe_deflation=survives,
            score=ForwardScore(
                forward_bars=4,
                forward_return=0.0,
                forward_sharpe=value,
                buy_and_hold_return=0.0,
                buy_and_hold_sharpe=0.0,
                beats_buy_and_hold=False,
                as_of=datetime(2026, 1, 5, tzinfo=UTC),
            ),
        )
        for i, value in enumerate(values)
    ]
    return deflation_cohorts(positions)


def _mean(values: list[float], survives: bool = True) -> float:
    result = _summary(values, survives)
    value = (
        result.survivor_mean_forward_sharpe if survives else result.non_survivor_mean_forward_sharpe
    )
    assert value is not None
    return value


def _integer_grid_oracle(values: list[float]) -> float:
    """Independent integer accumulation on a common binary denominator, without Fraction."""
    ratios = [value.as_integer_ratio() for value in values]
    denominator = max(denominator for _, denominator in ratios)
    total = sum(numerator * (denominator // divisor) for numerator, divisor in ratios)
    return total / (denominator * len(values))


@pytest.mark.parametrize("survives", [True, False])
@pytest.mark.parametrize(
    "values",
    [
        [_MAX, _MAX],
        [-_MAX, -_MAX],
        [_MAX, _MAX, -_MAX],
        [-_MAX, -_MAX, _MAX],
        [_MAX, _MAX, -_MAX, -_MAX],
        [_MAX, _MAX, -_MAX, -_MAX, 5 * _SMALLEST],
        [5 * _SMALLEST, _MAX, _MAX, -_MAX, -_MAX],
        [_MAX, _MAX, -_MAX, -_MAX, -5 * _SMALLEST],
    ],
)
def test_cohort_mean_given_native_sum_overflow_matches_independent_integer_oracle(
    values: list[float], survives: bool
) -> None:
    assert not math.isfinite(sum(values))
    mean = _mean(values, survives)
    assert math.isfinite(mean)
    assert mean.hex() == _integer_grid_oracle(values).hex()
    assert min(values) <= mean <= max(values)
    summary = _summary(values, survives)
    assert (summary.n_survivors if survives else summary.n_non_survivors) == len(values)


@pytest.mark.parametrize(
    "values",
    [
        [1.2, 2.3, -0.7],
        [_MAX, 0.0],
        [_MAX, -_MAX, 5 * _SMALLEST],
        [_SMALLEST, 0.0],
        [_SMALLEST, -_SMALLEST, _SMALLEST],
        [-0.0, -0.0],
        [0.0, -0.0],
    ],
)
def test_cohort_mean_given_finite_native_result_preserves_exact_float_encoding(
    values: list[float],
) -> None:
    expected = sum(values) / len(values)
    assert math.isfinite(expected)
    assert _mean(values).hex() == expected.hex()


@pytest.mark.parametrize("survives", [True, False])
def test_cohort_mean_given_finite_extreme_sources_preserves_standard_json_transport(
    survives: bool,
) -> None:
    summary = _summary([1e308, 1e308], survives)
    response = JSONResponse(jsonable_encoder(summary))
    payload = json.loads(response.body)
    key = "survivor_mean_forward_sharpe" if survives else "non_survivor_mean_forward_sharpe"
    assert payload[key] == 1e308


@given(
    large=st.floats(min_value=1e308, max_value=_MAX, allow_nan=False, allow_infinity=False),
    tiny=st.floats(min_value=-1e-200, max_value=1e-200, allow_nan=False, allow_infinity=False),
    negative_first=st.booleans(),
    survives=st.booleans(),
)
@settings(max_examples=45, deadline=None)
def test_cohort_mean_preserves_represented_residual_after_overflowing_cancellation(
    large: float, tiny: float, negative_first: bool, survives: bool
) -> None:
    first = -large if negative_first else large
    values = [first, first, -first, -first, tiny]
    assert not math.isfinite(sum(values))
    actual = _mean(values, survives)
    assert math.isfinite(actual)
    assert actual.hex() == _integer_grid_oracle(values).hex()
    assert min(values) <= actual <= max(values)
