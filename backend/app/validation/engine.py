import numpy as np
import pandas as pd

from app.research.backtesting.engine import BacktestEngine
from app.research.strategies.base import BaseStrategy
from app.validation.deflated_sharpe import deflated_sharpe
from app.validation.parameter_stability import parameter_stability
from app.validation.pbo import probability_of_backtest_overfitting
from app.validation.purged_cv import purged_kfold_splits
from app.validation.report import Interpretation, ValidationReport
from app.validation.walk_forward import walk_forward_splits

_SHORT_SAMPLE = 100


def _interpret(pbo: float, dsr: float, stability: float) -> list[Interpretation]:
    """Plain-English thresholds for the headline metrics.

    Notes:
        Thresholds are intentionally simple and visible — a non-quant reader of the
        UI should see *what* each number means without having to know the methodology.
        Sources for the cutoffs: Bailey & López de Prado (2014) on PBO interpretation,
        Bailey & López de Prado (2014) DSR > 0 as the multiple-testing-survival bar,
        and a parameter-stability rule-of-thumb (>0.7 = robust, <0.4 = fragile).
    """
    items: list[Interpretation] = []

    if pbo < 0.3:
        items.append(
            Interpretation(
                metric="pbo",
                message=(
                    f"PBO {pbo:.0%} — overfitting risk is low; the strategy's edge is "
                    "unlikely to be a backtest artifact."
                ),
                verdict="good",
            )
        )
    elif pbo < 0.5:
        items.append(
            Interpretation(
                metric="pbo",
                message=(
                    f"PBO {pbo:.0%} — moderate overfitting risk; treat the result with caution."
                ),
                verdict="warning",
            )
        )
    else:
        items.append(
            Interpretation(
                metric="pbo",
                message=(
                    f"PBO {pbo:.0%} — high probability the strategy is overfit to the "
                    "parameter grid; do not trust this result."
                ),
                verdict="bad",
            )
        )

    if dsr > 0:
        items.append(
            Interpretation(
                metric="deflated_sharpe",
                message=(
                    f"Deflated Sharpe {dsr:.2f} — survives the multiple-testing penalty for "
                    "the number of configurations tried."
                ),
                verdict="good",
            )
        )
    else:
        items.append(
            Interpretation(
                metric="deflated_sharpe",
                message=(
                    f"Deflated Sharpe {dsr:.2f} — observed Sharpe doesn't survive the "
                    "multiple-testing penalty; plausibly attributable to luck."
                ),
                verdict="bad",
            )
        )

    if stability > 0.7:
        items.append(
            Interpretation(
                metric="parameter_stability_score",
                message=(
                    f"Parameter stability {stability:.0%} — results are robust to small "
                    "parameter perturbations."
                ),
                verdict="good",
            )
        )
    elif stability > 0.4:
        items.append(
            Interpretation(
                metric="parameter_stability_score",
                message=(
                    f"Parameter stability {stability:.0%} — moderate sensitivity to parameter "
                    "choice; some fragility."
                ),
                verdict="warning",
            )
        )
    else:
        items.append(
            Interpretation(
                metric="parameter_stability_score",
                message=(
                    f"Parameter stability {stability:.0%} — small parameter changes flip the "
                    "result; high model fragility."
                ),
                verdict="bad",
            )
        )

    return items


class ValidationEngine:
    """Runs the full validation suite over a strategy's config grid (ADR-008).

    Notes:
        Backtests every configuration, builds the (T, N) returns matrix for PBO, deflates the
        best config's Sharpe by the number of trials, and records walk-forward / purged-CV
        fold counts. Produces the ValidationReport — the MVP deliverable. A strategy is only
        "promising" if it survives (low PBO, positive deflated Sharpe).
    """

    def __init__(
        self,
        backtest_engine: BacktestEngine | None = None,
        pbo_splits: int = 10,
        walk_forward_count: int = 5,
        purged_folds: int = 5,
        embargo: int = 2,
    ) -> None:
        self._engine = backtest_engine or BacktestEngine()
        self._pbo_splits = pbo_splits
        self._walk_forward_count = walk_forward_count
        self._purged_folds = purged_folds
        self._embargo = embargo

    def validate(
        self, strategy_name: str, configs: list[BaseStrategy], data: pd.DataFrame
    ) -> ValidationReport:
        if len(configs) < 2:
            raise ValueError("need >= 2 configurations to estimate overfitting")

        returns_columns = []
        sharpes = []
        for strategy in configs:
            result = self._engine.run_strategy(data, strategy)
            returns_columns.append(result.returns.to_numpy())
            sharpes.append(result.metrics.sharpe)

        performance = np.column_stack(returns_columns)
        pbo = probability_of_backtest_overfitting(performance, self._pbo_splits)

        best = int(np.argmax(sharpes))
        observed_sharpe = float(sharpes[best])
        sr_std = max(float(np.std(sharpes, ddof=1)), 1e-6)
        deflated = deflated_sharpe(observed_sharpe, n_trials=len(configs), sr_std=sr_std)
        stability = parameter_stability(sharpes).stability_score

        n_obs = len(data)
        flags: list[str] = []
        if n_obs < _SHORT_SAMPLE:
            flags.append(f"short sample (<{_SHORT_SAMPLE} bars): low statistical confidence")
        if pbo >= 0.5:
            flags.append("high overfitting risk (PBO >= 0.5)")

        return ValidationReport(
            strategy_name=strategy_name,
            observed_sharpe=observed_sharpe,
            deflated_sharpe=deflated,
            pbo=pbo,
            parameter_stability_score=stability,
            n_walk_forward_splits=len(walk_forward_splits(n_obs, self._walk_forward_count)),
            n_purged_folds=len(purged_kfold_splits(n_obs, self._purged_folds, self._embargo)),
            flags=flags,
            interpretations=_interpret(pbo, deflated, stability),
        )
