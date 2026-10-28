"""One-window research continuation, distinct from production WF (ADR-393)."""

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.backtesting.engine import BacktestEngine
from app.research.backtesting.metrics import sharpe_ratio
from app.research.lab import sma_selection
from app.research.strategies.sma import SMAStrategy


def _evaluator():
    assert hasattr(sma_selection, "evaluate_sma_train_window"), "missing SMA window evaluator"
    return sma_selection.evaluate_sma_train_window


def _frame(n=650):
    t = np.arange(n)
    return pd.DataFrame({"close": 100 * np.exp(0.0001 * t + 0.02 * np.sin(t / 9))})


def _alternating():
    frame = _frame()
    frame.iloc[200:, 0] = frame.iloc[199, 0] * np.exp(0.3 * (np.arange(450) % 2))
    return frame


def _evaluate(frame, train_end=58, test_end=116, **overrides):
    args = {
        "budget": 200,
        "n_per_param": 3,
        "refine": True,
        "refine_span": 0.25,
        "cost_rate": 0.001,
    }
    args.update(overrides)
    return _evaluator()(frame, train_end=train_end, test_end=test_end, **args)


@pytest.mark.parametrize("train_end,test_end", [(1, 2), (3, 5), (58, 116), (600, 630)])
def test_sma_window_matches_independent_native_continuation(train_end, test_end, monkeypatch):
    frame = _alternating()
    prefix = frame.iloc[:test_end]
    selection = sma_selection.select_sma_on_train(
        prefix.iloc[:train_end],
        budget=200,
        n_per_param=3,
        refine=True,
        refine_span=0.25,
        cost_rate=0.001,
    )
    selected = selection.selected
    expected = BacktestEngine(cost_rate=0.001).run_strategy(
        prefix, SMAStrategy(fast=selected.fast, slow=selected.slow)
    )
    net = expected.returns.iloc[train_end:]
    hold = prefix.close.pct_change().fillna(0.0).iloc[train_end:]
    calls = []
    original = BacktestEngine.run_strategy

    def record(self, data, strategy):
        calls.append((len(data), self.cost_rate))
        return original(self, data, strategy)

    monkeypatch.setattr(BacktestEngine, "run_strategy", record)
    result = _evaluate(frame, np.int64(train_end), np.uint64(test_end))
    assert result.method == "nested-sma-native-metrics-continuation-v1"
    assert result.selection == selection
    assert result.train_end == result.n_train == train_end
    assert result.test_end == test_end and result.n_test == test_end - train_end
    assert type(result.train_end) is type(result.test_end) is int
    assert result.test_net_returns == tuple(net)
    assert result.test_gross_hold_returns == tuple(hold)
    assert result.oos_sharpe == sharpe_ratio(net)
    assert result.oos_hold_sharpe == sharpe_ratio(hold)
    assert result.n_hypotheses == selection.n_hypotheses
    assert result.n_engine_calls == len(calls) == selection.n_engine_calls + 1
    assert calls == [(train_end, 0.001)] * selection.n_engine_calls + [(test_end, 0.001)]
    if train_end == 600:
        assert selection.evaluated_refinement_count == 9
    if train_end == 1:
        assert result.test_net_returns == (-0.001,)  # first internal entry turnover
        assert result.oos_sharpe == result.oos_hold_sharpe == 0.0
    if train_end == 3:
        assert result.test_net_returns[0] == frame.close.iloc[3] / frame.close.iloc[2] - 1
        assert result.test_gross_hold_returns[0] == result.test_net_returns[0]


@given(st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False))
@settings(max_examples=10, deadline=None)
def test_sma_window_test_prices_never_change_selection(slope):
    a = _frame()
    b = a.copy()
    b.iloc[58:116, 0] = b.iloc[57, 0] * np.exp(slope * np.arange(1, 59))
    assert _evaluate(a).selection == _evaluate(b).selection


@given(st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False))
@settings(max_examples=10, deadline=None)
def test_sma_window_post_test_prices_never_change_complete_result(slope):
    a = _frame()
    b = a.copy()
    b.iloc[116:, 0] = b.iloc[115, 0] * np.exp(slope * np.arange(len(b) - 116))
    assert _evaluate(a) == _evaluate(b)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, 0.0, -1.0])
def test_sma_window_invalid_post_test_prices_and_calendar_are_ignored(value):
    a = _frame()
    b = a.copy()
    b.iloc[116:, 0] = value
    b.index = list(range(116)) + [0] * (len(b) - 116)
    assert _evaluate(a) == _evaluate(b)


def test_sma_window_changed_test_realization_keeps_trace():
    a = _frame()
    b = a.copy()
    b.iloc[58:116, 0] = b.iloc[57, 0] * np.exp(0.02 * (np.arange(58) % 2))
    x, y = _evaluate(a), _evaluate(b)
    assert x.selection == y.selection
    assert x.test_net_returns != y.test_net_returns
    assert x.oos_sharpe != y.oos_sharpe


@pytest.mark.parametrize(
    "train_end,test_end",
    [
        (True, 116),
        (58, True),
        (58.0, 116),
        (58, 116.0),
        (0, 116),
        (-1, 116),
        (58, 58),
        (59, 58),
        (58, 651),
        (2**64 - 1, 116),
    ],
)
def test_sma_window_invalid_geometry_refuses_before_engine(train_end, test_end, monkeypatch):
    calls = []
    monkeypatch.setattr(BacktestEngine, "run_strategy", lambda *args: calls.append(args))
    with pytest.raises(ValueError):
        _evaluate(_frame(), train_end, test_end)
    assert calls == []


@pytest.mark.parametrize(
    "kind",
    [
        "nan",
        "inf",
        "zero",
        "negative",
        "duplicate",
        "reverse",
        "columns",
        "float32",
        "empty",
        "missing",
    ],
)
def test_sma_window_invalid_used_prefix_refuses_before_selection(kind, monkeypatch):
    frame = _frame()
    if kind in {"nan", "inf", "zero", "negative"}:
        frame.iloc[115, 0] = {"nan": np.nan, "inf": np.inf, "zero": 0.0, "negative": -1.0}[kind]
    elif kind == "duplicate":
        frame.index = [*range(115), 114, *range(116, len(frame))]
    elif kind == "reverse":
        calendar = list(range(len(frame)))
        calendar[114], calendar[115] = calendar[115], calendar[114]
        frame.index = calendar
    elif kind == "columns":
        frame = pd.concat([frame, frame], axis=1)
    elif kind == "float32":
        frame["close"] = frame.close.astype("float32")
    elif kind == "empty":
        frame = frame.iloc[:0]
    else:
        frame = frame.rename(columns={"close": "other"})
    calls = []
    monkeypatch.setattr(sma_selection, "select_sma_on_train", lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError):
        _evaluate(frame)
    assert calls == []


@pytest.mark.parametrize("stage", ["selection", "continuation", "score", "short", "nan"])
def test_sma_window_failures_abort_without_partial_result(stage, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("unmeasurable window")

    if stage == "selection":
        monkeypatch.setattr(sma_selection, "select_sma_on_train", fail)
    elif stage == "score":
        _evaluator()
        monkeypatch.setattr(sma_selection, "sharpe_ratio", fail)
    else:
        original = BacktestEngine.run_strategy

        def changed(self, data, strategy):
            if len(data) == 116:
                if stage == "continuation":
                    fail()
                result = original(self, data, strategy)
                returns = result.returns.iloc[:58] if stage == "short" else result.returns.copy()
                if stage == "nan":
                    returns.iloc[-1] = np.nan
                return replace(result, returns=returns)
            return original(self, data, strategy)

        monkeypatch.setattr(BacktestEngine, "run_strategy", changed)
    with pytest.raises(ValueError):
        _evaluate(_frame())


def test_sma_window_trace_is_frozen_detached_and_flat_safe():
    frame = _frame()
    frame["close"] = 100.0
    original = frame.copy(deep=True)
    result = _evaluate(frame, refine=False, budget=2, cost_rate=0.002)
    pd.testing.assert_frame_equal(frame, original)
    snapshot = (result.test_net_returns, result.test_gross_hold_returns)
    frame.iloc[:, 0] = 1.0
    assert (result.test_net_returns, result.test_gross_hold_returns) == snapshot
    assert result.oos_sharpe == result.oos_hold_sharpe == 0.0
    assert result.selection.selected_index == 0
    assert all(type(v) is float for seq in snapshot for v in seq)
    with pytest.raises(FrozenInstanceError):
        result.test_end = 999
    with pytest.raises(TypeError):
        result.test_net_returns[0] = 1.0
