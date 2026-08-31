from collections.abc import Sequence
from typing import Literal

import pandas as pd

from app.data.fundamentals import (
    FundamentalCriteria,
    FundamentalScreen,
    FundamentalSnapshot,
    screen_fundamentals,
)
from app.research.backtesting.engine import BacktestEngine
from app.research.backtesting.metrics import ReturnMoments, return_moments
from app.research.fundamentals.distress import DistressScreen
from app.research.lab.candidate_budget import (
    allocate_catalog_candidate_budget,
    select_space_filling_candidates,
)
from app.research.lab.experiment import Experiment, Graduate, Trial
from app.research.lab.gate import GateConfig, GraduationGate
from app.research.lab.holdout import score_on_holdout, split_holdout
from app.research.lab.trial_accounting import (
    whole_search_deflated_sharpe_probabilities,
    whole_search_deflated_sharpes,
)
from app.research.strategies.base import BaseStrategy
from app.research.strategies.grid_generator import find_catalog_entry, refine_grid
from app.validation.engine import ValidationEngine
from app.validation.report import ValidationReport

_MIN_CONFIGS_FOR_PBO = 2


def _walk_forward_oos(report: ValidationReport) -> float | None:
    return report.walk_forward.mean_oos_sharpe if report.walk_forward else None


def _purged_cv_oos(report: ValidationReport) -> float | None:
    return report.purged_cv.mean_oos_sharpe if report.purged_cv else None


def _numeric_params(strategy: BaseStrategy) -> dict[str, float | int]:
    return {k: v for k, v in strategy.parameters.items() if isinstance(v, int | float)}


def _score_configs(
    configs: list[BaseStrategy], frame: pd.DataFrame, engine: BacktestEngine
) -> tuple[BaseStrategy, list[float], ReturnMoments | None]:
    """The config with the highest in-sample Sharpe — matches ValidationEngine's own `best`
    selection, so the holdout is scored on the same config the report describes.

    Notes:
        Also returns the winner's PER-PERIOD return moments. They are the two inputs the paper's
        DSR needs that a Sharpe alone cannot supply (ADR-054), and this loop is the only place
        the finalist's return series exists.
    """
    best = configs[0]
    best_sharpe = float("-inf")
    best_returns: pd.Series | None = None
    sharpes: list[float] = []
    for config in configs:
        result = engine.run_strategy(frame, config)
        sharpes.append(result.metrics.sharpe)
        if result.metrics.sharpe > best_sharpe:
            best_sharpe, best, best_returns = result.metrics.sharpe, config, result.returns
    moments = None if best_returns is None else return_moments(best_returns)
    return best, sharpes, moments


SelectBy = Literal["observed", "walk_forward"]


def _select_index(trials: Sequence[Trial], select_by: SelectBy) -> int:
    """Which family is the finalist (ADR-069).

    Notes:
        `observed` is the in-sample maximum this project has always used; `walk_forward` ranks the
        SELECTION PROCEDURE instead of its luckiest draw, using ADR-038's mean OOS Sharpe over the
        expanding train blocks — computed on the in-sample handle only, so it touches no sealed
        holdout. A family carrying no walk-forward number falls back to its observed Sharpe rather
        than ranking as a measured zero (ADR-067).
    """

    def rank(trial: Trial) -> float:
        prequential = trial.walk_forward_oos_sharpe
        if select_by == "walk_forward" and prequential is not None:
            return prequential
        return trial.observed_sharpe

    return max(range(len(trials)), key=lambda i: rank(trials[i]))


def run_search(
    frame: pd.DataFrame,
    symbol: str,
    strategy_names: list[str],
    *,
    config: GateConfig | None = None,
    prior_trials: int = 0,
    n_per_param: int = 3,
    refine: bool = False,
    refine_span: float = 0.25,
    fundamentals: FundamentalSnapshot | None = None,
    fundamental_criteria: FundamentalCriteria | None = None,
    distress_screen: DistressScreen | None = None,
    select_by: SelectBy = "observed",
    rationale: str = "",
) -> Experiment:
    """Run one search: validate each catalog strategy on the in-sample split, pick the best by
    deflated Sharpe, score it on the sealed holdout, and apply the graduation gate (ADR-014/016).

    The holdout is split here and never handed to any per-strategy step — only `score_on_holdout`
    touches it, once, for the finalist. Every family's finalist is recorded as a Trial; the best
    candidate's verdict (pass or fail) is always attached so failures are legible.
    ``n_evaluated_configs`` and ``lifetime_trials`` count the concrete hypotheses that produced
    those compact summaries (ADR-046).
    """
    gate_config = config or GateConfig()
    handle, sealed = split_holdout(frame, symbol)
    engine = BacktestEngine()
    validator = ValidationEngine()

    allocation = allocate_catalog_candidate_budget(
        strategy_names,
        n_per_param=n_per_param,
        budget=gate_config.trial_budget,
        refine=refine,
    )
    trials: list[Trial] = []
    best_configs: list[BaseStrategy] = []
    reports: list[ValidationReport] = []
    candidate_sharpes: list[float] = []
    finalist_moments: list[ReturnMoments | None] = []
    for name, allocated_configs in allocation.families.items():
        configs = list(allocated_configs)
        report = validator.validate(name, configs, handle.frame)
        best_config, config_sharpes, moments = _score_configs(configs, handle.frame, engine)
        candidate_sharpes.extend(config_sharpes)
        finalist_moments.append(moments)
        trials.append(
            Trial(
                strategy_name=report.strategy_name,
                parameters=_numeric_params(best_config),
                observed_sharpe=report.observed_sharpe,
                deflated_sharpe=report.deflated_sharpe,
                pbo=report.pbo,
                parameter_stability_score=report.parameter_stability_score,
                n_evaluated_configs=len(configs),
                walk_forward_oos_sharpe=_walk_forward_oos(report),
                purged_cv_oos_sharpe=_purged_cv_oos(report),
            )
        )
        best_configs.append(best_config)
        reports.append(report)

    if not trials:
        raise ValueError(
            "no valid strategies to search: none had a catalog entry with "
            f">= {_MIN_CONFIGS_FOR_PBO} grid configs"
        )

    best_idx = _select_index(trials, select_by)

    # Coarse-to-fine (ADR-014): zoom in around the coarse winner. Every refined CONFIG raises the
    # DSR/MinTRL bar, so searching harder self-polices against overfitting (ADR-046).
    if refine:
        entry = find_catalog_entry(trials[best_idx].strategy_name)
        refined_configs = (
            refine_grid(
                entry, trials[best_idx].parameters, n_per_param=n_per_param, span_frac=refine_span
            )
            if entry is not None
            else []
        )
        budgeted_refined = select_space_filling_candidates(
            refined_configs,
            allocation.refinement_reserve,
            parameters=_numeric_params,
        )
        if len(budgeted_refined) >= _MIN_CONFIGS_FOR_PBO:
            refined_configs = list(budgeted_refined)
            refined_report = validator.validate(
                trials[best_idx].strategy_name, refined_configs, handle.frame
            )
            refined_config, refined_sharpes, refined_moments = _score_configs(
                refined_configs, handle.frame, engine
            )
            candidate_sharpes.extend(refined_sharpes)
            finalist_moments.append(refined_moments)
            trials.append(
                Trial(
                    strategy_name=refined_report.strategy_name,
                    parameters=_numeric_params(refined_config),
                    observed_sharpe=refined_report.observed_sharpe,
                    deflated_sharpe=refined_report.deflated_sharpe,
                    pbo=refined_report.pbo,
                    parameter_stability_score=refined_report.parameter_stability_score,
                    n_evaluated_configs=len(refined_configs),
                    walk_forward_oos_sharpe=_walk_forward_oos(refined_report),
                    purged_cv_oos_sharpe=_purged_cv_oos(refined_report),
                )
            )
            reports.append(refined_report)
            best_configs.append(refined_config)

    lifetime_trials = prior_trials + len(candidate_sharpes)
    observed = [trial.observed_sharpe for trial in trials]
    repriced = whole_search_deflated_sharpes(observed, candidate_sharpes, lifetime_trials)
    probabilities = whole_search_deflated_sharpe_probabilities(
        observed, finalist_moments, candidate_sharpes, lifetime_trials
    )
    trials = [
        trial.model_copy(update={"deflated_sharpe": dsr, "deflated_sharpe_probability": psr})
        for trial, dsr, psr in zip(trials, repriced, probabilities, strict=True)
    ]
    best_idx = _select_index(trials, select_by)
    best_report = reports[best_idx].model_copy(
        update={"deflated_sharpe": trials[best_idx].deflated_sharpe}
    )
    finalist_config = best_configs[best_idx]
    holdout = score_on_holdout(sealed, finalist_config)
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
    # Distress veto (ADR-029 3c): a name in hard financial distress is also blocked, a business-
    # quality safety rail on top of the statistical one. No distress screen = not vetoed.
    distressed = distress_screen is not None and distress_screen.distressed
    fundamentals_ok = (screen is None or screen.passed) and not distressed
    graduate = None
    if gate_result.passed and fundamentals_ok:
        graduate = Graduate(
            strategy_name=best_report.strategy_name,
            parameters=_numeric_params(finalist_config),
            gate_result=gate_result,
            holdout_sharpe=holdout.sharpe,
            holdout_total_return=holdout.total_return,
            holdout_n_bars=holdout.n_bars,
        )

    # Imported here rather than at module scope: calibration.py imports run_search, so the
    # fingerprint's home cannot import search.py back without a cycle. Deliberately the SAME
    # function the calibration path calls — two implementations of one identity would drift
    # silently, and the whole value of the field is that the strings compare equal (ADR-052).
    from app.research.lab.calibration import calibration_search_version

    return Experiment(
        symbol=symbol,
        strategy_names=[t.strategy_name for t in trials],
        gate_config=gate_config,
        trials=trials,
        lifetime_trials=lifetime_trials,
        n_bars=len(frame),
        search_config_version=calibration_search_version(
            strategy_names,
            n_per_param=n_per_param,
            config=gate_config,
            refine=refine,
            refine_span=refine_span,
            select_by=select_by,
        ),
        walk_forward_hold_sharpe=(
            None
            if best_report.walk_forward is None
            else best_report.walk_forward.mean_oos_hold_sharpe
        ),
        purged_cv_hold_sharpe=(
            None if best_report.purged_cv is None else best_report.purged_cv.mean_oos_hold_sharpe
        ),
        best_strategy_name=best_report.strategy_name,
        best_gate_result=gate_result,
        fundamentals=fundamentals,
        fundamental_screen=screen,
        distress_screen=distress_screen,
        graduate=graduate,
        rationale=rationale,
    )
