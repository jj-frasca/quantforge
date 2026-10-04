"""Lifecycle verdicts require valid policy and paired evidence before holds (ADR-168)."""

from datetime import UTC, datetime

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.cross_sectional.forward import (
    CrossSectionalExitPolicy,
    CrossSectionalPosition,
    evaluate_cross_sectional_lifecycle,
    lifecycle_from_forward_returns,
)
from app.research.lab.paper import (
    ExitPolicy,
    PaperPosition,
    evaluate_lifecycle,
    lifecycle_from_returns,
)

_POLICY_TYPES = [ExitPolicy, CrossSectionalExitPolicy]


def _returns(n: int = 3) -> pd.Series:
    return pd.Series([0.001] * n, index=pd.date_range("2026-01-01", periods=n, freq="B", tz="UTC"))


def _decide(panel: bool, forward: pd.Series, benchmark: pd.Series, policy, trades=1):
    if panel:
        return lifecycle_from_forward_returns(forward, benchmark, policy)
    return lifecycle_from_returns(forward, benchmark, policy, trades)


@pytest.mark.parametrize("policy_type", _POLICY_TYPES)
@pytest.mark.parametrize(
    "updates",
    [
        {"min_forward_bars_before_exit": -1},
        {"rolling_window_bars": 0},
        {"rolling_window_bars": -1},
        {"min_rolling_sharpe": float("nan")},
        {"max_forward_drawdown": float("inf")},
        {"max_forward_drawdown": -0.1},
    ],
)
def test_lifecycle_invalid_policy_rejects_construction_and_unchecked_copy_at_grace(
    policy_type: type, updates: dict
) -> None:
    with pytest.raises(ValueError):
        policy_type.model_validate(updates)
    unchecked = policy_type().model_copy(update=updates)
    with pytest.raises(ValueError):
        _decide(policy_type is CrossSectionalExitPolicy, _returns(), _returns(), unchecked)


@pytest.mark.parametrize("policy_type", _POLICY_TYPES)
def test_lifecycle_unchecked_policy_rejected_before_no_forward_data_hold(policy_type: type) -> None:
    policy = policy_type().model_copy(update={"rolling_window_bars": 0})
    frame = pd.DataFrame(
        {"A": [100.0]} if policy_type is CrossSectionalExitPolicy else {"close": [100.0]},
        index=pd.DatetimeIndex([datetime(2025, 1, 1, tzinfo=UTC)]),
    )
    with pytest.raises(ValueError):
        if policy_type is ExitPolicy:
            position = PaperPosition(
                symbol="A",
                strategy_name="sma",
                parameters={"fast": 2, "slow": 3},
                frozen_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
            evaluate_lifecycle(position, frame, policy)
        else:
            position = CrossSectionalPosition(
                strategy_name="xs_momentum",
                parameters={"lookback": 2, "skip": 0, "quantile": 0.2},
                universe_symbols=["A"],
                cost_rate=0.001,
                frozen_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
            evaluate_cross_sectional_lifecycle(position, frame, policy)


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize("side", ["forward", "benchmark"])
@pytest.mark.parametrize(
    "mutation",
    [
        "nan",
        "inf",
        "ruin",
        "below_ruin",
        "length",
        "calendar",
        "duplicate",
        "reverse",
        "object",
        "boolean",
        "complex",
    ],
)
def test_lifecycle_invalid_returns_rejected_even_during_grace(
    panel: bool, side: str, mutation: str
) -> None:
    forward, benchmark = _returns(), _returns()
    target = forward if side == "forward" else benchmark
    if mutation in {"nan", "inf", "ruin", "below_ruin"}:
        target.iloc[0] = {
            "nan": float("nan"),
            "inf": float("inf"),
            "ruin": -1.0,
            "below_ruin": -1.1,
        }[mutation]
    elif mutation == "length":
        target = target.iloc[:-1]
    elif mutation == "calendar":
        target.index = target.index + pd.Timedelta(days=1)
    elif mutation == "duplicate":
        target.index = pd.DatetimeIndex([target.index[0]] * len(target))
    elif mutation == "reverse":
        target = target.iloc[::-1]
    elif mutation == "object":
        target = target.astype(str)
    elif mutation == "boolean":
        target = target.astype(bool)
    else:
        target = target.astype(complex)
    if side == "forward":
        forward = target
    else:
        benchmark = target
    policy = CrossSectionalExitPolicy() if panel else ExitPolicy()
    with pytest.raises(ValueError):
        _decide(panel, forward, benchmark, policy)


@pytest.mark.parametrize("count", [-1, 4, 0.5, True])
def test_single_name_lifecycle_rejects_invalid_trade_count_before_grace(count: object) -> None:
    with pytest.raises(ValueError, match="trade"):
        lifecycle_from_returns(_returns(), _returns(), ExitPolicy(), count)


@pytest.mark.parametrize("count", [0, -1])
def test_single_name_lifecycle_rejects_invalid_no_trade_horizon(count: int) -> None:
    with pytest.raises(ValueError):
        ExitPolicy(max_bars_without_trade=count)


@pytest.mark.parametrize("policy_type", _POLICY_TYPES)
def test_lifecycle_preserves_empty_pairs_and_deliberate_diagnostic_policy(
    policy_type: type,
) -> None:
    policy = policy_type(
        min_forward_bars_before_exit=1,
        rolling_window_bars=1,
        min_rolling_sharpe=-100.0,
        max_forward_drawdown=10.0,
    )
    decision = _decide(policy_type is CrossSectionalExitPolicy, _returns(0), _returns(0), policy, 0)
    assert decision.action == "hold"


@pytest.mark.parametrize("panel", [False, True])
@given(
    values=st.lists(
        st.floats(min_value=-0.99, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=20,
    )
)
def test_lifecycle_valid_finite_paired_returns_preserve_grace(
    panel: bool, values: list[float]
) -> None:
    forward = pd.Series(values, index=pd.RangeIndex(len(values)))
    policy = CrossSectionalExitPolicy() if panel else ExitPolicy()
    assert _decide(panel, forward, forward.copy(), policy, 0).action == "hold"


def test_single_name_invalid_evidence_rejected_before_zero_trade_hold() -> None:
    forward, benchmark = _returns(40), _returns(40)
    benchmark.iloc[0] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        lifecycle_from_returns(forward, benchmark, ExitPolicy(), 0)


def test_lifecycle_default_policy_values_are_unchanged() -> None:
    assert ExitPolicy().model_dump() == {
        "min_forward_bars_before_exit": 21,
        "rolling_window_bars": 63,
        "min_rolling_sharpe": 0.0,
        "max_forward_drawdown": 0.25,
        "require_beat_buy_and_hold_forward": True,
        "max_bars_without_trade": 126,
    }
    assert CrossSectionalExitPolicy().model_dump() == {
        "min_forward_bars_before_exit": 21,
        "rolling_window_bars": 63,
        "min_rolling_sharpe": 0.0,
        "max_forward_drawdown": 0.30,
        "require_beat_benchmark_forward": True,
    }


@pytest.mark.parametrize("panel", [False, True])
@pytest.mark.parametrize("mutation", ["duplicate", "reverse"])
def test_lifecycle_aligned_invalid_calendar_is_rejected(panel: bool, mutation: str) -> None:
    forward = _returns()
    if mutation == "duplicate":
        forward.index = pd.DatetimeIndex([forward.index[0]] * len(forward))
    else:
        forward = forward.iloc[::-1]
    policy = CrossSectionalExitPolicy() if panel else ExitPolicy()
    with pytest.raises(ValueError, match="unique and ascending"):
        _decide(panel, forward, forward.copy(), policy)
