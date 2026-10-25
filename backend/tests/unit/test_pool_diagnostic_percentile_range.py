"""Pool diagnostic summaries retain finite evidence (ADR-368)."""

import json
import math
import sys
from typing import Literal

import numpy as np
import pytest
from fastapi.encoders import jsonable_encoder
from hypothesis import given, settings
from hypothesis import strategies as st
from starlette.responses import JSONResponse

from app.research.lab.experiment import Experiment, Trial
from app.research.lab.gate import GateConfig
from app.research.lab.pool_report import _summarize, summarize_pool

_MAX = sys.float_info.max
_FIELDS = ["walk_forward_oos_sharpe", "purged_cv_oos_sharpe"]
Mode = Literal["ignore", "warn", "raise"]


def _trial(value: float | None, field: str) -> Trial:
    return Trial.model_validate(
        {
            "strategy_name": "sma",
            "parameters": {"fast": 5, "slow": 20},
            "observed_sharpe": 1.0,
            "deflated_sharpe": 0.0,
            "pbo": 0.1,
            "parameter_stability_score": 0.8,
            field: value,
        }
    )


def _integer_quantile(values: list[float], q: float) -> float:
    """Accumulate weighted binary endpoints on an integer grid, without Fraction."""
    ordered = sorted(values)
    index = (len(values) - 1) * q
    left = int(index)
    right = min(left + 1, len(values) - 1)
    weight, weight_denominator = (index - left).as_integer_ratio()
    low, low_denominator = ordered[left].as_integer_ratio()
    high, high_denominator = ordered[right].as_integer_ratio()
    denominator = max(low_denominator, high_denominator)
    numerator = (
        low * (denominator // low_denominator) * (weight_denominator - weight)
        + high * (denominator // high_denominator) * weight
    )
    return numerator / (denominator * weight_denominator)


@pytest.mark.parametrize("field", _FIELDS)
@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
@pytest.mark.parametrize(
    "values", [[1e308, 1e308], [-1e308, -1e308], [_MAX, _MAX], [-_MAX, -_MAX], [-_MAX, _MAX]]
)
def test_pool_diagnostic_extremes_match_integer_oracle_and_preserve_error_policy(
    values: list[float], field: str, mode: Mode
) -> None:
    trials = [_trial(value, field) for value in values]
    before = [trial.model_dump_json() for trial in trials]
    with np.errstate(all=mode):
        policy = np.geterr()
        result = _summarize(trials, field)
        assert np.geterr() == policy
    assert result is not None
    assert result.n == len(values)
    assert result.median.hex() == _integer_quantile(values, 0.5).hex()
    assert result.p95.hex() == _integer_quantile(values, 0.95).hex()
    assert result.maximum == max(values)
    assert min(values) <= result.median <= result.p95 <= result.maximum
    assert [trial.model_dump_json() for trial in trials] == before


@pytest.mark.parametrize("field", _FIELDS)
@pytest.mark.parametrize("values", [[1.2, -0.7, 2.3], [1.0], [0.0, 0.0], [1e-308, 2e-308]])
def test_pool_diagnostic_finite_native_payload_and_encodings_remain_exact(
    values: list[float], field: str
) -> None:
    result = _summarize([_trial(None, field), *[_trial(v, field) for v in values]], field)
    assert result is not None
    expected = (float(np.median(values)), float(np.percentile(values, 95)), max(values))
    assert result.n == len(values)
    assert tuple(v.hex() for v in (result.median, result.p95, result.maximum)) == tuple(
        v.hex() for v in expected
    )


@pytest.mark.parametrize("field", _FIELDS)
def test_pool_diagnostic_empty_and_all_missing_remain_unmeasured(field: str) -> None:
    assert _summarize([], field) is None
    assert _summarize([_trial(None, field), _trial(None, field)], field) is None


@pytest.mark.parametrize("field", _FIELDS)
@pytest.mark.parametrize("values", [[1e308, 1e308], [-_MAX, _MAX]])
def test_public_pool_finalist_diagnostics_encode_finite_summary_evidence(
    field: str, values: list[float]
) -> None:
    experiments = [
        Experiment(
            symbol=f"S{i}",
            strategy_names=["sma"],
            gate_config=GateConfig(),
            trials=[_trial(value, field)],
            lifetime_trials=1,
        )
        for i, value in enumerate(values)
    ]
    report = summarize_pool(experiments, [])
    payload = json.loads(JSONResponse(jsonable_encoder(report)).body)
    summary = payload[
        "walk_forward_finalists" if field.startswith("walk") else "purged_cv_finalists"
    ]
    assert summary == {
        "n": len(values),
        "median": _integer_quantile(values, 0.5),
        "p95": _integer_quantile(values, 0.95),
        "maximum": max(values),
    }


@given(
    value=st.floats(min_value=1e308, max_value=_MAX, allow_nan=False, allow_infinity=False),
    opposite=st.booleans(),
    field=st.sampled_from(_FIELDS),
)
@settings(max_examples=45, deadline=None)
def test_pool_diagnostic_extreme_quantiles_stay_in_convex_range(
    value: float, opposite: bool, field: str
) -> None:
    values = [-value, value] if opposite else [value, value]
    with np.errstate(over="raise", invalid="raise"):
        result = _summarize([_trial(v, field) for v in values], field)
    assert result is not None
    assert all(math.isfinite(v) for v in (result.median, result.p95, result.maximum))
    assert min(values) <= result.median <= result.p95 <= result.maximum <= max(values)
    assert result.median.hex() == _integer_quantile(values, 0.5).hex()
    assert result.p95.hex() == _integer_quantile(values, 0.95).hex()
