"""ADR-356: every scored forward loss participates in lifecycle peak history."""

from fractions import Fraction
from typing import Literal

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional.forward import (
    CrossSectionalExitPolicy,
    CrossSectionalLifecycleDecision,
    lifecycle_from_forward_returns,
)
from app.research.lab.paper import ExitPolicy, LifecycleDecision, lifecycle_from_returns

Family = Literal["single", "panel"]


def _decision(
    family: Family,
    returns: pd.Series,
    *,
    grace: int = 21,
    limit: float | None = None,
    trades: int = 1,
) -> LifecycleDecision | CrossSectionalLifecycleDecision:
    benchmark = pd.Series(0.0, index=returns.index)
    if family == "single":
        policy = ExitPolicy(min_forward_bars_before_exit=grace)
        if limit is not None:
            policy = ExitPolicy(min_forward_bars_before_exit=grace, max_forward_drawdown=limit)
        return lifecycle_from_returns(returns, benchmark, policy, trades)
    panel_policy = CrossSectionalExitPolicy(min_forward_bars_before_exit=grace)
    if limit is not None:
        panel_policy = CrossSectionalExitPolicy(
            min_forward_bars_before_exit=grace, max_forward_drawdown=limit
        )
    return lifecycle_from_forward_returns(returns, benchmark, panel_policy)


@pytest.mark.parametrize("family", ["single", "panel"])
def test_lifecycle_initial_loss_recovery_breaches_default_risk_limit(family: Family) -> None:
    returns = pd.Series([-0.35] + [0.009, 0.011] * 50)
    result = _decision(family, returns)
    assert result.forward_drawdown == pytest.approx(0.35)
    assert result.rolling_sharpe > 100.0
    assert result.action == ("exit" if family == "single" else "retire")
    assert len(result.reasons) == 1
    assert "drawdown 35.0% >" in result.reasons[0]


@pytest.mark.parametrize("family", ["single", "panel"])
@pytest.mark.parametrize("dtype", ["float32", "float64", "Float32", "Float64"])
def test_lifecycle_single_scored_loss_keeps_pre_return_peak(family: Family, dtype: str) -> None:
    result = _decision(family, pd.Series([-0.5], dtype=dtype), grace=0)
    assert result.forward_drawdown == 0.5
    assert any("drawdown 50.0% >" in reason for reason in result.reasons)


@pytest.mark.parametrize("family", ["single", "panel"])
def test_lifecycle_exact_risk_limit_does_not_breach(family: Family) -> None:
    result = _decision(family, pd.Series([-0.5, 0.01, 0.02]), grace=0, limit=0.5)
    assert result.forward_drawdown == 0.5
    assert not any("drawdown" in reason for reason in result.reasons)


@pytest.mark.parametrize("family", ["single", "panel"])
@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([0.5, -0.25, 0.5], 0.25),
        ([0.0, -0.5, 0.25], 0.5),
        ([0.25, 0.5, 0.125], 0.0),
        ([-0.125, 1.0, -0.5], 0.5),
        ([-0.5, -0.5, 1.0], 0.75),
    ],
)
def test_lifecycle_complete_peak_history_matches_known_wealth(
    family: Family, values: list[float], expected: float
) -> None:
    result = _decision(family, pd.Series(values), grace=0)
    assert result.forward_drawdown == expected


@pytest.mark.parametrize("family", ["single", "panel"])
def test_lifecycle_initial_loss_does_not_bypass_grace(family: Family) -> None:
    result = _decision(family, pd.Series([-0.5, 0.01]))
    assert result.action == "hold"
    assert result.forward_drawdown == 0.0
    assert result.reasons == ["grace period (insufficient forward data)"]


@pytest.mark.parametrize("bars", [21, 126])
def test_single_initial_loss_does_not_override_no_trade_branch(bars: int) -> None:
    result = _decision("single", pd.Series([-0.5] + [0.01] * (bars - 1)), trades=0)
    assert result.forward_drawdown == 0.0
    assert result.action == ("hold" if bars < 126 else "exit")
    assert not any("drawdown" in reason for reason in result.reasons)


@pytest.mark.parametrize("family", ["single", "panel"])
def test_lifecycle_zero_grace_empty_retains_zero_risk(family: Family) -> None:
    result = _decision(family, pd.Series(dtype="float64"), grace=0, trades=0)
    assert result.forward_drawdown == 0.0


@pytest.mark.parametrize("family", ["single", "panel"])
@pytest.mark.parametrize("dtype", ["float32", "float64", "Float32", "Float64"])
def test_lifecycle_baseline_keeps_native_dtype_and_original_series(
    family: Family, dtype: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.research.backtesting.metrics import max_drawdown

    returns = pd.Series(
        [-0.5, 0.25, 0.125],
        index=pd.date_range("2024-01-01", periods=3, tz="UTC"),
        dtype=dtype,
    )
    original = returns.copy(deep=True)
    native_equity = (1.0 + returns).cumprod()
    observed: list[pd.Series] = []

    def capture(equity: pd.Series) -> float:
        observed.append(equity.copy(deep=True))
        return max_drawdown(equity)

    module = (
        "app.research.lab.paper" if family == "single" else "app.research.cross_sectional.forward"
    )
    monkeypatch.setattr(f"{module}.max_drawdown", capture)
    _decision(family, returns, grace=0)
    assert len(observed) == 1
    assert observed[0].dtype == native_equity.dtype
    assert observed[0].iloc[0] == 1.0
    np.testing.assert_array_equal(observed[0].iloc[1:].to_numpy(), native_equity.to_numpy())
    pd.testing.assert_series_equal(returns, original)


@pytest.mark.parametrize("family", ["single", "panel"])
@given(ticks=st.lists(st.integers(-63, 63), min_size=1, max_size=30))
@settings(max_examples=60, deadline=None)
def test_lifecycle_drawdown_matches_exact_complete_wealth_property(
    family: Family, ticks: list[int]
) -> None:
    wealth = peak = Fraction(1)
    worst = Fraction(0)
    for tick in ticks:
        wealth *= 1 + Fraction(tick, 128)
        peak = max(peak, wealth)
        worst = max(worst, 1 - wealth / peak)
    returns = pd.Series([tick / 128 for tick in ticks])
    result = _decision(family, returns, grace=0)
    assert 0.0 <= result.forward_drawdown <= 1.0
    assert result.forward_drawdown == pytest.approx(float(worst), rel=3e-14, abs=3e-15)
