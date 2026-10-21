"""ADR-337: forward Gaussian mass detects central-quantile cancellation."""

import math
import warnings

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.backtesting.metrics import sharpe_confidence_interval


def _complete_zero_centered_returns() -> pd.Series:
    return pd.Series([-0.01, 0.01] * 126)


@pytest.mark.parametrize(
    "confidence", [2.0**-1000, 1e-20, 1e-16, 1e-12, 1e-10, 0.001, 0.1, 0.25, 0.5]
)
def test_representable_central_interval_matches_requested_gaussian_mass(confidence: float) -> None:
    # Complete 252-row symmetric returns give Sharpe0 and SE1 independently of z.
    result = sharpe_confidence_interval(_complete_zero_centered_returns(), confidence=confidence)
    assert result is not None
    assert result.assumption == "iid_normal" and result.confidence == confidence
    assert result.lower == -result.upper and result.upper > 0
    # A numerical quantile oracle, not measured frequentist/market coverage.
    assert math.erf(result.upper / math.sqrt(2)) == pytest.approx(confidence, rel=1e-14, abs=0)


@pytest.mark.parametrize("confidence", [2.0**-1074, 2.0**-1072, 2.0**-1060])
def test_selected_subnormal_central_mass_has_explicit_quantization_bound(confidence: float) -> None:
    result = sharpe_confidence_interval(_complete_zero_centered_returns(), confidence=confidence)
    assert result is not None and math.isfinite(result.upper) and result.upper > 0
    forward_mass = math.erf(result.upper / math.sqrt(2))
    # Separate ULP bound on these cases; uniform relative accuracy is not promised.
    assert abs(forward_mass - confidence) <= 2 * math.ulp(confidence)


@pytest.mark.parametrize("mode", ["ignore", "warn", "raise"])
@pytest.mark.parametrize("confidence", [2.0**-1074, 2.0**-1072, 2.0**-1060])
def test_subnormal_quantile_product_does_not_add_numpy_policy_failures(
    confidence: float, mode: str
) -> None:
    with warnings.catch_warnings(), np.errstate(all=mode):
        warnings.simplefilter("error", RuntimeWarning)
        result = sharpe_confidence_interval(
            _complete_zero_centered_returns(), confidence=confidence
        )
    assert result is not None and math.isfinite(result.upper) and result.upper > 0


def test_central_tail_branch_neighbors_remain_ordered() -> None:
    quantiles = []
    for confidence in (math.nextafter(0.5, 0), 0.5, math.nextafter(0.5, 1)):
        result = sharpe_confidence_interval(
            _complete_zero_centered_returns(), confidence=confidence
        )
        assert result is not None
        quantiles.append(result.upper)
    assert quantiles[0] < quantiles[1] < quantiles[2]


@pytest.mark.parametrize("confidence", [0.75, 0.95, 0.99, math.nextafter(1.0, 0)])
def test_existing_high_confidence_forward_tail_remains_measurable(confidence: float) -> None:
    result = sharpe_confidence_interval(_complete_zero_centered_returns(), confidence=confidence)
    assert result is not None and math.isfinite(result.upper)
    assert math.erfc(result.upper / math.sqrt(2)) == pytest.approx(1 - confidence, rel=1e-12, abs=0)


@pytest.mark.parametrize("confidence", [0.0, 1.0, math.nan, math.inf])
def test_confidence_validation_still_precedes_bad_source(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence must be finite and between 0 and 1"):
        sharpe_confidence_interval(pd.Series([math.nan]), confidence=confidence)


def test_tiny_confidence_still_requires_complete_observations() -> None:
    source = _complete_zero_centered_returns()
    source.iloc[0] = math.nan
    with pytest.raises(ValueError, match="returns must be finite and complete"):
        sharpe_confidence_interval(source, confidence=1e-20)


def test_valid_short_history_still_returns_none_at_tiny_confidence() -> None:
    assert sharpe_confidence_interval(pd.Series([0.01] * 251), confidence=1e-20) is None


@given(confidence=st.floats(2.0**-1022, 0.5, allow_nan=False, allow_infinity=False))
def test_normal_central_probabilities_invert_with_relative_forward_oracle(
    confidence: float,
) -> None:
    result = sharpe_confidence_interval(_complete_zero_centered_returns(), confidence=confidence)
    assert result is not None and 0 < result.upper < math.inf
    assert result.lower == -result.upper
    assert math.isclose(math.erf(result.upper / math.sqrt(2)), confidence, rel_tol=1e-14, abs_tol=0)
