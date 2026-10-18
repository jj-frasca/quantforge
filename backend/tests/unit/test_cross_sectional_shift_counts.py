"""Causal shift counts at direct factors and public forward reconstruction (ADR-314)."""

from collections.abc import Callable
from fractions import Fraction
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional.engine import portfolio_returns
from app.research.cross_sectional.forward import CrossSectionalPosition, score_forward
from app.research.cross_sectional.registry import default_strategies
from app.research.cross_sectional.strategies import (
    alpha19_signal,
    momentum_signal,
    residual_momentum_signal,
    reversal_signal,
)

CASES = [
    (momentum_signal, {"lookback": 2, "skip": 0}, "lookback"),
    (momentum_signal, {"lookback": 2, "skip": 0}, "skip"),
    (reversal_signal, {"lookback": 2}, "lookback"),
    (residual_momentum_signal, {"lookback": 2, "skip": 0, "mean_window": 2}, "skip"),
    (alpha19_signal, {"change_lag": 2, "sum_window": 2}, "change_lag"),
]


def _panel(n: int = 40) -> pd.DataFrame:
    t = np.arange(n, dtype=float)
    return pd.DataFrame(
        {
            sym: 100 + (j + 1) * np.sin(t / (j + 2)) + 0.1 * j * t
            for j, sym in enumerate(("D", "B", "A", "C"))
        },
        index=pd.date_range("2020-01-01", periods=n, freq="B", tz="UTC"),
    )


@pytest.mark.parametrize("fn,params,field", CASES)
@pytest.mark.parametrize(
    "bad", [-1, np.int64(-2), True, np.bool_(False), 1.0, Fraction(1, 1), "2", np.array(2)]
)
def test_shift_count_invalid_original_refuses_before_panel_access(
    fn: Callable[..., pd.DataFrame], params: dict[str, int], field: str, bad: object
) -> None:
    kwargs: dict[str, Any] = {**params, field: bad}
    with pytest.raises(ValueError, match=f"{field} must be a nonnegative nonboolean integer"):
        fn(None, **kwargs)


@pytest.mark.parametrize("fn,params,field", CASES)
@pytest.mark.parametrize("bad", [-1, -3])
def test_shift_count_negative_refuses_empty_panel(
    fn: Callable[..., pd.DataFrame], params: dict[str, int], field: str, bad: int
) -> None:
    with pytest.raises(ValueError, match=field):
        fn(_panel(0), **{**params, field: bad})


@pytest.mark.parametrize("fn,params,field", CASES)
@pytest.mark.parametrize("count", [0, 1, np.int64(2), np.uint64(3)])
def test_shift_count_valid_retains_original_formula(
    fn: Callable[..., pd.DataFrame], params: dict[str, int], field: str, count: int
) -> None:
    prices = _panel()
    kwargs = {**params, field: count}
    actual = fn(prices, **kwargs)
    rets = prices.pct_change()
    if fn is momentum_signal:
        expected = (
            prices.shift(int(kwargs["skip"]))
            / prices.shift(int(kwargs["skip"]) + int(kwargs["lookback"]))
            - 1.0
        )
    elif fn is reversal_signal:
        expected = -(prices / prices.shift(int(kwargs["lookback"])) - 1.0)
    elif fn is residual_momentum_signal:
        residual = rets - rets.rolling(kwargs["mean_window"]).mean()
        expected = residual.rolling(kwargs["lookback"]).sum().shift(int(kwargs["skip"]))
    else:
        change = prices - prices.shift(int(kwargs["change_lag"]))
        expected = -np.sign(change) * (1.0 + (1.0 + rets.rolling(2).sum()).rank(axis=1, pct=True))
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)


def test_momentum_shift_counts_normalize_before_fixed_width_addition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    original = pd.DataFrame.shift

    def checked(self: pd.DataFrame, periods: int = 1, *args: Any, **kwargs: Any) -> pd.DataFrame:
        calls.append(periods)
        # Preserve the operation without allocating an unrepresentably large pandas shift.
        return original(self, min(int(periods), len(self) + 1), *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "shift", checked)
    largest = np.int64(np.iinfo(np.int64).max)
    momentum_signal(_panel(), lookback=largest, skip=largest)
    assert calls == [int(largest), 2 * int(largest)]
    assert all(type(value) is int for value in calls)


@pytest.mark.parametrize(
    "name,params",
    [
        ("xs_momentum", {"lookback": -2, "skip": 0}),
        ("xs_momentum", {"lookback": 2, "skip": -3}),
        ("xs_reversal", {"lookback": -2}),
        ("xs_short_term_reversal_1m", {"lookback": -2}),
        ("xs_residual_momentum", {"lookback": 2, "skip": -2, "mean_window": 2}),
        ("xs_alpha19", {"change_lag": -2}),
    ],
)
def test_forward_reconstructed_negative_shift_refuses(name: str, params: dict[str, int]) -> None:
    prices = _panel()
    position = CrossSectionalPosition(
        strategy_name=name,
        parameters={**params, "quantile": 0.25},
        universe_symbols=tuple(prices.columns),
        cost_rate=0.001,
        frozen_at=prices.index[2].to_pydatetime(),
    )
    with pytest.raises(ValueError, match="nonnegative nonboolean integer"):
        score_forward(position, prices)


@given(lookback=st.integers(0, 12), skip=st.integers(0, 12), cut=st.integers(15, 38))
@settings(max_examples=30, deadline=None)
def test_shift_factors_causal_prefix_and_future_perturbation(
    lookback: int, skip: int, cut: int
) -> None:
    prices = _panel()
    modified = prices.copy(deep=True)
    modified.iloc[cut:] *= np.array([0.8, 1.2, 0.85, 1.15])
    cases = [
        (momentum_signal, {"lookback": lookback, "skip": skip}),
        (reversal_signal, {"lookback": lookback}),
        (residual_momentum_signal, {"lookback": 2, "skip": skip, "mean_window": 2}),
        (alpha19_signal, {"change_lag": lookback, "sum_window": 2}),
    ]
    for fn, kwargs in cases:
        full = fn(prices, **kwargs)
        realized = portfolio_returns(full, prices, quantile=0.25, cost_rate=0.001)
        for variant in (prices.iloc[:cut], modified):
            signals = fn(variant, **kwargs)
            pd.testing.assert_frame_equal(full.iloc[:cut], signals.iloc[:cut], check_exact=True)
            pd.testing.assert_series_equal(
                realized.iloc[:cut],
                portfolio_returns(signals, variant, quantile=0.25, cost_rate=0.001).iloc[:cut],
                check_exact=True,
            )


def test_shipped_registry_grids_preserve_prefixes() -> None:
    prices = _panel(360)
    registry = default_strategies()
    for spec in registry.values():
        for params in spec.param_grid:
            fn = spec.build(dict(params))
            pd.testing.assert_frame_equal(
                fn(prices).iloc[:330], fn(prices.iloc[:330]), check_exact=True
            )
