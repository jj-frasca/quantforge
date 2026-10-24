"""ADR-361: no turnover does not erase observed forward return evidence."""

from datetime import UTC, datetime
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.data.models import DataQualityReport
from app.research.backtesting.engine import BacktestEngine
from app.research.dataset import ResearchDataset
from app.research.lab.paper import (
    ExitPolicy,
    PaperPosition,
    _forward_trades,
    evaluate_forward,
    evaluate_lifecycle,
    lifecycle_from_returns,
)
from app.research.strategies.momentum import MomentumStrategy


def _frame(returns: list[float]) -> pd.DataFrame:
    closes = 100.0 * np.cumprod(1.0 + np.array(returns))
    return pd.DataFrame(
        {"close": closes}, index=pd.date_range("2020-01-01", periods=len(closes), tz="UTC")
    )


def _position(frame: pd.DataFrame) -> PaperPosition:
    return PaperPosition(
        symbol="AAA",
        strategy_name="momentum",
        parameters={"lookback": 60, "skip": 5},
        frozen_at=frame.index[299].to_pydatetime(),
    )


def _dataset(frame: pd.DataFrame) -> ResearchDataset:
    return ResearchDataset(
        frame=frame,
        quality_report=DataQualityReport(
            symbol="AAA", source="yfinance", checked_at=datetime(2024, 1, 1, tzinfo=UTC)
        ),
        source="yfinance",
        adapter_version="synthetic-adr361",
        start=frame.index.min().to_pydatetime(),
        end=(frame.index.max() + pd.Timedelta(days=1)).to_pydatetime(),
        git_commit_hash="a" * 40,
    )


def test_inherited_default_momentum_exposure_faces_existing_risk_limit() -> None:
    frame = _frame([0.01] * 300 + [-0.35] + [0.009, 0.011] * 25)
    position = _position(frame)
    result = BacktestEngine().run_strategy(frame, MomentumStrategy())
    mask = frame.index > position.frozen_at
    assert result.position[mask].eq(1.0).all()
    assert _forward_trades(result.position, mask) == 0
    assert result.returns[mask].iloc[0] == pytest.approx(-0.35)

    decision = evaluate_lifecycle(position, frame, ExitPolicy())
    assert decision.action == "exit"
    assert decision.forward_drawdown == pytest.approx(0.35)
    assert any("risk limit" in reason for reason in decision.reasons)
    assert not any("measurable" in reason for reason in decision.reasons)


def test_inherited_short_forward_score_keeps_zero_count_and_measured_comparison() -> None:
    frame = _frame([-0.01] * 300 + [-0.009, -0.011] * 25)
    position = _position(frame)
    result = BacktestEngine().run_strategy(frame, MomentumStrategy())
    mask = frame.index > position.frozen_at
    assert result.position[mask].eq(-1.0).all()
    assert _forward_trades(result.position, mask) == 0

    score = evaluate_forward(position, _dataset(frame))
    assert score.forward_trades == 0
    assert score.forward_bars == 50
    assert score.forward_sharpe > score.buy_and_hold_sharpe
    assert score.beats_buy_and_hold is True
    assert len(score.forward_equity) == 50


def test_inactive_public_forward_score_still_does_not_beat_a_declining_benchmark() -> None:
    frame = _frame([-0.01] * 350)
    position = _position(frame).model_copy(update={"parameters": {"lookback": 400, "skip": 5}})
    score = evaluate_forward(position, _dataset(frame))
    assert score.forward_trades == 0
    assert score.forward_return == 0
    assert score.forward_sharpe > score.buy_and_hold_sharpe
    assert score.beats_buy_and_hold is False


def test_zero_turnover_keeps_strict_default_drawdown_comparison() -> None:
    returns = pd.Series([-0.25] + [0.009, 0.011] * 25)
    result = lifecycle_from_returns(returns, returns, ExitPolicy(), 0)
    assert result.forward_drawdown == 0.25
    assert not any("risk limit" in reason for reason in result.reasons)


@pytest.mark.parametrize("bars", [21, 51, 126, 127])
@pytest.mark.parametrize("dtype", ["float32", "float64", "Float32", "Float64"])
def test_zero_turnover_nonzero_returns_keep_measured_healthy_decision(
    bars: int, dtype: str
) -> None:
    returns = pd.Series(([0.009, 0.011] * bars)[:bars], dtype=dtype)
    before = returns.copy(deep=True)
    benchmark = pd.Series(0.0, index=returns.index)
    decision = lifecycle_from_returns(returns, benchmark, ExitPolicy(), 0)
    assert decision.action == "hold"
    assert decision.reasons == []
    assert decision.rolling_sharpe > 0
    assert decision.forward_drawdown == 0
    pd.testing.assert_series_equal(returns, before)


@pytest.mark.parametrize("bars", [0, 20, 21, 125, 126, 127])
@pytest.mark.parametrize("zero", [0.0, -0.0])
def test_zero_turnover_all_zero_returns_keep_grace_and_no_evidence_timeout(
    bars: int, zero: float
) -> None:
    returns = pd.Series([zero] * bars, dtype="float64")
    decision = lifecycle_from_returns(returns, returns, ExitPolicy(), 0)
    assert decision.action == ("exit" if bars >= 126 else "hold")
    assert decision.forward_drawdown == 0
    assert decision.rolling_sharpe == 0
    expected = "grace" if bars < 21 else "never traded" if bars >= 126 else "not yet measurable"
    assert expected in decision.reasons[0]


def test_nonzero_returns_with_zero_turnover_still_respect_grace() -> None:
    returns = pd.Series([-0.5, 0.01])
    decision = lifecycle_from_returns(returns, returns, ExitPolicy(), 0)
    assert decision.action == "hold"
    assert decision.forward_drawdown == 0
    assert decision.reasons == ["grace period (insufficient forward data)"]


@pytest.mark.parametrize("kind", ["ordinary", "subnormal", "wide"])
def test_native_nonzero_evidence_is_not_replaced_by_a_zero_tolerance(kind: str) -> None:
    if kind == "ordinary":
        returns = pd.Series([1e-30] * 21)
    elif kind == "subnormal":
        returns = pd.Series([np.nextafter(0.0, 1.0)] * 21)
    else:
        if np.finfo(np.longdouble).minexp >= np.finfo(float).minexp:
            returns = pd.Series(np.full(21, np.longdouble("1e-30")))
        else:
            returns = pd.Series(np.full(21, np.ldexp(np.longdouble(1), -1075)))
    benchmark = pd.Series(0.0, index=returns.index)
    assert returns.ne(0).all()
    zero_count = lifecycle_from_returns(returns, benchmark, ExitPolicy(), 0)
    measured = lifecycle_from_returns(returns, benchmark, ExitPolicy(), 1)
    assert zero_count == measured


def test_offsetting_returns_are_observed_even_when_their_sum_is_zero() -> None:
    returns = pd.Series([0.125, -0.125] * 11)
    assert returns.sum() == 0
    result = lifecycle_from_returns(returns, returns * 0, ExitPolicy(), 0)
    assert result.forward_drawdown > 0
    assert not any("measurable" in reason for reason in result.reasons)


@given(ticks=st.lists(st.integers(-32, 32), min_size=1, max_size=30).filter(any))
@settings(max_examples=60, deadline=None)
def test_zero_turnover_measured_drawdown_matches_exact_wealth_property(ticks: list[int]) -> None:
    returns = pd.Series([tick / 64 for tick in ticks])
    wealth = peak = Fraction(1)
    worst = Fraction(0)
    for tick in ticks:
        wealth *= 1 + Fraction(tick, 64)
        peak = max(peak, wealth)
        worst = max(worst, 1 - wealth / peak)
    policy = ExitPolicy(min_forward_bars_before_exit=0)
    result = lifecycle_from_returns(returns, returns * 0, policy, 0)
    assert result.forward_drawdown == pytest.approx(float(worst), abs=1e-12)
    assert not any("measurable" in reason for reason in result.reasons)
