import math
from collections.abc import Sequence
from numbers import Integral, Real

import numpy as np
from scipy.stats import norm

_EULER_MASCHERONI = 0.5772156649015329
_NORMAL_IQR = 2.0 * 0.6744897501960817
_MIN_DISPERSION = 1e-6


def robust_sharpe_dispersion(sharpes: Sequence[float]) -> float:
    """Normal-consistent IQR scale for trial Sharpe estimates (ADR-050).

    The DSR expected-maximum model assumes an approximately Normal trial family. Scaling the
    interquartile range by the standard Normal IQR estimates that family's null dispersion while
    preventing a minority of signal-loading trials from raising their own null haircut without
    bound. The positive floor preserves well-defined pricing for degenerate grids.
    """
    if len(sharpes) < 2:
        raise ValueError("need at least two Sharpe estimates")
    values = np.asarray(sharpes, dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("Sharpe estimates must be finite")
    if len(values) < 4:
        dispersion = float(np.std(values, ddof=1))
    else:
        q25, q75 = np.quantile(values, [0.25, 0.75])
        dispersion = float((q75 - q25) / _NORMAL_IQR)
    return max(dispersion, _MIN_DISPERSION)


def expected_max_sharpe(n_trials: int, sr_std: float) -> float:
    """Expected maximum of N iid Sharpe estimates ~N(0, sr_std^2) (Bailey et al. 2015)."""
    count_evidence: object = n_trials
    if isinstance(count_evidence, (bool, np.bool_)) or not isinstance(count_evidence, Integral):
        raise ValueError("n_trials must be a positive nonboolean integer")
    n_trials = int(count_evidence)
    if n_trials < 1:
        raise ValueError("n_trials must be a positive nonboolean integer")
    dispersion_evidence: object = sr_std
    if isinstance(dispersion_evidence, (bool, np.bool_)) or not isinstance(
        dispersion_evidence, Real
    ):
        raise ValueError("sr_std must be a positive finite real nonboolean scalar")
    try:
        sr_std = float(dispersion_evidence)
    except (OverflowError, ValueError) as exc:
        raise ValueError("sr_std must be a positive finite real nonboolean scalar") from exc
    if not np.isfinite(sr_std) or sr_std <= 0.0:
        raise ValueError("sr_std must be a positive finite real nonboolean scalar")
    if n_trials == 1:
        return 0.0
    # Integer true division preserves representable reciprocals beyond float count range.
    tail_a = 1 / n_trials
    tail_b = tail_a / math.e
    if not np.isfinite([tail_a, tail_b]).all() or tail_a <= 0.0 or tail_b <= 0.0:
        raise ValueError("trial tails must be positive and finite")
    a = norm.isf(tail_a)
    b = norm.isf(tail_b)
    with np.errstate(over="ignore", invalid="ignore"):
        result = float(sr_std * ((1.0 - _EULER_MASCHERONI) * a + _EULER_MASCHERONI * b))
    if not np.isfinite(result):
        raise ValueError("expected maximum Sharpe must be finite")
    return result


def deflated_sharpe(observed_sr: float, n_trials: int, sr_std: float = 1.0) -> float:
    """Selection-adjusted Sharpe MARGIN = observed Sharpe minus the multiple-testing haircut.

    Notes:
        This is NOT the Deflated Sharpe Ratio of Bailey & Lopez de Prado (2014), which is a
        probability in [0, 1] that also uses the track record's length, skewness and kurtosis —
        see `deflated_sharpe_probability` below and FINDING-007. It is adapted from that paper's
        expected-maximum haircut, and it is in Sharpe units, so `margin <= observed_sr` holds by
        construction (§8 invariant #5). N == 1 means no penalty.
    """
    haircut = max(expected_max_sharpe(n_trials, sr_std), 0.0)
    score_evidence: object = observed_sr
    if isinstance(score_evidence, (bool, np.bool_)) or not isinstance(score_evidence, Real):
        raise ValueError("observed_sr must be a finite real nonboolean scalar")
    try:
        observed_sr = float(score_evidence)
    except (OverflowError, ValueError) as exc:
        raise ValueError("observed_sr must be a finite real nonboolean scalar") from exc
    if not np.isfinite(observed_sr):
        raise ValueError("observed_sr must be a finite real nonboolean scalar")
    result = observed_sr - haircut
    if not np.isfinite(result):
        raise ValueError("deflated Sharpe margin must be finite")
    return result


def probabilistic_sharpe_ratio(
    observed_sr: float,
    *,
    benchmark_sr: float,
    n_returns: int,
    skew: float,
    kurtosis: float,
) -> float:
    """P(true Sharpe > benchmark) for an estimate from `n_returns` non-Normal returns.

    Bailey & Lopez de Prado (2014) Eq. 1. `kurtosis` is RAW, not excess: a Normal series is 3.0 and
    reduces the denominator to the familiar `1/sqrt(n-1)` standardization. All three arguments are
    per-period on the same scale as `observed_sr` — annualizing one and not the others silently
    rescales the answer.

    Notes:
        The retained domain policy requires positive `kurtosis - skew^2 - 1`, the slack in
        Pearson's population-moment inequality. This is distinct from the SE-squared factor
        `(1 - skew*SR + (kurtosis-1)*SR^2/4)/(n-1)`. Zero slack can describe a genuine two-point
        distribution even when that factor is positive; the strict policy still excludes it.
        ADR-193 clarifies the explanation without relaxing the guard or its legacy error label.
    """
    count_evidence: object = n_returns
    if isinstance(count_evidence, (bool, np.bool_)) or not isinstance(count_evidence, Integral):
        raise ValueError("n_returns must be a nonboolean integer >= 2")
    n_returns = int(count_evidence)
    if n_returns < 2:
        raise ValueError("n_returns must be a nonboolean integer >= 2")
    source_scalars: tuple[tuple[str, object], ...] = (
        ("observed_sr", observed_sr),
        ("benchmark_sr", benchmark_sr),
        ("skew", skew),
        ("kurtosis", kurtosis),
    )
    validated: list[float] = []
    for name, value in source_scalars:
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
            raise ValueError(f"{name} must be a finite real nonboolean scalar")
        try:
            scalar = float(value)
        except (OverflowError, ValueError) as exc:
            raise ValueError(f"{name} must be a finite real nonboolean scalar") from exc
        if not np.isfinite(scalar):
            raise ValueError(f"{name} must be a finite real nonboolean scalar")
        validated.append(scalar)
    observed_sr, benchmark_sr, skew, kurtosis = validated
    try:
        variance = kurtosis - skew**2 - 1.0
    except OverflowError as exc:
        raise ValueError("PSR arithmetic must be finite and measurable") from exc
    if not math.isfinite(variance):
        raise ValueError("PSR arithmetic must be finite and measurable")
    if variance <= 0.0:
        raise ValueError("degenerate Sharpe-estimator variance: kurtosis - skew^2 - 1 must be > 0")
    try:
        se_squared = (1.0 - skew * observed_sr + 0.25 * (kurtosis - 1.0) * observed_sr**2) / (
            n_returns - 1
        )
    except OverflowError as exc:
        raise ValueError("PSR arithmetic must be finite and measurable") from exc
    if not math.isfinite(se_squared) or se_squared <= 0.0:
        raise ValueError("PSR arithmetic must be finite and measurable")
    standard_error = math.sqrt(se_squared)
    return float(norm.cdf((observed_sr - benchmark_sr) / standard_error))


def deflated_sharpe_probability(
    observed_sr: float,
    *,
    n_trials: int,
    sr_std: float,
    n_returns: int,
    skew: float,
    kurtosis: float,
) -> float:
    """The paper's Deflated Sharpe Ratio (ADR-054): PSR against the multiple-testing threshold.

    Notes:
        A PROBABILITY in [0, 1]. `deflated_sharpe` above returns a Sharpe-unit MARGIN and the two
        are not comparable; FINDING-007 records what went wrong when one was reported under the
        other's name. Delegates to `probabilistic_sharpe_ratio` rather than reimplementing it so
        the two can never disagree.
    """
    haircut = max(expected_max_sharpe(n_trials, sr_std), 0.0)
    return probabilistic_sharpe_ratio(
        observed_sr,
        benchmark_sr=haircut,
        n_returns=n_returns,
        skew=skew,
        kurtosis=kurtosis,
    )
