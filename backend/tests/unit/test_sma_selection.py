"""Research-only train-prefix selection, never a full nested-search claim."""

from dataclasses import FrozenInstanceError
from importlib.util import find_spec
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.backtesting.engine import BacktestEngine
from app.research.lab.candidate_budget import (
    allocate_catalog_candidate_budget,
    select_space_filling_candidates,
)
from app.research.strategies.grid_generator import find_catalog_entry, refine_grid


def _selector():
    assert find_spec("app.research.lab.sma_selection") is not None, "missing train-only selector"
    from app.research.lab.sma_selection import select_sma_on_train

    return select_sma_on_train


def _frame(n=600):
    t = np.arange(n)
    return pd.DataFrame(
        {"close": 100 * np.exp(0.0001 * t + 0.02 * np.sin(t / 9))},
        index=pd.date_range("2020-01-01", periods=n),
    )


def _select(frame, **overrides):
    args = {
        "budget": 200,
        "n_per_param": 3,
        "refine": True,
        "refine_span": 0.25,
        "cost_rate": 0.001,
    }
    args.update(overrides)
    return _selector()(frame, **args)


def test_sma_train58_matches_original_primitive_receipt():
    result = _select(_frame(58))
    assert result.method == "sma-train-observed-v1"
    assert result.n_train == 58
    assert [(c.fast, c.slow) for c in result.candidates] == [
        (1, 2),
        (1, 251),
        (1, 500),
        (100, 251),
        (100, 500),
        (200, 251),
        (200, 500),
    ]
    assert result.coarse_count == 7
    assert result.refinement_reserve == 9
    assert result.raw_refinement_count == result.budgeted_refinement_count == 1
    assert result.evaluated_refinement_count == 0
    assert result.coarse_selected_index == result.selected_index == 0
    assert (result.selected.fast, result.selected.slow) == (1, 2)
    assert result.selected.sharpe == 20.251609905954144
    assert [c.sharpe for c in result.candidates[1:]] == [0.0] * 6
    assert result.n_hypotheses == result.n_engine_calls == 7


@pytest.mark.parametrize("budget", [4, 6, 9, 200])
def test_sma_actual_engine_trace_matches_independent_primitive_oracle(budget, monkeypatch):
    frame = _frame()
    # Alternating tail selects a long-window center, activating real refinement.
    frame.iloc[200:, 0] = frame.iloc[199, 0] * np.exp(0.3 * (np.arange(400) % 2))
    allocation = allocate_catalog_candidate_budget(
        ["sma"], n_per_param=3, budget=budget, refine=True
    )
    coarse = list(allocation.families["sma"])
    engine = BacktestEngine(cost_rate=0.002)
    scores = [engine.run_strategy(frame, c).metrics.sharpe for c in coarse]
    center = max(range(len(scores)), key=scores.__getitem__)
    entry = find_catalog_entry("sma")
    assert entry is not None
    raw = refine_grid(entry, coarse[center].parameters, n_per_param=3, span_frac=0.25)
    refined = select_space_filling_candidates(
        raw, allocation.refinement_reserve, parameters=lambda c: c.parameters
    )
    configs = coarse + (list(refined) if len(refined) >= 2 else [])
    expected_scores = [engine.run_strategy(frame, c).metrics.sharpe for c in configs]
    calls = []
    original = BacktestEngine.run_strategy

    def record(self, data, strategy):
        calls.append((len(data), strategy.parameters.copy(), self.cost_rate))
        return original(self, data, strategy)

    monkeypatch.setattr(BacktestEngine, "run_strategy", record)
    result = _select(frame, budget=budget, cost_rate=0.002)
    assert result.coarse_selected_index == center
    assert result.raw_refinement_count == len(raw)
    assert result.budgeted_refinement_count == len(refined)
    assert result.evaluated_refinement_count == len(configs) - len(coarse)
    assert [(c.fast, c.slow) for c in result.candidates] == [
        (c.parameters["fast"], c.parameters["slow"]) for c in configs
    ]
    assert [c.sharpe for c in result.candidates] == expected_scores
    assert [c.stage for c in result.candidates] == ["coarse"] * len(coarse) + ["refined"] * (
        len(configs) - len(coarse)
    )
    assert result.selected_index == max(range(len(configs)), key=expected_scores.__getitem__)
    assert result.n_engine_calls == result.n_hypotheses == len(calls) == len(configs) <= budget
    assert all(n == len(frame) and cost == 0.002 for n, _, cost in calls)
    if budget == 200:
        assert len(refined) == 9
        assert {(c.fast, c.slow) for c in result.candidates[:7]} & {
            (c.fast, c.slow) for c in result.candidates[7:]
        }, "repeated cross-pass hypotheses must remain evaluated"


@pytest.mark.parametrize("n", [1, 58])
def test_sma_flat_ties_keep_first_coarse_with_no_warmup_filter(n):
    frame = _frame(n)
    frame["close"] = 100.0
    result = _select(frame)
    assert result.selected_index == result.coarse_selected_index == 0
    assert all(c.sharpe == 0 for c in result.candidates)


def test_sma_negative_active_candidate_can_lose_to_warmup_zero(monkeypatch):
    def score(self, data, strategy):
        return SimpleNamespace(
            metrics=SimpleNamespace(sharpe=-1.0 if strategy.parameters["slow"] == 2 else 0.0)
        )

    monkeypatch.setattr(BacktestEngine, "run_strategy", score)
    result = _select(_frame(58), refine=False)
    assert result.selected_index == 1
    assert result.selected.sharpe == 0.0


def test_sma_ties_across_executed_pass_keep_first_coarse(monkeypatch):
    def score(self, data, strategy):
        p = strategy.parameters
        return SimpleNamespace(
            metrics=SimpleNamespace(sharpe=1.0 if p == {"fast": 100, "slow": 251} else 0.0)
        )

    monkeypatch.setattr(BacktestEngine, "run_strategy", score)
    result = _select(_frame(58))
    assert result.evaluated_refinement_count >= 2
    assert result.selected_index == result.coarse_selected_index == 3
    assert sum((c.fast, c.slow) == (100, 251) for c in result.candidates) == 2


@pytest.mark.parametrize(
    "settings_override",
    [
        {"budget": True},
        {"budget": 4.5},
        {"budget": 0},
        {"budget": -1},
        {"budget": 3},
        {"n_per_param": False},
        {"n_per_param": 2.5},
        {"n_per_param": 0},
        {"n_per_param": 1},
        {"refine": 1},
        {"refine_span": float("nan")},
        {"refine_span": float("inf")},
        {"refine_span": -0.1},
        {"refine_span": True},
        {"refine_span": ".25"},
        {"cost_rate": float("nan")},
        {"cost_rate": float("inf")},
        {"cost_rate": -0.1},
        {"cost_rate": True},
        {"cost_rate": ".001"},
    ],
)
def test_sma_invalid_settings_refuse_before_engine(settings_override, monkeypatch):
    calls = []
    monkeypatch.setattr(BacktestEngine, "run_strategy", lambda *a: calls.append(a))
    with pytest.raises(ValueError):
        _select(_frame(58), **settings_override)
    assert calls == []


@pytest.mark.parametrize(
    "kind",
    [
        "empty",
        "no-close",
        "nan",
        "inf",
        "zero",
        "negative",
        "object",
        "bool",
        "float32",
        "reverse",
        "duplicate",
    ],
)
def test_sma_invalid_train_refuses_before_engine(kind, monkeypatch):
    frame = _frame(58)
    if kind == "empty":
        frame = frame.iloc[:0]
    elif kind == "no-close":
        frame = frame.rename(columns={"close": "other"})
    elif kind in {"nan", "inf", "zero", "negative"}:
        frame.iloc[-1, 0] = {"nan": np.nan, "inf": np.inf, "zero": 0.0, "negative": -1.0}[kind]
    elif kind in {"object", "bool", "float32"}:
        frame["close"] = frame.close.astype(kind)
    elif kind == "reverse":
        frame = frame.iloc[::-1]
    else:
        frame.index = [0] * len(frame)
    calls = []
    monkeypatch.setattr(BacktestEngine, "run_strategy", lambda *a: calls.append(a))
    with pytest.raises(ValueError):
        _select(frame)
    assert calls == []


def test_sma_engine_failure_aborts_whole_call(monkeypatch):
    calls = []
    original = BacktestEngine.run_strategy

    def fail(self, data, strategy):
        calls.append(strategy)
        if len(calls) == 3:
            raise ValueError("unmeasurable candidate")
        return original(self, data, strategy)

    monkeypatch.setattr(BacktestEngine, "run_strategy", fail)
    with pytest.raises(ValueError, match="unmeasurable candidate"):
        _select(_frame(58))
    assert len(calls) == 3


def test_sma_trace_is_immutable_and_detached():
    frame = _frame(58)
    before = frame.copy(deep=True)
    result = _select(frame, budget=np.int64(200), n_per_param=np.int64(3))
    pd.testing.assert_frame_equal(frame, before)
    frame.iloc[:, 0] = 1.0
    assert result.n_train == 58 and result.selected.sharpe == 20.251609905954144
    assert type(result.budget) is type(result.n_per_param) is int
    with pytest.raises(FrozenInstanceError):
        result.selected_index = 2
    with pytest.raises(FrozenInstanceError):
        result.candidates[0].fast = 2
    assert isinstance(result.candidates, tuple)


@given(st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False))
@settings(max_examples=10, deadline=None)
def test_sma_train_selection_unchanged_by_unseen_suffix(slope):
    a = _frame()
    b = a.copy()
    b.iloc[200:, 0] = b.iloc[199, 0] * np.exp(slope * np.arange(400))
    assert _select(a.iloc[:58]) == _select(b.iloc[:58])


def test_sma_disabled_refinement_and_zero_span_keep_counts():
    for overrides in ({"refine": False}, {"refine_span": 0.0}):
        result = _select(_frame(58), **overrides)
        assert result.evaluated_refinement_count == 0
        assert result.n_hypotheses == 7
    result = _select(_frame(58), refine=False, budget=2, cost_rate=0.0)
    assert result.n_hypotheses == 2 and result.refinement_reserve == 0


def test_sma_duplicate_close_columns_refuse_before_engine(monkeypatch):
    frame = _frame(58)
    frame = pd.concat([frame, frame], axis=1)
    calls = []
    monkeypatch.setattr(BacktestEngine, "run_strategy", lambda *a: calls.append(a))
    with pytest.raises(ValueError, match="unique columns"):
        _select(frame)
    assert calls == []
