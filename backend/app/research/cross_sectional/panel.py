import numpy as np
import pandas as pd


def long_short_weights(signals: pd.DataFrame, quantile: float = 0.2) -> pd.DataFrame:
    """Turn a (dates x symbols) signal panel into dollar-neutral target weights (ADR-024).

    For each date independently: drop NaN signals (an unscorable name that day), rank the rest, and
    give the top ``quantile`` fraction a shared +1 long leg and the bottom fraction a shared -1 short
    leg (each name in a leg gets an equal share, so the legs net to zero). A date with fewer than two
    valid names cannot form both legs and trades flat. Ties are broken with ``rank(method="first")``
    so the selection is deterministic, never dependent on column order.

    Notes:
        ``quantile`` must be in (0, 0.5]; at 0.5 the universe splits cleanly into long and short
        halves. ``k = max(1, int(quantile · n_valid))`` per leg, so a small cross-section still
        trades one name per side. ``k`` is per DATE, not per panel.

        Vectorised over the whole frame rather than looped per date. The row loop this replaces
        used ``DataFrame.iterrows()``, which rebuilds and copies a Series for every date, and it
        was slow enough that one Hypothesis property test over it exceeded the suite's 300s
        per-test timeout on a developer machine — killing its xdist worker and stalling the run.
        Every cross-sectional backtest goes through here, so the cost was never only a test's.
    """
    if not 0.0 < quantile <= 0.5:
        raise ValueError("quantile must be in (0, 0.5]")

    ranked = signals.rank(axis=1, method="first")  # 1 = lowest signal; NaN stays NaN
    n_valid = signals.notna().sum(axis=1)
    k = np.maximum(1, (quantile * n_valid).astype(int))

    # Both legs hold exactly k names, so each name's share is 1/k. Comparisons against NaN ranks
    # are False, which is how unscorable names stay out of either leg.
    longs = ranked.gt(n_valid - k, axis=0).astype(float)
    shorts = ranked.le(k, axis=0).astype(float)
    weights = longs.sub(shorts).div(k, axis=0)
    return weights.where(n_valid >= 2, 0.0, axis=0)
