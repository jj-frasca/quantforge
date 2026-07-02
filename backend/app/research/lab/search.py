import pandas as pd

from app.data.fundamentals import (
    FundamentalCriteria,
    FundamentalScreen,
    FundamentalSnapshot,
    screen_fundamentals,
)
from app.research.backtesting.engine import BacktestEngine
from app.research.lab.experiment import Experiment, Graduate, Trial
from app.research.lab.gate import GateConfig, GraduationGate
from app.research.lab.holdout import score_on_holdout, split_holdout
from app.research.strategies.base import BaseStrategy
from app.research.strategies.grid_generator import find_catalog_entry, grid_from_catalog
from app.validation.engine import ValidationEngine

_MIN_CONFIGS_FOR_PBO = 2


def _numeric_params(strategy: BaseStrategy) -> dict[str, float | int]:
    return {k: v for k, v in strategy.parameters.items() if isinstance(v, int | float)}


def _best_config(
    configs: list[BaseStrategy], frame: pd.DataFrame, engine: BacktestEngine
) -> BaseStrategy:
    """The config with the highest in-sample Sharpe — matches ValidationEngine's own `best`
    selection, so the holdout is scored on the same config the report describes."""
    best = configs[0]
    best_sharpe = float("-inf")
    for config in configs:
        sharpe = engine.run_strategy(frame, config).metrics.sharpe
        if sharpe > best_sharpe:
            best_sharpe, best = sharpe, config
    return best


def run_search(
    frame: pd.DataFrame,
    symbol: str,
    strategy_names: list[str],
    *,
    config: GateConfig | None = None,
    prior_trials: int = 0,
    n_per_param: int = 3,
    fundamentals: FundamentalSnapshot | None = None,
    fundamental_criteria: FundamentalCriteria | None = None,
    rationale: str = "",
) -> Experiment:
    """Run one search: validate each catalog strategy on the in-sample split, pick the best by
    deflated Sharpe, score it on the sealed holdout, and apply the graduation gate (ADR-014/016).

    The holdout is split here and never handed to any per-strategy step — only `score_on_holdout`
    touches it, once, for the finalist. Every candidate is recorded as a Trial; the best
    candidate's verdict (pass or fail) is always attached so failures are legible.
    """
    gate_config = config or GateConfig()
    handle, sealed = split_holdout(frame, symbol)
    engine = BacktestEngine()
    validator = ValidationEngine()

    trials: list[Trial] = []
    best_configs: list[BaseStrategy] = []
    reports = []
    for name in strategy_names:
        entry = find_catalog_entry(name)
        if entry is None:
            continue
        configs = grid_from_catalog(entry, n_per_param=n_per_param)
        if len(configs) < _MIN_CONFIGS_FOR_PBO:
            continue
        report = validator.validate(name, configs, handle.frame)
        best_config = _best_config(configs, handle.frame, engine)
        trials.append(
            Trial(
                strategy_name=report.strategy_name,
                parameters=_numeric_params(best_config),
                observed_sharpe=report.observed_sharpe,
                deflated_sharpe=report.deflated_sharpe,
                pbo=report.pbo,
                parameter_stability_score=report.parameter_stability_score,
            )
        )
        best_configs.append(best_config)
        reports.append(report)

    if not trials:
        raise ValueError(
            "no valid strategies to search: none had a catalog entry with "
            f">= {_MIN_CONFIGS_FOR_PBO} grid configs"
        )

    lifetime_trials = prior_trials + len(trials)
    best_idx = max(range(len(trials)), key=lambda i: trials[i].deflated_sharpe)
    best_report = reports[best_idx]
    holdout = score_on_holdout(sealed, best_configs[best_idx])
    gate_result = GraduationGate().evaluate(
        report=best_report,
        track_record_years=handle.years,
        n_trials=lifetime_trials,
        holdout=holdout,
        config=gate_config,
    )
    screen: FundamentalScreen | None = None
    if fundamentals is not None and fundamental_criteria is not None:
        screen = screen_fundamentals(fundamentals, fundamental_criteria)

    # Fundamentals veto: a name that fails the 'sane fundamentals' screen cannot graduate no
    # matter how good the technicals look (ADR-017). No screen (e.g. an ETF) = technicals only.
    fundamentals_ok = screen is None or screen.passed
    graduate = None
    if gate_result.passed and fundamentals_ok:
        graduate = Graduate(
            strategy_name=best_report.strategy_name,
            parameters=trials[best_idx].parameters,
            gate_result=gate_result,
            holdout_sharpe=holdout.sharpe,
            holdout_total_return=holdout.total_return,
        )

    return Experiment(
        symbol=symbol,
        strategy_names=[t.strategy_name for t in trials],
        gate_config=gate_config,
        trials=trials,
        lifetime_trials=lifetime_trials,
        best_strategy_name=best_report.strategy_name,
        best_gate_result=gate_result,
        fundamentals=fundamentals,
        fundamental_screen=screen,
        graduate=graduate,
        rationale=rationale,
    )
