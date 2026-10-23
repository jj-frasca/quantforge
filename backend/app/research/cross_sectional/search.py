from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

import numpy as np
import numpy.typing as npt
import pandas as pd
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

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
from app.research.cross_sectional.purged import (
    HIGH_PURGED_METHOD,
    PurgedDiagnostic,
    measure_family_purged,
    requested_fold_count,
)
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
from app.research.trial_counts import require_trial_count
from app.validation.deflated_sharpe import deflated_sharpe
from app.validation.parameter_stability import parameter_stability
from app.validation.pbo import probability_of_backtest_overfitting
from app.validation.purged_cv import purged_kfold_splits
from app.validation.report import ValidationReport
from app.validation.walk_forward import walk_forward_evaluate, walk_forward_splits

_MIN_CONFIGS_FOR_PBO = 2
_DAYS_PER_YEAR = 365.25

_Config = tuple[Params, float]  # (signal params, quantile)


class CrossSectionalTrial(Trial):
    """A cross-sectional finalist (ADR-035). Adds the rank IC of the signal that produced it — the
    direct measurement of the ranking claim, which the portfolio return series alone cannot
    distinguish from a two-name concentration story. Nullable: trials persisted before ADR-035 are
    honestly "not measured", never backfilled. Nothing gates, selects, or sizes on it."""

    ic: ICSummary | None = None
    purged_diagnostic: PurgedDiagnostic | None = None

    @model_validator(mode="after")
    def _validate_purged_evidence(self) -> "CrossSectionalTrial":
        evidence = self.purged_diagnostic
        if evidence is None:
            return self
        evidence = PurgedDiagnostic.model_validate(evidence)
        object.__setattr__(self, "purged_diagnostic", evidence)
        expected = evidence.mean_oos_sharpe if evidence.status == "measured" else None
        if self.purged_cv_oos_sharpe != expected:
            raise ValueError("trial purged scalar must match current evidence status and mean")
        if evidence.method == HIGH_PURGED_METHOD:
            if self.strategy_name != "xs_52w_high" or set(self.parameters) != {
                "window",
                "quantile",
            }:
                raise ValueError("high purged evidence requires its shipped family and parameters")
            window = require_trial_count(
                self.parameters["window"], minimum=1, parameter="purged finalist window"
            )
            if (
                window not in (126, 189, 252)
                or evidence.max_price_lag is None
                or evidence.max_price_lag < window
            ):
                raise ValueError("high purged allocated lag must cover its supported finalist")
        elif evidence.status != "unsupported":
            domains = {
                "xs_momentum": ("shifted-momentum-v1", {127, 148, 190, 211, 253, 274}),
                "xs_reversal": ("shifted-reversal-v1", {4, 6, 11}),
                "xs_short_term_reversal_1m": ("shifted-reversal-v1", {22, 43, 64}),
            }
            domain = domains.get(self.strategy_name)
            if (
                domain is None
                or evidence.dependency_rule != domain[0]
                or evidence.max_price_lag not in domain[1]
            ):
                raise ValueError("trial purged dependency must identify a supported family domain")
            keys = (
                {"lookback", "skip", "quantile"}
                if self.strategy_name == "xs_momentum"
                else {"lookback", "quantile"}
            )
            if set(self.parameters) != keys:
                raise ValueError("purged finalist must retain its shipped signal parameters")
            lookback = require_trial_count(
                self.parameters["lookback"], minimum=1, parameter="purged finalist lookback"
            )
            skip = require_trial_count(
                self.parameters.get("skip", 0), minimum=0, parameter="purged finalist skip"
            )
            if self.strategy_name == "xs_momentum" and (
                lookback not in (126, 189, 252) or skip not in (0, 21)
            ):
                raise ValueError("purged finalist must retain each shipped momentum parameter")
            finalist_lag = lookback + skip + 1
            if (
                finalist_lag not in domain[1]
                or evidence.max_price_lag is None
                or evidence.max_price_lag < finalist_lag
            ):
                raise ValueError("purged allocated lag must cover its supported finalist")
        return self


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
    # ADR-321: compact, paired family-local continuation evidence. Legacy rows are not backfilled.
    walk_forward_method: Literal["family-walk-forward-equal-weight-continuation-v1"] | None = None
    walk_forward_hold_sharpe: float | None = Field(default=None, allow_inf_nan=False)
    walk_forward_n_bars: int | None = None
    walk_forward_n_splits: int | None = None

    @field_validator("walk_forward_n_bars", "walk_forward_n_splits", mode="before")
    @classmethod
    def _validate_walk_forward_count(cls, value: object) -> int | None:
        if value is None:
            return None
        return require_trial_count(value, minimum=1, parameter="walk_forward geometry")

    @field_serializer("value_scores", "quality_scores")
    def _serialize_score_snapshot(
        self, scores: Mapping[str, float] | None
    ) -> dict[str, float] | None:
        return None if scores is None else dict(scores)

    @field_validator("lifetime_trials", mode="before")
    @classmethod
    def _validate_lifetime_count(cls, value: object) -> int:
        return require_trial_count(value, minimum=0, parameter="lifetime_trials")

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

    @model_validator(mode="after")
    def _validate_trial_accounting(self) -> "CrossSectionalExperiment":
        if self.lifetime_trials < sum(trial.n_evaluated_configs for trial in self.trials):
            raise ValueError("lifetime_trials must cover the recorded evaluated configurations")
        return self

    @model_validator(mode="after")
    def _validate_walk_forward_evidence(self) -> "CrossSectionalExperiment":
        evidence = (
            self.walk_forward_hold_sharpe,
            self.walk_forward_n_bars,
            self.walk_forward_n_splits,
        )
        if self.walk_forward_method is None:
            if any(value is not None for value in evidence):
                raise ValueError("walk-forward pairing and geometry require a method")
            return self
        if not self.trials or any(trial.walk_forward_oos_sharpe is None for trial in self.trials):
            raise ValueError("measured walk-forward requires every family mean and nonempty trials")
        if (
            self.walk_forward_hold_sharpe is None
            or self.walk_forward_n_bars is None
            or self.walk_forward_n_splits is None
        ):
            raise ValueError("measured walk-forward requires paired benchmark and geometry")
        if self.walk_forward_n_bars < self.walk_forward_n_splits + 1:
            raise ValueError("walk-forward bars must be >= splits + 1")
        return self

    @model_validator(mode="after")
    def _validate_purged_evidence(self) -> "CrossSectionalExperiment":
        evidence = [trial.purged_diagnostic for trial in self.trials]
        if not any(item is not None for item in evidence):
            return self
        if any(item is None for item in evidence):
            raise ValueError("current purged evidence requires every family outcome")
        first = evidence[0]
        assert first is not None
        request = (first.n_bars, first.requested_folds, first.floor)
        for item in evidence:
            assert item is not None
            if (item.n_bars, item.requested_folds, item.floor) != request:
                raise ValueError("purged families must carry the same request geometry")
            if self.walk_forward_method is not None and item.n_bars != self.walk_forward_n_bars:
                raise ValueError("purged bars must match attributed walk-forward bars")
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
    benchmark: npt.NDArray[np.float64] | None = None,
) -> ValidationReport:
    """Assemble a ValidationReport from the (T, N) matrix of a strategy's per-config portfolio
    returns — the same primitives ValidationEngine uses, only the inputs are portfolio series
    instead of one config's series. Regime breakdown is omitted (there is no single market close
    for a dollar-neutral portfolio); the gate does not use it. Walk-forward is family-local
    fixed-config continuation (ADR-321), with no whole-search winning-family or switching-account
    claim. Its equal-weight universe benchmark has no additional turnover-cost model."""
    pbo = probability_of_backtest_overfitting(matrix, pbo_splits)
    best = int(np.argmax(sharpes))
    observed = float(sharpes[best])
    sr_std = max(float(np.std(sharpes, ddof=1)), 1e-6)
    deflated = deflated_sharpe(observed, n_trials=matrix.shape[1], sr_std=sr_std)
    stability = parameter_stability(sharpes).stability_score
    walk_forward = walk_forward_evaluate(
        matrix, walk_forward_splits(n_obs, walk_forward_count), benchmark=benchmark
    )
    return ValidationReport(
        strategy_name=name,
        observed_sharpe=observed,
        deflated_sharpe=deflated,
        pbo=pbo,
        parameter_stability_score=stability,
        n_walk_forward_splits=walk_forward.n_splits,
        n_purged_folds=len(purged_kfold_splits(n_obs, purged_folds, embargo)),
        walk_forward=walk_forward,
        flags=[
            "Family-local walk-forward: whole-search winning-family selection is not walked forward.",
            "Fixed-config continuation includes internal costs, not account entry/switching trades.",
            "Static fundamental snapshots are conditional inputs, not point-in-time history.",
            "Purged CV not measured; fold count describes geometry only.",
        ],
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
    if (sliced <= -1.0).any():
        raise ValueError("holdout returns must preserve positive wealth")
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
    Original prior_trials must be a nonnegative nonboolean integral count and is
    normalized to Python int before arithmetic or search work.

    Family finalists receive one whole-search lifetime DSR haircut before the best strategy overall
    is scored once on the sealed holdout and fed to the unmodified GraduationGate (ADR-046). Their
    shared PBO is likewise computed over every current concrete config (ADR-104).
    """
    prior_trials = require_trial_count(prior_trials, minimum=0, parameter="prior_trials")
    embargo = require_trial_count(embargo, minimum=0, parameter="embargo")
    purged_folds = requested_fold_count(purged_folds)
    gate_config = config or GateConfig()
    frozen_value_scores = _project_score_snapshot(value_scores, prices.columns)
    frozen_quality_scores = _project_score_snapshot(quality_scores, prices.columns)
    registry = default_strategies(
        value_scores=frozen_value_scores, quality_scores=frozen_quality_scores
    )
    names = list(strategy_names) if strategy_names is not None else list(registry)
    in_sample, holdout = split_panel_holdout(prices)
    walk_forward_benchmark = asset_returns(in_sample).mean(axis=1).to_numpy()

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
    purged_inputs: list[tuple[CrossSectionalStrategy, list[_Config], npt.NDArray[np.float64]]] = []
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
            benchmark=walk_forward_benchmark,
        )
        purged_inputs.append((strategy, configs, matrix))
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
                walk_forward_oos_sharpe=report.walk_forward.mean_oos_sharpe
                if report.walk_forward is not None
                else None,
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
    for index, (strategy, configs, matrix) in enumerate(purged_inputs):
        report = reports[index]
        purged_evidence, purged_result = measure_family_purged(
            strategy,
            configs,
            in_sample,
            matrix,
            walk_forward_benchmark,
            floor=embargo,
            requested_folds=purged_folds,
        )
        purged_flag = (
            "Family-local purged CV uses later training rows and continued-config internal costs; "
            "it is not a causal switching-account score."
            if purged_result is not None
            else f"Purged CV not measured: {purged_evidence.status}"
            + (f" ({purged_evidence.reason})." if purged_evidence.reason else ".")
        )
        reports[index] = ValidationReport.model_validate(
            report.model_copy(
                update={
                    "purged_cv": purged_result,
                    "n_purged_folds": purged_result.n_folds if purged_result is not None else 0,
                    "flags": [
                        flag
                        for flag in report.flags
                        if flag != "Purged CV not measured; fold count describes geometry only."
                    ]
                    + [purged_flag],
                }
            )
        )
        trials[index] = validated_trial_update(
            trials[index],
            {
                "purged_diagnostic": purged_evidence,
                "purged_cv_oos_sharpe": purged_evidence.mean_oos_sharpe,
            },
        )
    best_idx = max(range(len(trials)), key=lambda i: trials[i].observed_sharpe)
    best_report = reports[best_idx].model_copy(
        update={
            "deflated_sharpe": trials[best_idx].deflated_sharpe,
            "pbo": whole_search_pbo,
        }
    )
    strategy, params, quantile = finalists[best_idx]

    paired_walk_forward = reports[0].walk_forward
    if paired_walk_forward is None or paired_walk_forward.mean_oos_hold_sharpe is None:
        raise ValueError("walk-forward measurement requires a paired benchmark")
    for report in reports:
        measured = report.walk_forward
        if (
            measured is None
            or measured.n_splits != paired_walk_forward.n_splits
            or [(split.n_train, split.n_test) for split in measured.splits]
            != [(split.n_train, split.n_test) for split in paired_walk_forward.splits]
            or measured.mean_oos_hold_sharpe != paired_walk_forward.mean_oos_hold_sharpe
        ):
            raise ValueError("walk-forward families must share evaluated geometry and benchmark")

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
        walk_forward_method="family-walk-forward-equal-weight-continuation-v1",
        walk_forward_hold_sharpe=paired_walk_forward.mean_oos_hold_sharpe,
        walk_forward_n_bars=len(in_sample),
        walk_forward_n_splits=paired_walk_forward.n_splits,
    )
