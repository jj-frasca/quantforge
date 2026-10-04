from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

import numpy as np
import numpy.typing as npt
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from app.data.models import DataQualityReport
from app.research.backtesting.manifest import compute_parameter_hash
from app.research.backtesting.metrics import ReturnMoments, return_moments, sharpe_ratio
from app.research.claim_graph import FrozenClaimList, freeze_claim_model
from app.research.cross_sectional.engine import (
    asset_returns,
    portfolio_returns,
    split_panel_holdout,
)
from app.research.cross_sectional.ic import ICSummary, rank_ic, summarize_ic
from app.research.cross_sectional.manifest import CrossSectionalManifest
from app.research.cross_sectional.registry import (
    CrossSectionalStrategy,
    Params,
    default_strategies,
)
from app.research.cross_sectional.snapshots import freeze_score_snapshot
from app.research.lab.candidate_budget import allocate_candidate_budget
from app.research.lab.experiment import Graduate, Trial, validated_trial_update
from app.research.lab.gate import GateConfig, GateResult, GraduationGate
from app.research.lab.holdout import HoldoutScore
from app.research.lab.trial_accounting import (
    whole_search_deflated_sharpe_probabilities,
    whole_search_deflated_sharpes,
)
from app.validation.deflated_sharpe import deflated_sharpe
from app.validation.parameter_stability import parameter_stability
from app.validation.pbo import probability_of_backtest_overfitting
from app.validation.purged_cv import purged_kfold_splits
from app.validation.report import ValidationReport
from app.validation.walk_forward import walk_forward_splits

_MIN_CONFIGS_FOR_PBO = 2
_DAYS_PER_YEAR = 365.25

_Config = tuple[Params, float]  # (signal params, quantile)


class CrossSectionalTrial(Trial):
    """A cross-sectional finalist (ADR-035). Adds the rank IC of the signal that produced it — the
    direct measurement of the ranking claim, which the portfolio return series alone cannot
    distinguish from a two-name concentration story. Nullable: trials persisted before ADR-035 are
    honestly "not measured", never backfilled. Nothing gates, selects, or sizes on it."""

    ic: ICSummary | None = None


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
    trials: list[CrossSectionalTrial]
    lifetime_trials: int
    best_strategy_name: str | None = None
    best_gate_result: GateResult | None = None
    graduate: Graduate | None = None
    rationale: str = ""
    # ADR-138: legacy and synthetic rows have no vendor-panel acquisition claim. New production
    # rows persist the ordered component manifest and the complete report for every retained name.
    panel_manifest: CrossSectionalManifest | None = None
    data_quality_reports: list[DataQualityReport] | None = None
    # ADR-142: exact panel-projected non-price inputs; None retains legacy/unsupplied semantics.
    value_scores: Mapping[str, float] | None = None
    quality_scores: Mapping[str, float] | None = None

    @field_serializer("value_scores", "quality_scores")
    def _serialize_score_snapshot(
        self, scores: Mapping[str, float] | None
    ) -> dict[str, float] | None:
        return None if scores is None else dict(scores)

    @model_validator(mode="after")
    def _validate_panel_lineage(self) -> "CrossSectionalExperiment":
        # Pydantic's frozen models block attribute assignment but do not recursively freeze their
        # lists and dictionaries. Reconstruct every nested record before freezing it so a caller
        # retaining the original Trial/Graduate/report cannot mutate this persisted claim later.
        object.__setattr__(self, "universe_symbols", FrozenClaimList(self.universe_symbols))
        object.__setattr__(self, "strategy_names", FrozenClaimList(self.strategy_names))
        object.__setattr__(
            self,
            "gate_config",
            freeze_claim_model(self.gate_config),
        )
        object.__setattr__(
            self,
            "trials",
            FrozenClaimList([freeze_claim_model(trial) for trial in self.trials]),
        )
        if self.best_gate_result is not None:
            object.__setattr__(self, "best_gate_result", freeze_claim_model(self.best_gate_result))
        if self.graduate is not None:
            object.__setattr__(self, "graduate", freeze_claim_model(self.graduate))
        if self.panel_manifest is not None:
            object.__setattr__(self, "panel_manifest", freeze_claim_model(self.panel_manifest))
        if self.data_quality_reports is not None:
            object.__setattr__(
                self,
                "data_quality_reports",
                FrozenClaimList(
                    [freeze_claim_model(report) for report in self.data_quality_reports]
                ),
            )
        object.__setattr__(
            self, "value_scores", freeze_score_snapshot(self.value_scores, self.universe_symbols)
        )
        object.__setattr__(
            self,
            "quality_scores",
            freeze_score_snapshot(self.quality_scores, self.universe_symbols),
        )

        if self.trials:
            trial_names = [trial.strategy_name for trial in self.trials]
            if list(self.strategy_names) != trial_names:
                raise ValueError("strategy_names must exactly match trials in order")
        selected = next(
            (trial for trial in self.trials if trial.strategy_name == self.best_strategy_name), None
        )
        if self.best_strategy_name is not None and selected is None:
            raise ValueError("best_strategy_name must identify a persisted trial")
        if self.graduate is not None:
            if selected is None:
                raise ValueError("graduate requires the selected strategy trial")
            if self.best_gate_result is None:
                raise ValueError("graduate requires the best gate result")
            if self.graduate.strategy_name != selected.strategy_name:
                raise ValueError("graduate strategy must match the selected trial")
            if dict(self.graduate.parameters) != dict(selected.parameters):
                raise ValueError("graduate parameters must match the selected trial")
            if self.graduate.gate_result != self.best_gate_result:
                raise ValueError("graduate gate result must match the best gate result")
            if not self.best_gate_result.passed:
                raise ValueError("graduate requires a passing best gate result")
            if (
                self.best_gate_result.holdout_sharpe is not None
                and self.graduate.holdout_sharpe != self.best_gate_result.holdout_sharpe
            ):
                raise ValueError("graduate holdout Sharpe must match the best gate result")
            if (
                self.best_gate_result.holdout_n_bars is not None
                and self.graduate.holdout_n_bars != self.best_gate_result.holdout_n_bars
            ):
                raise ValueError("graduate holdout length must match the best gate result")
        if self.panel_manifest is None and self.data_quality_reports is None:
            return self
        if self.panel_manifest is None or self.data_quality_reports is None:
            raise ValueError("panel_manifest and data_quality_reports must be present together")
        manifest = self.panel_manifest
        if manifest.experiment_id != self.experiment_id:
            raise ValueError("panel manifest experiment_id must match experiment")
        if manifest.created_at != self.created_at:
            raise ValueError("panel manifest created_at must match experiment")
        if manifest.validation_config_hash != self.gate_config.version_hash:
            raise ValueError("panel manifest validation config must match experiment")
        components = {component.symbol: component for component in manifest.components}
        reports = {report.symbol: report for report in self.data_quality_reports}
        if len(components) != len(manifest.components):
            raise ValueError("panel manifest contains duplicate symbols")
        if len(reports) != len(self.data_quality_reports):
            raise ValueError("panel quality reports contain duplicate symbols")
        expected = self.universe_symbols
        if list(components) != expected or list(reports) != expected:
            raise ValueError("panel lineage symbols must exactly match the experiment universe")
        for symbol in expected:
            component = components[symbol]
            report = reports[symbol]
            if not report.passed:
                raise ValueError("panel lineage cannot retain a failed quality report")
            if report.source is None:
                raise ValueError("panel quality report must identify its source")
            if component.data_quality_report_id != report.id:
                raise ValueError("panel component report id must match embedded report")
            if component.data_source != report.source:
                raise ValueError("panel component source must match embedded report")
        if selected is None:
            raise ValueError("panel lineage requires the selected strategy trial")
        if manifest.strategy_name != selected.strategy_name:
            raise ValueError("panel manifest strategy must match selected trial")
        if manifest.parameter_hash != compute_parameter_hash(selected.parameters):
            raise ValueError("panel manifest parameter hash must match selected trial")
        return self


def _trial_params(params: Params, quantile: float) -> dict[str, float | int]:
    """Record the searched quantile alongside the signal params, so a finalist is fully specified."""
    return {**params, "quantile": quantile}


def _project_score_snapshot(
    scores: Mapping[str, float] | None, columns: pd.Index
) -> dict[str, float] | None:
    """Freeze only scores that could affect this panel, retaining panel order and missingness."""
    if scores is None:
        return None
    return {symbol: float(scores[symbol]) for symbol in columns if symbol in scores}


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
    quality_scores: Mapping[str, float] | None = None,
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
    in-sample panel to get one portfolio return series per config, and validate the (T, N) matrix.
    Family finalists receive one whole-search lifetime DSR haircut before the best strategy overall
    is scored once on the sealed holdout and fed to the unmodified GraduationGate (ADR-046). Their
    shared PBO is likewise computed over every current concrete config (ADR-104).
    """
    gate_config = config or GateConfig()
    frozen_value_scores = _project_score_snapshot(value_scores, prices.columns)
    frozen_quality_scores = _project_score_snapshot(quality_scores, prices.columns)
    registry = default_strategies(
        value_scores=frozen_value_scores, quality_scores=frozen_quality_scores
    )
    names = list(strategy_names) if strategy_names is not None else list(registry)
    in_sample, holdout = split_panel_holdout(prices)

    full_families: dict[str, list[_Config]] = {}
    for name in sorted(set(names)):
        strategy = registry.get(name)
        if strategy is not None:
            full_families[name] = [(p, q) for p in strategy.param_grid for q in quantiles]
    allocation = allocate_candidate_budget(
        full_families,
        budget=gate_config.trial_budget,
        parameters=lambda candidate: _trial_params(candidate[0], candidate[1]),
    )

    trials: list[CrossSectionalTrial] = []
    reports: list[ValidationReport] = []
    finalists: list[tuple[CrossSectionalStrategy, Params, float]] = []
    total_configs = 0
    candidate_sharpes: list[float] = []
    candidate_returns: list[npt.NDArray[np.float64]] = []
    finalist_moments: list[ReturnMoments | None] = []
    for name, allocated_configs in allocation.families.items():
        strategy = registry[name]
        configs = list(allocated_configs)
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
        candidate_sharpes.extend(sharpes)
        candidate_returns.extend(s.to_numpy(dtype=np.float64) for s in series)
        finalist_moments.append(return_moments(series[best_i]))
        # The IC is a property of the RANKING, so it is computed from the finalist's signal and is
        # independent of the quantile the portfolio happened to trade (ADR-035).
        finalist_signal = strategy.build(best_params)(in_sample)
        trials.append(
            CrossSectionalTrial(
                strategy_name=name,
                parameters=_trial_params(best_params, best_quantile),
                observed_sharpe=report.observed_sharpe,
                deflated_sharpe=report.deflated_sharpe,
                pbo=report.pbo,
                parameter_stability_score=report.parameter_stability_score,
                n_evaluated_configs=len(configs),
                ic=summarize_ic(rank_ic(finalist_signal, in_sample)),
            )
        )
        reports.append(report)
        finalists.append((strategy, best_params, best_quantile))

    if not trials:
        raise ValueError(
            "no valid cross-sectional strategies to search: none had a known registry entry with "
            f">= {_MIN_CONFIGS_FOR_PBO} configs (signal params x quantiles)"
        )

    lifetime_trials = prior_trials + total_configs
    observed = [trial.observed_sharpe for trial in trials]
    repriced = whole_search_deflated_sharpes(observed, candidate_sharpes, lifetime_trials)
    probabilities = whole_search_deflated_sharpe_probabilities(
        observed, finalist_moments, candidate_sharpes, lifetime_trials
    )
    whole_search_pbo = probability_of_backtest_overfitting(
        np.column_stack(candidate_returns), pbo_splits
    )
    trials = [
        validated_trial_update(
            trial,
            {
                "deflated_sharpe": dsr,
                "deflated_sharpe_probability": psr,
                "pbo": whole_search_pbo,
            },
        )
        for trial, dsr, psr in zip(trials, repriced, probabilities, strict=True)
    ]
    best_idx = max(range(len(trials)), key=lambda i: trials[i].observed_sharpe)
    best_report = reports[best_idx].model_copy(
        update={
            "deflated_sharpe": trials[best_idx].deflated_sharpe,
            "pbo": whole_search_pbo,
        }
    )
    strategy, params, quantile = finalists[best_idx]

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
        value_scores=frozen_value_scores,
        quality_scores=frozen_quality_scores,
    )
