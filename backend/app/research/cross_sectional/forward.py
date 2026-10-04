"""Forward-testing for cross-sectional graduates (ADR-025).

A cross-sectional graduate is a whole dollar-neutral long/short PORTFOLIO, not one symbol, so it is
forward-tested by continuing to compute its engine `portfolio_returns` on bars AFTER its freeze
boundary and benchmarking against the equal-weight long-only universe -- the same benchmark ADR-024
used at the holdout. This mirrors the SHAPE of the single-name `paper.py` / `portfolio_manager.py`
(ADR-019/020) at the portfolio level, reusing the ADR-024 engine + registry unchanged. Pure over
injectable panels -- no network, no look-ahead (weights at t use prices <= t).
"""

from collections.abc import Callable, Mapping
from datetime import datetime
from itertools import pairwise
from math import isclose, isfinite
from types import MappingProxyType
from typing import Literal, cast

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, model_validator

from app.research.backtesting.metrics import max_drawdown, sharpe_ratio
from app.research.claim_graph import FrozenClaimList, freeze_claim_model
from app.research.cross_sectional.engine import asset_returns, portfolio_returns
from app.research.cross_sectional.hunt import price_panel_from_frames
from app.research.cross_sectional.registry import default_strategies
from app.research.cross_sectional.search import CrossSectionalExperiment
from app.research.cross_sectional.snapshots import freeze_score_snapshot
from app.research.dataset import ResearchDataset, ResearchDatasetEvidence
from app.research.forward_claims import (
    forward_timestamp_utc,
    validate_forward_curve,
    validate_forward_equities,
    validate_forward_statistics,
)


class CrossSectionalForwardEquityPoint(BaseModel):
    """One bar of the forward equity curve (ADR-023 analog): normalized indices (base 1.0 at the
    freeze boundary) that compound each post-freeze bar -- the factor vs the equal-weight benchmark."""

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    timestamp: datetime
    strategy_equity: float
    benchmark_equity: float

    @field_validator("timestamp")
    @classmethod
    def _timestamp_utc(cls, value: datetime) -> datetime:
        return forward_timestamp_utc(value)

    @model_validator(mode="after")
    def _validate_equities(self) -> "CrossSectionalForwardEquityPoint":
        validate_forward_equities((self.strategy_equity, self.benchmark_equity))
        return self


class CrossSectionalForwardScore(BaseModel):
    """A frozen cross-sectional graduate's out-of-sample track record (ADR-025), scored ONLY on bars
    after its freeze date. `benchmark_*` is the equal-weight long-only universe (ADR-024's holdout
    benchmark); `beats_benchmark` is the honest bar: did the dollar-neutral factor out-earn holding
    the whole universe, risk-adjusted, going forward?"""

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    forward_bars: int
    forward_return: float
    forward_sharpe: float
    benchmark_return: float
    benchmark_sharpe: float
    beats_benchmark: bool
    as_of: datetime
    forward_equity: list[CrossSectionalForwardEquityPoint] = []
    # ADR-140: absent only for legacy rows and direct synthetic scoring.
    evidence: list[ResearchDatasetEvidence] | None = None

    @field_validator("as_of")
    @classmethod
    def _as_of_utc(cls, value: datetime) -> datetime:
        return forward_timestamp_utc(value)

    @model_validator(mode="after")
    def _validate_and_freeze_score(self) -> "CrossSectionalForwardScore":
        validate_forward_statistics(
            self.forward_bars,
            (
                self.forward_return,
                self.forward_sharpe,
                self.benchmark_return,
                self.benchmark_sharpe,
            ),
        )
        validate_forward_curve(
            [
                (point.timestamp, point.strategy_equity, point.benchmark_equity)
                for point in self.forward_equity
            ],
            forward_bars=self.forward_bars,
            forward_return=self.forward_return,
            benchmark_return=self.benchmark_return,
            as_of=self.as_of,
        )
        object.__setattr__(self, "forward_equity", FrozenClaimList(self.forward_equity))
        if self.evidence is not None:
            symbols = [item.quality_report.symbol.strip().upper() for item in self.evidence]
            if not symbols or len(symbols) != len(set(symbols)):
                raise ValueError("score evidence symbols must be non-empty and unique")
            if len({item.git_commit_hash for item in self.evidence}) != 1:
                raise ValueError("score evidence must name one git revision")
            object.__setattr__(self, "evidence", FrozenClaimList(self.evidence))
        return self


class CrossSectionalPosition(BaseModel):
    """A cross-sectional graduate frozen for forward-testing (ADR-025). Its config -- the strategy,
    the searched signal params AND quantile, the universe, the cost rate, and any static value and
    quality snapshots -- is locked as of `frozen_at`; everything after is genuinely unseen. `score`
    is the latest forward evaluation (None until first run). A factor is managed: retired when it
    deteriorates, kept afterward as an honest record and never re-promoted."""

    model_config = ConfigDict(frozen=True)

    strategy_name: str
    parameters: Mapping[str, float | int]
    universe_symbols: tuple[str, ...]
    cost_rate: float
    frozen_at: datetime
    value_scores: Mapping[str, float] | None = None
    quality_scores: Mapping[str, float] | None = None
    score: CrossSectionalForwardScore | None = None
    status: Literal["open", "retired"] = "open"
    retired_at: datetime | None = None
    exit_reasons: list[str] = []

    @field_serializer("value_scores", "quality_scores")
    def _serialize_score_snapshot(
        self, scores: Mapping[str, float] | None
    ) -> dict[str, float] | None:
        return None if scores is None else dict(scores)

    @field_serializer("parameters")
    def _serialize_parameters(
        self, parameters: Mapping[str, float | int]
    ) -> dict[str, float | int]:
        return dict(parameters)

    @model_validator(mode="after")
    def _validate_and_freeze_claim(self) -> "CrossSectionalPosition":
        if not isfinite(self.cost_rate) or self.cost_rate < 0.0:
            raise ValueError("cost_rate must be finite and non-negative")
        normalized_symbols = [symbol.strip().upper() for symbol in self.universe_symbols]
        if not normalized_symbols or any(not symbol for symbol in normalized_symbols):
            raise ValueError("frozen universe must be non-empty")
        if len(normalized_symbols) != len(set(normalized_symbols)):
            raise ValueError("frozen universe symbols must be unique")

        if self.status == "open":
            if self.retired_at is not None or self.exit_reasons:
                raise ValueError("open factor cannot have retirement metadata")
        else:
            if self.retired_at is None:
                raise ValueError("retired factor requires retired_at")
            if not self.exit_reasons:
                raise ValueError("retired factor requires exit reasons")

        score = self.score
        if score is not None:
            if score.forward_bars < 0:
                raise ValueError("forward_bars must be non-negative")
            statistics = (
                score.forward_return,
                score.forward_sharpe,
                score.benchmark_return,
                score.benchmark_sharpe,
            )
            if not all(isfinite(value) for value in statistics):
                raise ValueError("forward statistics must be finite")
            if score.evidence is not None:
                evidence_symbols = [
                    item.quality_report.symbol.strip().upper() for item in score.evidence
                ]
                if evidence_symbols != normalized_symbols:
                    raise ValueError("score evidence symbols must match frozen universe order")
                if len({item.git_commit_hash for item in score.evidence}) != 1:
                    raise ValueError("score evidence must name one git revision")

            curve = score.forward_equity
            if curve:
                if len(curve) != score.forward_bars:
                    raise ValueError("forward equity length must match forward_bars")
                try:
                    if any(
                        current.timestamp <= previous.timestamp
                        for previous, current in pairwise(curve)
                    ):
                        raise ValueError("forward equity timestamps must be strictly increasing")
                    if any(point.timestamp <= self.frozen_at for point in curve):
                        raise ValueError("forward equity timestamps must follow frozen_at")
                except TypeError as exc:
                    raise ValueError(
                        "forward equity timestamps must use compatible timezones"
                    ) from exc
                if any(
                    not isfinite(value) or value <= 0.0
                    for point in curve
                    for value in (point.strategy_equity, point.benchmark_equity)
                ):
                    raise ValueError("forward equity values must be finite and positive")
                terminal = curve[-1]
                if not (
                    isclose(
                        terminal.strategy_equity,
                        1.0 + score.forward_return,
                        rel_tol=1e-9,
                        abs_tol=1e-9,
                    )
                    and isclose(
                        terminal.benchmark_equity,
                        1.0 + score.benchmark_return,
                        rel_tol=1e-9,
                        abs_tol=1e-9,
                    )
                ):
                    raise ValueError("forward equity terminal values must match score returns")

        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
        object.__setattr__(
            self, "value_scores", freeze_score_snapshot(self.value_scores, self.universe_symbols)
        )
        object.__setattr__(
            self,
            "quality_scores",
            freeze_score_snapshot(self.quality_scores, self.universe_symbols),
        )
        object.__setattr__(self, "exit_reasons", FrozenClaimList(self.exit_reasons))
        if score is not None:
            object.__setattr__(
                self,
                "score",
                cast(CrossSectionalForwardScore, freeze_claim_model(score)),
            )
        return self


PanelDatasetProvider = Callable[[CrossSectionalPosition], Mapping[str, ResearchDataset]]


def _replace_position(
    position: CrossSectionalPosition, **updates: object
) -> CrossSectionalPosition:
    payload = position.model_dump(round_trip=True)
    payload.update(updates)
    return CrossSectionalPosition.model_validate(payload)


def _factor_returns(position: CrossSectionalPosition, panel: pd.DataFrame) -> pd.Series:
    """Recompute the frozen factor's portfolio return series over the FULL panel by rebuilding its
    signal from the unmodified registry. Warmup happens on the full panel; callers slice the
    post-freeze bars. Reuses `engine.portfolio_returns` -- no reinvented returns math."""
    registry = default_strategies(
        value_scores=position.value_scores, quality_scores=position.quality_scores
    )
    strategy = registry.get(position.strategy_name)
    if strategy is None:
        raise ValueError(f"unknown cross-sectional strategy {position.strategy_name!r}")
    params = {k: v for k, v in position.parameters.items() if k != "quantile"}
    quantile = float(position.parameters["quantile"])
    signal = strategy.build(params)(panel)
    return portfolio_returns(signal, panel, quantile=quantile, cost_rate=position.cost_rate)


def _benchmark_returns(panel: pd.DataFrame) -> pd.Series:
    """The equal-weight long-only universe return (ADR-024's holdout benchmark)."""
    return asset_returns(panel).mean(axis=1)


def score_forward(
    position: CrossSectionalPosition,
    panel: pd.DataFrame,
    *,
    evidence: list[ResearchDatasetEvidence] | None = None,
) -> CrossSectionalForwardScore:
    """Score `position` on the bars of `panel` strictly after its freeze date, vs the equal-weight
    long-only universe (ADR-025). The engine runs over the FULL panel so signals are warmed up by the
    freeze date; only the post-freeze slice is scored. No look-ahead; returns a zero-bar score when no
    forward data has accrued yet."""
    as_of = pd.Timestamp(panel.index.max())
    forward_mask = panel.index > pd.Timestamp(position.frozen_at)
    if not bool(forward_mask.any()):
        return CrossSectionalForwardScore(
            forward_bars=0,
            forward_return=0.0,
            forward_sharpe=0.0,
            benchmark_return=0.0,
            benchmark_sharpe=0.0,
            beats_benchmark=False,
            as_of=as_of.to_pydatetime(),
            evidence=evidence,
        )

    fwd = _factor_returns(position, panel)[forward_mask]
    bench = _benchmark_returns(panel)[forward_mask]
    fwd_sharpe = sharpe_ratio(fwd)
    bench_sharpe = sharpe_ratio(bench)
    strat_equity = (1.0 + fwd).cumprod()
    bench_equity = (1.0 + bench).cumprod()
    forward_equity = [
        CrossSectionalForwardEquityPoint(
            timestamp=ts.to_pydatetime(),
            strategy_equity=float(strat_equity.iloc[i]),
            benchmark_equity=float(bench_equity.iloc[i]),
        )
        for i, ts in enumerate(fwd.index)
    ]
    return CrossSectionalForwardScore(
        forward_bars=int(forward_mask.sum()),
        forward_return=float((1.0 + fwd).prod() - 1.0),
        forward_sharpe=fwd_sharpe,
        benchmark_return=float((1.0 + bench).prod() - 1.0),
        benchmark_sharpe=bench_sharpe,
        beats_benchmark=fwd_sharpe > bench_sharpe,
        as_of=as_of.to_pydatetime(),
        forward_equity=forward_equity,
        evidence=evidence,
    )


def _frozen_panel(
    position: CrossSectionalPosition, datasets: Mapping[str, ResearchDataset]
) -> tuple[pd.DataFrame, list[ResearchDatasetEvidence]]:
    """Validate and align the exact checked dataset set frozen on the position (ADR-140)."""
    expected = list(position.universe_symbols)
    if len(expected) != len(set(expected)):
        raise ValueError("frozen cross-sectional universe symbols must be unique")
    if set(datasets) != set(expected):
        raise ValueError("forward datasets must exactly match the frozen universe")

    ordered: list[ResearchDataset] = []
    for symbol in expected:
        dataset = datasets[symbol]
        if not isinstance(dataset, ResearchDataset):
            raise TypeError("cross-sectional forward provider must return ResearchDataset values")
        if dataset.quality_report.symbol != symbol.strip().upper():
            raise ValueError("forward dataset symbol does not match frozen universe symbol")
        ordered.append(dataset)
    if len({dataset.git_commit_hash for dataset in ordered}) != 1:
        raise ValueError("all forward panel datasets must name the same git revision")

    panel = price_panel_from_frames(
        {symbol: dataset.frame for symbol, dataset in zip(expected, ordered, strict=True)}
    )
    if list(panel.columns) != expected:
        raise ValueError("aligned forward panel must retain the exact frozen universe")
    return panel, [dataset.evidence() for dataset in ordered]


class CrossSectionalExitPolicy(BaseModel):
    """Tunable, versioned exit rules for a forward-tested cross-sectional factor (ADR-025) — the
    portfolio-level analog of the single-name ExitPolicy (ADR-020). A grace period avoids cutting on
    entry noise; a rolling trailing window measures RECENT decay so it isn't masked by early gains."""

    model_config = ConfigDict(frozen=True)

    min_forward_bars_before_exit: int = 21  # ~1mo grace
    rolling_window_bars: int = 63  # ~3mo trailing window
    min_rolling_sharpe: float = 0.0
    max_forward_drawdown: float = 0.30
    require_beat_benchmark_forward: bool = True


class CrossSectionalLifecycleDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    action: Literal["hold", "retire"]
    rolling_sharpe: float
    forward_drawdown: float
    rolling_benchmark_sharpe: float
    reasons: list[str] = []


def lifecycle_from_forward_returns(
    forward_returns: pd.Series,
    benchmark_returns: pd.Series,
    policy: CrossSectionalExitPolicy,
) -> CrossSectionalLifecycleDecision:
    """Decide hold/retire from a factor's FORWARD returns vs the equal-weight benchmark (ADR-025).
    Retire when recent (rolling-window) risk-adjusted performance decays below the floor, the forward
    drawdown breaches the risk limit, or it stops beating the benchmark. Pure -- no engine/network."""
    n = len(forward_returns)
    if n < policy.min_forward_bars_before_exit:
        return CrossSectionalLifecycleDecision(
            action="hold",
            rolling_sharpe=0.0,
            forward_drawdown=0.0,
            rolling_benchmark_sharpe=0.0,
            reasons=["grace period (insufficient forward data)"],
        )
    equity = (1.0 + forward_returns).cumprod()
    forward_drawdown = abs(max_drawdown(equity))
    roll = forward_returns.iloc[-policy.rolling_window_bars :]
    roll_bench = benchmark_returns.iloc[-policy.rolling_window_bars :]
    rolling_sharpe = sharpe_ratio(roll)
    rolling_bench_sharpe = sharpe_ratio(roll_bench)

    reasons: list[str] = []
    if rolling_sharpe <= policy.min_rolling_sharpe:
        reasons.append(
            f"rolling Sharpe {rolling_sharpe:.2f} <= {policy.min_rolling_sharpe} (edge has decayed)"
        )
    if forward_drawdown > policy.max_forward_drawdown:
        reasons.append(
            f"forward drawdown {forward_drawdown:.1%} > {policy.max_forward_drawdown:.0%} "
            "(risk limit)"
        )
    if policy.require_beat_benchmark_forward and rolling_sharpe <= rolling_bench_sharpe:
        reasons.append(
            f"rolling Sharpe {rolling_sharpe:.2f} <= equal-weight benchmark {rolling_bench_sharpe:.2f}"
            " (no longer beats holding the universe)"
        )
    return CrossSectionalLifecycleDecision(
        action="retire" if reasons else "hold",
        rolling_sharpe=rolling_sharpe,
        forward_drawdown=forward_drawdown,
        rolling_benchmark_sharpe=rolling_bench_sharpe,
        reasons=reasons,
    )


def evaluate_cross_sectional_lifecycle(
    position: CrossSectionalPosition, panel: pd.DataFrame, policy: CrossSectionalExitPolicy
) -> CrossSectionalLifecycleDecision:
    """Recompute the frozen factor's post-freeze forward returns + the equal-weight benchmark on
    `panel` and decide hold/retire (ADR-025). Holds during the grace period / before any forward
    data has accrued."""
    forward_mask = panel.index > pd.Timestamp(position.frozen_at)
    if not bool(forward_mask.any()):
        return CrossSectionalLifecycleDecision(
            action="hold",
            rolling_sharpe=0.0,
            forward_drawdown=0.0,
            rolling_benchmark_sharpe=0.0,
            reasons=["grace period (no forward data)"],
        )
    fwd = _factor_returns(position, panel)[forward_mask]
    bench = _benchmark_returns(panel)[forward_mask]
    return lifecycle_from_forward_returns(fwd, bench, policy)


def freeze_cross_sectional_graduate(
    experiment: CrossSectionalExperiment,
    frozen_at: datetime,
    *,
    cost_rate: float = 0.001,
) -> CrossSectionalPosition:
    """Freeze a cross-sectional graduate for forward-testing: lock its strategy, searched params +
    quantile, universe, cost rate, and fundamental score snapshots as of `frozen_at`."""
    graduate = experiment.graduate
    if graduate is None:
        raise ValueError("experiment has no graduate to freeze")
    if (
        graduate.strategy_name in {"xs_value", "xs_quality_value"}
        and experiment.value_scores is None
    ):
        raise ValueError("fundamental graduate lacks its frozen value-score snapshot")
    if (
        graduate.strategy_name in {"xs_quality", "xs_quality_value"}
        and experiment.quality_scores is None
    ):
        raise ValueError("fundamental graduate lacks its frozen quality-score snapshot")
    return CrossSectionalPosition(
        strategy_name=graduate.strategy_name,
        parameters=graduate.parameters,
        universe_symbols=tuple(experiment.universe_symbols),
        cost_rate=cost_rate,
        frozen_at=frozen_at,
        value_scores=experiment.value_scores,
        quality_scores=experiment.quality_scores,
    )


def manage_cross_sectional_book(
    positions: list[CrossSectionalPosition],
    graduate_experiments: list[CrossSectionalExperiment],
    panel_provider: PanelDatasetProvider,
    *,
    exit_policy: CrossSectionalExitPolicy | None = None,
    now: datetime,
    cost_rate: float = 0.001,
) -> list[CrossSectionalPosition]:
    """Advance the cross-sectional forward book one step (ADR-025, mirrors portfolio_manager): PROMOTE
    new graduates (freeze any factor -- (strategy, universe) -- not already tracked), MONITOR every
    OPEN position and RETIRE the deteriorating ones. Retired factors are kept as an honest record and
    never re-promoted. Pure over `panel_provider` -> testable without network."""
    policy = exit_policy or CrossSectionalExitPolicy()

    held = {(p.strategy_name, tuple(sorted(p.universe_symbols))) for p in positions}
    book = list(positions)
    for experiment in graduate_experiments:
        if experiment.graduate is None:
            continue
        key = (experiment.graduate.strategy_name, tuple(sorted(experiment.universe_symbols)))
        if key in held:
            continue
        try:
            position = freeze_cross_sectional_graduate(
                experiment, frozen_at=now, cost_rate=cost_rate
            )
        except ValueError:
            continue
        book.append(position)
        held.add(key)

    updated: list[CrossSectionalPosition] = []
    for position in book:
        if position.status != "open":
            updated.append(position)
            continue
        try:
            datasets = panel_provider(position)
            if not isinstance(datasets, Mapping):
                raise TypeError("cross-sectional forward provider must return a dataset mapping")
            panel, evidence = _frozen_panel(position, datasets)
            score = score_forward(position, panel, evidence=evidence)
            decision = evaluate_cross_sectional_lifecycle(position, panel, policy)
        except (ValueError, KeyError, OSError, ArithmeticError, TypeError):
            updated.append(position)
            continue
        if decision.action == "retire":
            updated.append(
                _replace_position(
                    position,
                    status="retired",
                    retired_at=now,
                    exit_reasons=decision.reasons,
                    score=score,
                )
            )
        else:
            updated.append(_replace_position(position, score=score))
    return updated
