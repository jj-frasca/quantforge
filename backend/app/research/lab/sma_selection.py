"""Unused train-only SMA selection and one-window continuation (ADR-392/393)."""

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Literal

import numpy as np
import pandas as pd

from app.research.backtesting.engine import BacktestEngine
from app.research.backtesting.metrics import sharpe_ratio
from app.research.lab.candidate_budget import (
    allocate_catalog_candidate_budget,
    select_space_filling_candidates,
)
from app.research.strategies.base import BaseStrategy
from app.research.strategies.grid_generator import find_catalog_entry, refine_grid
from app.research.strategies.sma import SMAStrategy
from app.research.trial_counts import require_trial_count


@dataclass(frozen=True)
class SMATrainCandidate:
    """One actually evaluated hypothesis; repeated cross-pass params stay distinct."""

    stage: Literal["coarse", "refined"]
    fast: int
    slow: int
    sharpe: float


@dataclass(frozen=True)
class SMATrainSelection:
    """Ephemeral immutable trace, not a validated persisted research artifact."""

    n_train: int
    budget: int
    n_per_param: int
    refine: bool
    refine_span: float
    cost_rate: float
    refinement_reserve: int
    coarse_count: int
    coarse_selected_index: int
    raw_refinement_count: int
    budgeted_refinement_count: int
    candidates: tuple[SMATrainCandidate, ...]
    selected_index: int
    method: Literal["sma-train-observed-v1"] = "sma-train-observed-v1"

    @property
    def selected(self) -> SMATrainCandidate:
        return self.candidates[self.selected_index]

    @property
    def evaluated_refinement_count(self) -> int:
        return len(self.candidates) - self.coarse_count

    @property
    def n_hypotheses(self) -> int:
        return len(self.candidates)

    @property
    def n_engine_calls(self) -> int:
        # This helper runs each scored hypothesis once, with no validation replay.
        return len(self.candidates)


def _nonnegative_real(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite nonnegative nonboolean real")
    return float(value)


def _parameters(strategy: BaseStrategy) -> dict[str, float | int]:
    return {k: v for k, v in strategy.parameters.items() if isinstance(v, int | float)}


def _validated_close_frame(train: pd.DataFrame) -> pd.DataFrame:
    if train.empty or "close" not in train:
        raise ValueError("train must contain nonempty close prices")
    if not train.index.is_unique or not train.index.is_monotonic_increasing:
        raise ValueError("train calendar must be unique and ascending")
    if not train.columns.is_unique:
        raise ValueError("train must have unique columns")
    close = train["close"]
    if close.dtype != np.dtype("float64"):
        raise ValueError("train close must have native Float64 dtype")
    values = close.to_numpy()
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("train close must be positive and finite")
    # Known SMA needs close only; no mutable frame/strategy escapes in the trace.
    return train[["close"]].copy(deep=True)


def select_sma_on_train(
    train: pd.DataFrame,
    *,
    budget: int,
    n_per_param: int,
    refine: bool,
    refine_span: float,
    cost_rate: float,
) -> SMATrainSelection:
    """Select/refine using only supplied training prices (ADR-048/392).

    The caller must supply the complete chronological train prefix. This function
    cannot certify that boundary or source provenance. It implements only the
    declared single-SMA observed selector, not run_search or nested evaluation.
    Native engine Sharpe, first maximum, coarse-before-refined ordering and zero
    warmup candidates are preserved. Any failure aborts without a partial trace.
    """
    budget = require_trial_count(budget, minimum=1, parameter="budget")
    n_per_param = require_trial_count(n_per_param, minimum=1, parameter="n_per_param")
    if not isinstance(refine, bool):
        raise ValueError("refine must be boolean")
    refine_span = _nonnegative_real(refine_span, "refine_span")
    cost_rate = _nonnegative_real(cost_rate, "cost_rate")
    frame = _validated_close_frame(train)
    allocation = allocate_catalog_candidate_budget(
        ["sma"], n_per_param=n_per_param, budget=budget, refine=refine
    )
    coarse = allocation.families.get("sma", ())
    if len(coarse) < 2:
        raise ValueError("need >= 2 allocated SMA configurations")
    engine = BacktestEngine(cost_rate=cost_rate)
    candidates: list[SMATrainCandidate] = []

    def score(config: BaseStrategy, stage: Literal["coarse", "refined"]) -> None:
        result = engine.run_strategy(frame, config)
        candidates.append(
            SMATrainCandidate(
                stage=stage,
                fast=int(_parameters(config)["fast"]),
                slow=int(_parameters(config)["slow"]),
                sharpe=result.metrics.sharpe,
            )
        )

    for config in coarse:
        score(config, "coarse")
    coarse_selected_index = max(range(len(candidates)), key=lambda i: candidates[i].sharpe)
    raw_count = budgeted_count = 0
    if refine:
        entry = find_catalog_entry("sma")
        if entry is None:
            raise ValueError("SMA catalog entry is required")
        center = coarse[coarse_selected_index]
        raw = refine_grid(
            entry, _parameters(center), n_per_param=n_per_param, span_frac=refine_span
        )
        refined = select_space_filling_candidates(
            raw, allocation.refinement_reserve, parameters=_parameters
        )
        raw_count, budgeted_count = len(raw), len(refined)
        if budgeted_count >= 2:
            for config in refined:
                score(config, "refined")
    selected_index = max(range(len(candidates)), key=lambda i: candidates[i].sharpe)
    return SMATrainSelection(
        n_train=len(frame),
        budget=budget,
        n_per_param=n_per_param,
        refine=refine,
        refine_span=refine_span,
        cost_rate=cost_rate,
        refinement_reserve=allocation.refinement_reserve,
        coarse_count=len(coarse),
        coarse_selected_index=coarse_selected_index,
        raw_refinement_count=raw_count,
        budgeted_refinement_count=budgeted_count,
        candidates=tuple(candidates),
        selected_index=selected_index,
    )


@dataclass(frozen=True)
class SMATrainWindowContinuation:
    """One native-metric continuation, not a switched account (ADR-293/393)."""

    train_end: int
    test_end: int
    selection: SMATrainSelection
    test_net_returns: tuple[float, ...]
    test_gross_hold_returns: tuple[float, ...]
    oos_sharpe: float
    oos_hold_sharpe: float
    method: Literal["nested-sma-native-metrics-continuation-v1"] = (
        "nested-sma-native-metrics-continuation-v1"
    )

    @property
    def n_train(self) -> int:
        return self.train_end

    @property
    def n_test(self) -> int:
        return self.test_end - self.train_end

    @property
    def n_hypotheses(self) -> int:
        return self.selection.n_hypotheses

    @property
    def n_engine_calls(self) -> int:
        return self.selection.n_engine_calls + 1


def evaluate_sma_train_window(
    frame: pd.DataFrame,
    *,
    train_end: int,
    test_end: int,
    budget: int,
    n_per_param: int,
    refine: bool,
    refine_span: float,
    cost_rate: float,
) -> SMATrainWindowContinuation:
    """Select on [0, train_end), realize [train_end, test_end) (ADR-392/393).

    Only the used prefix is validated. Post-test independence requires identical
    prefix dtype/schema/calendar as well as values. Caller search/holdout and
    source boundaries are not certified. Scores use native backtesting metrics,
    not production WF's distinct Sharpe, and retain fixed-config internal costs.
    No aggregate nested estimator, flat start or account switching is claimed.
    """
    train_end = require_trial_count(train_end, minimum=1, parameter="train_end")
    test_end = require_trial_count(test_end, minimum=1, parameter="test_end")
    if not train_end < test_end <= len(frame):
        raise ValueError("need 1 <= train_end < test_end <= frame length")
    prefix = _validated_close_frame(frame.iloc[:test_end])
    selection = select_sma_on_train(
        prefix.iloc[:train_end],
        budget=budget,
        n_per_param=n_per_param,
        refine=refine,
        refine_span=refine_span,
        cost_rate=cost_rate,
    )
    winner = selection.selected
    continuation = BacktestEngine(cost_rate=selection.cost_rate).run_strategy(
        prefix, SMAStrategy(fast=winner.fast, slow=winner.slow)
    )
    net = continuation.returns.iloc[train_end:]
    hold = prefix["close"].pct_change().fillna(0.0).iloc[train_end:]
    if len(net) != test_end - train_end or len(hold) != test_end - train_end:
        raise ValueError("window return sequences must cover every test observation")
    net_score, hold_score = sharpe_ratio(net), sharpe_ratio(hold)
    return SMATrainWindowContinuation(
        train_end=train_end,
        test_end=test_end,
        selection=selection,
        test_net_returns=tuple(float(v) for v in net),
        test_gross_hold_returns=tuple(float(v) for v in hold),
        oos_sharpe=net_score,
        oos_hold_sharpe=hold_score,
    )
