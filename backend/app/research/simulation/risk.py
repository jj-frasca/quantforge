import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.research.simulation.monte_carlo import TRADING_DAYS, MonteCarloSimulator


@dataclass(frozen=True)
class MonteCarloRisk:
    """Forward-looking risk of a strategy over a horizon (ADR-014 Phase 0).

    Notes:
        A parametric bootstrap: we treat the strategy's realized daily returns as GBM inputs
        (annualized drift + vol) and simulate `n_paths` equity paths over `horizon_days`.
        Reports the probability the strategy ENDS down more than `loss_threshold`, the
        probability its worst intra-horizon drawdown breaches `loss_threshold`, and terminal-
        return percentiles. Flags POTENTIAL downside (CLAUDE.md rule 6) — it does not predict.
    """

    horizon_days: int
    n_paths: int
    loss_threshold: float
    prob_terminal_loss: float
    prob_max_drawdown_exceeds: float
    terminal_return_p5: float
    terminal_return_p50: float
    terminal_return_p95: float
    expected_terminal_return: float


def analyze_strategy_risk(
    returns: pd.Series,
    horizon_days: int,
    n_paths: int,
    loss_threshold: float,
    seed: int | None = None,
) -> MonteCarloRisk:
    if horizon_days < 1:
        raise ValueError("horizon_days must be >= 1")
    if n_paths < 1:
        raise ValueError("n_paths must be >= 1")
    if not 0.0 < loss_threshold <= 1.0:
        raise ValueError("loss_threshold must be in (0, 1]")
    if (
        not pd.api.types.is_numeric_dtype(returns.dtype)
        or pd.api.types.is_bool_dtype(returns.dtype)
        or pd.api.types.is_complex_dtype(returns.dtype)
    ):
        raise ValueError("returns must be real nonboolean numeric observations")
    values = returns.to_numpy(dtype=float, na_value=np.nan)
    if not np.isfinite(values).all() or (values <= -1.0).any():
        raise ValueError("returns must be finite and greater than -1")
    if len(returns) < 2:
        raise ValueError("need >= 2 return observations to estimate drift/vol")

    # Annualize the daily moments for the GBM sim (simulate() expects annualized mu/sigma
    # with dt = 1/252). Sample std uses ddof=1 to match the rest of the metrics layer.
    mu = float(returns.mean()) * TRADING_DAYS
    sigma = float(returns.std(ddof=1)) * math.sqrt(TRADING_DAYS)

    paths = MonteCarloSimulator().simulate(
        s0=1.0, mu=mu, sigma=sigma, n_steps=horizon_days, n_paths=n_paths, seed=seed
    )

    terminal_return = paths[:, -1] / paths[:, 0] - 1.0
    running_max = np.maximum.accumulate(paths, axis=1)
    max_drawdown_per_path = (paths / running_max - 1.0).min(axis=1)  # most-negative per path

    # ADR-175: a finite mean can have an overflowing intermediate sum. Preserve ordinary
    # results and normalize only on overflow; no terminal observation is clipped or dropped.
    with np.errstate(over="ignore"):
        expected_terminal_return = float(np.mean(terminal_return))
    if not math.isfinite(expected_terminal_return):
        scale = float(np.max(np.abs(terminal_return)))
        expected_terminal_return = float(np.mean(terminal_return / scale)) * scale

    return MonteCarloRisk(
        horizon_days=horizon_days,
        n_paths=n_paths,
        loss_threshold=loss_threshold,
        prob_terminal_loss=float(np.mean(terminal_return <= -loss_threshold)),
        prob_max_drawdown_exceeds=float(np.mean(max_drawdown_per_path <= -loss_threshold)),
        terminal_return_p5=float(np.percentile(terminal_return, 5)),
        terminal_return_p50=float(np.percentile(terminal_return, 50)),
        terminal_return_p95=float(np.percentile(terminal_return, 95)),
        expected_terminal_return=expected_terminal_return,
    )
