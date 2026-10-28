"""Unused expanding SMA research composition, not production WF (ADR-394)."""

from dataclasses import FrozenInstanceError, replace
from importlib import import_module
from importlib.util import find_spec
from math import fsum, inf, nextafter

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.backtesting.engine import BacktestEngine
from app.research.lab.sma_selection import evaluate_sma_train_window
from app.validation.walk_forward import walk_forward_splits


def _module():
    name = "app.research.lab.sma_walk_forward"
    assert find_spec(name) is not None, "missing expanding SMA evaluator"
    return import_module(name)


def _frame(n=348):
    t = np.arange(n)
    return pd.DataFrame({"close": 100 * np.exp(0.0001 * t + 0.02 * np.sin(t / 9))})


def _settings(**overrides):
    values = {
        "budget": 200,
        "n_per_param": 3,
        "refine": True,
        "refine_span": 0.25,
        "cost_rate": 0.001,
    }
    values.update(overrides)
    return values


def _evaluate(frame, n_splits=5, min_train=None, **overrides):
    return _module().evaluate_sma_expanding_windows(
        frame, n_splits=n_splits, min_train=min_train, **_settings(**overrides)
    )


@pytest.mark.parametrize(
    "n,n_splits,min_train", [(2, 1, None), (348, 5, None), (650, 2, 58), (650, 1, 600)]
)
def test_sma_expanding_matches_direct_windows_and_actual_calls(n, n_splits, min_train, monkeypatch):
    frame = _frame(n)
    if n == 650:
        frame.iloc[200:, 0] = frame.iloc[199, 0] * np.exp(0.3 * (np.arange(450) % 2))
    geometry = walk_forward_splits(n, n_splits, min_train)
    expected = tuple(
        evaluate_sma_train_window(
            frame, train_end=len(train), test_end=int(test[-1]) + 1, **_settings()
        )
        for train, test in geometry
    )
    calls = []
    original = BacktestEngine.run_strategy

    def record(self, data, strategy):
        calls.append(len(data))
        return original(self, data, strategy)

    monkeypatch.setattr(BacktestEngine, "run_strategy", record)
    result = _evaluate(frame, np.uint64(n_splits), min_train)
    assert result.method == "nested-sma-native-metrics-expanding-v1"
    assert result.n_obs == n and result.n_splits == n_splits
    assert result.windows == expected
    assert isinstance(result.windows, tuple)
    assert result.mean_oos_sharpe == fsum(w.oos_sharpe / n_splits for w in expected)
    assert result.mean_oos_hold_sharpe == fsum(w.oos_hold_sharpe / n_splits for w in expected)
    assert result.n_hypotheses == sum(w.n_hypotheses for w in expected)
    assert result.n_engine_calls == len(calls) == result.n_hypotheses + n_splits
    expected_calls = []
    for w in expected:
        expected_calls.extend([w.train_end] * w.n_hypotheses + [w.test_end])
    assert calls == expected_calls
    assert result.windows[-1].test_end == n
    if min_train == 600:
        assert result.windows[0].selection.evaluated_refinement_count == 9
    if n == 2:
        assert result.mean_oos_sharpe == result.mean_oos_hold_sharpe == 0.0


@given(st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False))
@settings(max_examples=10, deadline=None)
def test_sma_expanding_early_window_ignores_later_prices_and_means_are_bounded(slope):
    a = _frame()
    b = a.copy()
    b.iloc[116:, 0] = b.iloc[115, 0] * np.exp(slope * np.arange(len(b) - 116))
    x, y = _evaluate(a), _evaluate(b)
    assert x.windows[0] == y.windows[0]
    assert x.windows[0].train_end == 58 and x.windows[0].test_end == 116
    for result in (x, y):
        for attribute, mean in (
            ("oos_sharpe", result.mean_oos_sharpe),
            ("oos_hold_sharpe", result.mean_oos_hold_sharpe),
        ):
            values = [getattr(w, attribute) for w in result.windows]
            assert nextafter(min(values), -inf) <= mean <= nextafter(max(values), inf)


def test_sma_expanding_budget_is_per_window_and_hypotheses_are_not_deduplicated():
    result = _evaluate(_frame(), budget=4)
    assert result.n_hypotheses > 4
    assert all(w.n_hypotheses <= 4 for w in result.windows)
    parameters = [(c.fast, c.slow) for w in result.windows for c in w.selection.candidates]
    assert len(parameters) > len(set(parameters))
    assert result.n_hypotheses == len(parameters)


@pytest.mark.parametrize(
    "n_splits,min_train",
    [
        (True, None),
        (0, None),
        (-1, None),
        (1.5, None),
        (349, None),
        (np.uint64(2**64 - 1), None),
        (5, True),
        (5, 0),
        (5, -1),
        (5, 1.5),
        (5, 348),
    ],
)
def test_sma_expanding_invalid_geometry_refuses_before_window(n_splits, min_train, monkeypatch):
    module = _module()
    calls = []
    monkeypatch.setattr(module, "evaluate_sma_train_window", lambda *a, **k: calls.append(k))
    with pytest.raises(ValueError):
        _evaluate(_frame(), n_splits, min_train)
    assert calls == []


def test_sma_expanding_later_invalid_prefix_aborts_after_earlier_compute(monkeypatch):
    frame = _frame()
    frame.iloc[-1, 0] = np.nan
    calls = []
    original = BacktestEngine.run_strategy

    def record(self, data, strategy):
        calls.append(len(data))
        return original(self, data, strategy)

    monkeypatch.setattr(BacktestEngine, "run_strategy", record)
    with pytest.raises(ValueError, match="positive and finite"):
        _evaluate(frame)
    assert calls and max(calls) == 290


def test_sma_expanding_window_failure_aborts_without_dropping_or_later_calls(monkeypatch):
    module = _module()
    original = module.evaluate_sma_train_window
    calls = []

    def fail_third(*args, **kwargs):
        calls.append(kwargs["train_end"])
        if len(calls) == 3:
            raise ValueError("failed window")
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "evaluate_sma_train_window", fail_third)
    with pytest.raises(ValueError, match="failed window"):
        _evaluate(_frame())
    assert calls == [58, 116, 174]


@pytest.mark.parametrize("attribute", ["oos_sharpe", "oos_hold_sharpe"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_sma_expanding_nonfinite_mean_refuses(attribute, value, monkeypatch):
    module = _module()
    original = module.evaluate_sma_train_window

    def invalid_score(*args, **kwargs):
        return replace(original(*args, **kwargs), **{attribute: value})

    monkeypatch.setattr(module, "evaluate_sma_train_window", invalid_score)
    with pytest.raises(ValueError, match="finite"):
        _evaluate(_frame(), n_splits=1)


def test_sma_expanding_evidence_is_frozen_and_detached():
    frame = _frame()
    before = frame.copy(deep=True)
    result = _evaluate(frame)
    pd.testing.assert_frame_equal(frame, before)
    first_return = result.windows[0].test_net_returns[0]
    frame.iloc[:, 0] = 1.0
    assert result.windows[0].test_net_returns[0] == first_return
    with pytest.raises(FrozenInstanceError):
        result.mean_oos_sharpe = 0.0
    with pytest.raises(TypeError):
        result.windows[0] = result.windows[1]
