from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

import numpy as np
import numpy.typing as npt
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from app.research.backtesting.metrics import sharpe_ratio
from app.research.cross_sectional.engine import (
    asset_returns,
    portfolio_returns,
    split_panel_holdout,
)
from app.research.cross_sectional.registry import (
    CrossSectionalStrategy,
    Params,
    default_strategies,
)
from app.research.lab.experiment import Graduate, Trial
from app.research.lab.gate import GateConfig, GateResult, GraduationGate
from app.research.lab.holdout import HoldoutScore
from app.validation.deflated_sharpe import deflated_sharpe
from app.validation.parameter_stability import parameter_stability
from app.validation.pbo import probability_of_backtest_overfitting
from app.validation.purged_cv import purged_kfold_splits
from app.validation.report import ValidationReport
from app.validation.walk_forward import walk_forward_splits

_MIN_CONFIGS_FOR_PBO = 2
_DAYS_PER_YEAR = 365.25

_Config = tuple[Params, float]  # (signal params, quantile)


class CrossSectionalExperiment(BaseModel):
    """One cross-sectional search run (ADR-024) — the per-strategy/universe analog of the
    single-name `Experiment`. Reproducible: the gate config, every strategy's finalist Trial, the
    lifetime trial count, and the winning graduate (if any) are all recorded."""

    model_config = ConfigDict(frozen=True)

    experiment_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    universe_symbols: list[str]
    strategy_names: list[str]
    gate_config: GateConfig
    trials: list[Trial]
    lifetime_trials: int
    best_strategy_name: str | None = None
    best_gate_result: GateResult | None = None
    graduate: Graduate | None = None
    rationale: str = ""


def _trial_params(params: Params, quantile: float) -> dict[str, float | int]:
    """Record the searched quantile alongside the signal params, so a finalist is fully specified."""
    return {**params, "quantile": quantile}


def _config_returns(
    strategy: CrossSectionalStrategy,
    params: Params,
    quantile: float,
    prices: pd.DataFrame,
    cost: float,
) -> pd.Series:
    signal = strategy.build(params)(prices)
    return portfolio_returns(signal, prices, quantile=quantile, cost_rate=cost)


def _build_report(
    name: str,
    matrix: npt.NDArray[np.float64],
    sharpes: list[float],
    n_obs: int,
    *,
    pbo_splits: int,
    walk_forward_count: int,
    purged_folds: int,
    embargo: int,
) -> ValidationReport:
    """Assemble a ValidationReport from the (T, N) matrix of a strategy's per-config portfolio
    returns — the same primitives ValidationEngine uses, only the inputs are portfolio series
    instead of one config's series. Regime breakdown is omitted (there is no single market close
    for a dollar-neutral portfolio); the gate does not use it."""
    pbo = probability_of_backtest_overfitting(matrix, pbo_splits)
    best = int(np.argmax(sharpes))
    observed = float(sharpes[best])
    sr_std = max(float(np.std(sharpes, ddof=1)), 1e-6)
    deflated = deflated_sharpe(observed, n_trials=matrix.shape[1], sr_std=sr_std)
    stability = parameter_stability(sharpes).stability_score
    return ValidationReport(
        strategy_name=name,
        observed_sharpe=observed,
        deflated_sharpe=deflated,
        pbo=pbo,
        parameter_stability_score=stability,
        n_walk_forward_splits=len(walk_forward_splits(n_obs, walk_forward_count)),
        n_purged_folds=len(purged_kfold_splits(n_obs, purged_folds, embargo)),
    )


def _score_holdout(
    strategy: CrossSectionalStrategy,
    params: Params,
    quantile: float,
    full_prices: pd.DataFrame,
    holdout: pd.DataFrame,
    cost: float,
) -> HoldoutScore:
    """Score the finalist on the sealed holdout: run over the FULL panel for warmup, then score only
    the post-split slice (leak-free — weights at t use only prices <= t, and only holdout dates are
    scored, mirroring paper.evaluate_forward). The benchmark is the equal-weight long-only universe
    — the cross-sectional analog of 'why not just hold it?'."""
    full_port = _config_returns(strategy, params, quantile, full_prices, cost)
    sliced = full_port.loc[holdout.index]
    equal_weight = asset_returns(full_prices).mean(axis=1).loc[holdout.index]
    total_return = float((1.0 + sliced).prod() - 1.0)
    return HoldoutScore(
        sharpe=sharpe_ratio(sliced),
        total_return=total_return,
        n_bars=len(sliced),
        buy_and_hold_sharpe=sharpe_ratio(equal_weight),
    )


def _track_record_years(index: pd.DatetimeIndex) -> float:
    span = index.max() - index.min()
    return float(span.days) / _DAYS_PER_YEAR


def run_cross_sectional_search(
    prices: pd.DataFrame,
    strategy_names: Sequence[str] | None = None,
    *,
    value_scores: Mapping[str, float] | None = None,
    quantiles: Sequence[float] = (0.1, 0.2, 0.3),
    config: GateConfig | None = None,
    prior_trials: int = 0,
    cost_rate: float = 0.001,
    pbo_splits: int = 10,
    walk_forward_count: int = 5,
    purged_folds: int = 5,
    embargo: int = 2,
    rationale: str = "",
) -> CrossSectionalExperiment:
    """Search the cross-sectional strategies over a price panel and apply the graduation gate
    (ADR-024). For each strategy: build config = (signal params x quantile), run the engine on the
    in-sample panel to get one portfolio return series per config, validate the (T, N) matrix, and
    keep the finalist by deflated Sharpe. The best strategy overall is scored once on the sealed
    holdout and fed to the unmodified GraduationGate.
    """
    gate_config = config or GateConfig()
    registry = default_strategies(value_scores=value_scores)
    names = list(strategy_names) if strategy_names is not None else list(registry)
    in_sample, holdout = split_panel_holdout(prices)

    trials: list[Trial] = []
    reports: list[ValidationReport] = []
    finalists: list[tuple[CrossSectionalStrategy, Params, float]] = []
    total_configs = 0
    for name in names:
        strategy = registry.get(name)
        if strategy is None:
            continue
        configs: list[_Config] = [(p, q) for p in strategy.param_grid for q in quantiles]
        if len(configs) < _MIN_CONFIGS_FOR_PBO:
            continue
        series = [_config_returns(strategy, p, q, in_sample, cost_rate) for p, q in configs]
        matrix = np.column_stack([s.to_numpy() for s in series])
        sharpes = [sharpe_ratio(s) for s in series]
        report = _build_report(
            name,
            matrix,
            sharpes,
            len(in_sample),
            pbo_splits=pbo_splits,
            walk_forward_count=walk_forward_count,
            purged_folds=purged_folds,
            embargo=embargo,
        )
        best_i = int(np.argmax(sharpes))
        best_params, best_quantile = configs[best_i]
        total_configs += len(configs)
        trials.append(
            Trial(
                strategy_name=name,
                parameters=_trial_params(best_params, best_quantile),
                observed_sharpe=report.observed_sharpe,
                deflated_sharpe=report.deflated_sharpe,
                pbo=report.pbo,
                parameter_stability_score=report.parameter_stability_score,
            )
        )
        reports.append(report)
        finalists.append((strategy, best_params, best_quantile))

    if not trials:
        raise ValueError(
            "no valid cross-sectional strategies to search: none had a known registry entry with "
            f">= {_MIN_CONFIGS_FOR_PBO} configs (signal params x quantiles)"
        )

    best_idx = max(range(len(trials)), key=lambda i: trials[i].deflated_sharpe)
    best_report = reports[best_idx]
    strategy, params, quantile = finalists[best_idx]

    lifetime_trials = prior_trials + total_configs
    holdout_score = _score_holdout(strategy, params, quantile, prices, holdout, cost_rate)
    gate_result = GraduationGate().evaluate(
        report=best_report,
        track_record_years=_track_record_years(in_sample.index),
        n_trials=lifetime_trials,
        holdout=holdout_score,
        config=gate_config,
    )
    graduate = None
    if gate_result.passed:
        graduate = Graduate(
            strategy_name=strategy.name,
            parameters=_trial_params(params, quantile),
            gate_result=gate_result,
            holdout_sharpe=holdout_score.sharpe,
            holdout_total_return=holdout_score.total_return,
            holdout_n_bars=holdout_score.n_bars,
        )

    return CrossSectionalExperiment(
        universe_symbols=list(prices.columns),
        strategy_names=[t.strategy_name for t in trials],
        gate_config=gate_config,
        trials=trials,
        lifetime_trials=lifetime_trials,
        best_strategy_name=strategy.name,
        best_gate_result=gate_result,
        graduate=graduate,
        rationale=rationale,
    )
