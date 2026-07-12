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
        trades one name per side.
    """
    if not 0.0 < quantile <= 0.5:
        raise ValueError("quantile must be in (0, 0.5]")

    weights = pd.DataFrame(0.0, index=signals.index, columns=signals.columns)
    for date, row in signals.iterrows():
        valid = row.dropna()
        n = len(valid)
        if n < 2:
            continue
        k = max(1, int(quantile * n))
        ranked = valid.rank(method="first")  # 1 = lowest signal
        longs = ranked.index[ranked > n - k]
        shorts = ranked.index[ranked <= k]
        weights.loc[date, longs] = 1.0 / len(longs)
        weights.loc[date, shorts] = -1.0 / len(shorts)
    return weights
