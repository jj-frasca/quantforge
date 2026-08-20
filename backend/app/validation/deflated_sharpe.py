import math
from collections.abc import Sequence

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
    if n_trials <= 1:
        return 0.0
    a = norm.ppf(1.0 - 1.0 / n_trials)
    b = norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    return float(sr_std * ((1.0 - _EULER_MASCHERONI) * a + _EULER_MASCHERONI * b))


def deflated_sharpe(observed_sr: float, n_trials: int, sr_std: float = 1.0) -> float:
    """Deflated Sharpe value = observed Sharpe minus the multiple-testing haircut.

    Notes:
        Reported as a value (not a probability) so DSR <= observed_sr by construction
        (§8 invariant #5): the haircut is the expected max Sharpe of n_trials under the null,
        which is >= 0. N == 1 means no penalty. Bailey & López de Prado (2014).
    """
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")
    if sr_std <= 0:
        raise ValueError("sr_std must be > 0")
    haircut = max(expected_max_sharpe(n_trials, sr_std), 0.0)
    return observed_sr - haircut
