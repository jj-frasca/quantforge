"""ADR-054 decision 3: the PER-PERIOD sample moments the PSR denominator is written in.

The whole reason this is a separate, tested unit is scale. Everything a `Trial` stores is
annualized; PSR is a function of the per-period Sharpe and the per-period moments TOGETHER, so a
moment computed under the wrong convention (excess instead of raw kurtosis) silently rescales a
probability rather than failing.
"""

import numpy as np
import pandas as pd
import pytest

from app.research.backtesting.metrics import return_moments


def _series(values: list[float]) -> pd.Series:
    index = pd.date_range("2024-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=index, dtype="float64")


def test_kurtosis_is_raw_not_excess() -> None:
    """A Normal series must report ~3.0, which is what reduces the PSR denominator to the
    familiar 1/sqrt(n-1). Reporting pandas' excess kurtosis here would make every series look
    3.0 units more Normal than it is."""
    rng = np.random.default_rng(11)
    returns = _series(list(rng.normal(0.0, 0.01, 4000)))
    moments = return_moments(returns)
    assert moments is not None
    assert moments.kurtosis == pytest.approx(float(returns.kurt()) + 3.0)
    assert moments.kurtosis == pytest.approx(3.0, abs=0.25)
    assert moments.skew == pytest.approx(float(returns.skew()))
    assert moments.n_returns == len(returns)


def test_a_left_skewed_series_reports_negative_skew() -> None:
    returns = _series([-0.20] + [0.01] * 60)
    moments = return_moments(returns)
    assert moments is not None
    assert moments.skew < 0.0
    assert moments.kurtosis > 3.0


@pytest.mark.parametrize("values", [[], [0.01], [0.01, -0.02], [0.01, -0.02, 0.03]])
def test_too_short_a_series_is_unmeasured_rather_than_zero(values: list[float]) -> None:
    """Sample kurtosis is undefined below four observations. None means 'not measured'; a 0.0
    would enter the PSR denominator as a real, extremely non-Normal reading."""
    assert return_moments(_series(values)) is None


def test_a_constant_series_is_unmeasured() -> None:
    """pandas reports skew 0.0 / excess kurtosis 0.0 for a zero-variance series, which would read
    as a perfectly Normal track record. It has no distribution to describe."""
    assert return_moments(_series([0.0] * 40)) is None
