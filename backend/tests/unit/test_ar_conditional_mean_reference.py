"""Known-law AR reference, independent of historical calibration defaults (ADR-223)."""

from collections.abc import Callable
from fractions import Fraction
from itertools import pairwise
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab import calibration


def _frame(returns: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"close": 100.0 * np.cumprod([1.0, *[1 + r for r in returns]])})


def _score(frame: pd.DataFrame, **kwargs: Any) -> float:
    helper = getattr(calibration, "ar1_conditional_mean_sign_sharpe", None)
    assert callable(helper), "explicit-drift AR reference helper is absent"
    return float(helper(frame, **kwargs))


def _scalar_score(frame: pd.DataFrame, phi: float, drift: float, cost: float) -> float:
    closes = frame["close"].to_list()
    returns = [right / left - 1.0 for left, right in pairwise(closes)]
    if len(returns) < 3:
        return 0.0
    realized = [0.0]
    previous_position = 0.0
    for lag, current in pairwise(returns):
        mean = phi * lag + drift * (1 - phi)
        position = float((mean > 0) - (mean < 0))
        realized.append(position * current - abs(position - previous_position) * cost)
        previous_position = position
    std = float(np.std(realized, ddof=1))
    return 0.0 if std == 0 else float(np.sqrt(252) * np.mean(realized) / std)


@pytest.mark.parametrize("phi,lag", [(0.3, -0.0005), (-0.3, 0.0005)])
def test_drift_intercept_reverses_recorded_historical_sign(phi: float, lag: float) -> None:
    frame = _frame([lag, 0.003, -0.002, 0.004, -0.001])
    assert phi * lag < 0 < phi * lag + 0.0003 * (1 - phi)
    score = _score(frame, phi=phi, drift=0.0003)
    assert score == pytest.approx(_scalar_score(frame, phi, 0.0003, 0.0))
    assert score != pytest.approx(calibration.oracle_sharpe(frame, phi=phi))


@pytest.mark.parametrize("drift", [-0.0003, 0.0003])
def test_zero_phi_retains_known_drift_without_initial_observed_lag(drift: float) -> None:
    frame = _frame([0.02, -0.01, 0.003, 0.004, -0.005])
    assert _score(frame, phi=0.0, drift=drift) == pytest.approx(
        _scalar_score(frame, 0.0, drift, 0.0)
    )
    assert calibration.oracle_sharpe(frame, phi=0.0) == 0.0


@pytest.mark.parametrize("phi", [-0.3, 0.0, 0.3])
@pytest.mark.parametrize("cost", [0.0, 0.001])
def test_zero_drift_is_exactly_the_historical_reference(phi: float, cost: float) -> None:
    frame = calibration.autocorrelated_edge(128, seed=71, phi=phi, drift=0.0)
    assert _score(frame, phi=phi, drift=0.0, cost_rate=cost) == calibration.oracle_sharpe(
        frame, phi=phi, cost_rate=cost
    )


def test_conditional_mean_prefix_is_causal_and_first_unavailable_lag_is_flat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[pd.Series] = []
    native: Callable[..., float] = calibration.oracle_sharpe_of

    def capture(frame: pd.DataFrame, conditional_mean: pd.Series, **kwargs: Any) -> float:
        seen.append(conditional_mean.copy())
        return native(frame, conditional_mean, **kwargs)

    monkeypatch.setattr(calibration, "oracle_sharpe_of", capture)
    frame = _frame([0.002, -0.003, 0.001, 0.004, -0.002, 0.005])
    _score(frame.iloc[:5], phi=-0.3, drift=0.0003)
    changed = frame.copy()
    changed.loc[5:, "close"] *= [1.5, 0.5]
    _score(changed, phi=-0.3, drift=0.0003)
    pd.testing.assert_series_equal(seen[0], seen[1].loc[seen[0].index])
    assert pd.isna(seen[0].iloc[0])
    observed_lag = frame["close"].iloc[1] / frame["close"].iloc[0] - 1
    assert seen[0].iloc[1] == pytest.approx(-0.3 * observed_lag + 0.0003 * 1.3)


@pytest.mark.parametrize("n", [0, 1, 2])
def test_short_observed_history_retains_zero_reference(n: int) -> None:
    assert _score(_frame([0.01] * n), phi=0.3, drift=0.0003) == 0.0


@pytest.mark.parametrize("missing", ["phi", "drift"])
def test_known_law_parameters_must_be_explicit(missing: str) -> None:
    params = {"phi": 0.3, "drift": 0.0003}
    del params[missing]
    with pytest.raises(TypeError):
        _score(_frame([0.001] * 4), **params)


@pytest.mark.parametrize("field", ["phi", "drift", "cost_rate"])
@pytest.mark.parametrize("bad", [True, np.bool_(False), "0.1", 1j, np.nan, np.inf, -np.inf])
def test_original_law_and_cost_parameters_reject_invalid_evidence(field: str, bad: Any) -> None:
    params = {"phi": 0.3, "drift": 0.0003, "cost_rate": 0.001}
    params[field] = bad
    with pytest.raises(ValueError):
        _score(_frame([0.001] * 4), **params)


@pytest.mark.parametrize("phi", [-1.0, 1.0, -2.0, 2.0, Fraction(10**20 + 1, 10**20)])
def test_nonstationary_original_phi_is_refused(phi: Any) -> None:
    with pytest.raises(ValueError):
        _score(_frame([0.001] * 4), phi=phi, drift=0.0003)


def test_negative_cost_and_nonfinite_derived_mean_are_refused() -> None:
    frame = _frame([0.001] * 4)
    with pytest.raises(ValueError):
        _score(frame, phi=0.3, drift=0.0003, cost_rate=-0.001)
    with pytest.raises(ValueError):
        _score(frame, phi=-0.5, drift=1.7e308)


def test_supported_real_scalar_parameters_keep_the_same_reference() -> None:
    frame = _frame([0.001, -0.002, 0.003, -0.004])
    assert _score(frame, phi=np.float64(0.3), drift=Fraction(3, 10000), cost_rate=np.int64(0)) == (
        _score(frame, phi=0.3, drift=0.0003)
    )


@given(
    returns=st.lists(
        st.floats(-0.02, 0.02, allow_nan=False, allow_infinity=False), min_size=5, max_size=40
    ),
    phi=st.floats(-0.8, 0.8, allow_nan=False, allow_infinity=False),
    drift=st.floats(-0.002, 0.002, allow_nan=False, allow_infinity=False),
    cost=st.floats(0.0, 0.002, allow_nan=False, allow_infinity=False),
)
def test_known_law_score_matches_independent_scalar_turnover_accounting(
    returns: list[float], phi: float, drift: float, cost: float
) -> None:
    frame = _frame(returns)
    assert _score(frame, phi=phi, drift=drift, cost_rate=cost) == pytest.approx(
        _scalar_score(frame, phi, drift, cost), rel=1e-12, abs=1e-12
    )


def test_nonfinite_observed_prediction_is_refused() -> None:
    frame = pd.DataFrame({"close": [1e-308, 1e308, 1.1e308, 1.2e308]})
    with (
        np.errstate(over="ignore", invalid="ignore"),
        pytest.raises(ValueError, match="conditional mean must be finite"),
    ):
        _score(frame, phi=0.3, drift=0.0003)
