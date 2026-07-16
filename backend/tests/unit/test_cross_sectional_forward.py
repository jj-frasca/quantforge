"""Cross-sectional forward-testing (ADR-025). A cross-sectional graduate is a whole dollar-neutral
long/short portfolio, so it is forward-tested by continuing to compute its engine `portfolio_returns`
on bars AFTER its freeze boundary and benchmarking against the equal-weight long-only universe (the
same benchmark ADR-024 used at the holdout). Everything is pure over injectable panels -- no network,
no look-ahead (weights at t use prices <= t)."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional.forward import (
    CrossSectionalExitPolicy,
    CrossSectionalForwardScore,
    CrossSectionalPosition,
    evaluate_cross_sectional_lifecycle,
    freeze_cross_sectional_graduate,
    lifecycle_from_forward_returns,
    manage_cross_sectional_book,
    score_forward,
)
from app.research.cross_sectional.search import CrossSectionalExperiment
from app.research.lab.experiment import Graduate, Trial
from app.research.lab.gate import GateConfig, GateResult


def _noise_panel(n: int = 800, n_symbols: int = 6, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    prices = 100.0 * np.cumprod(1.0 + rng.normal(0.0002, 0.01, (n, n_symbols)), axis=0)
    idx = pd.date_range("2015-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame(prices, index=idx, columns=[f"S{i}" for i in range(n_symbols)])


def _persistent_momentum_panel(n: int = 800, n_symbols: int = 6, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    drifts = np.linspace(-0.0010, 0.0010, n_symbols)
    steps = rng.normal(0.0, 0.006, (n, n_symbols)) + drifts
    prices = 100.0 * np.cumprod(1.0 + steps, axis=0)
    idx = pd.date_range("2015-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame(prices, index=idx, columns=[f"S{i}" for i in range(n_symbols)])


def _momentum_position(panel: pd.DataFrame, split: int = 400) -> CrossSectionalPosition:
    return CrossSectionalPosition(
        strategy_name="xs_momentum",
        parameters={"lookback": 126, "skip": 0, "quantile": 0.2},
        universe_symbols=list(panel.columns),
        cost_rate=0.001,
        frozen_at=panel.index[split].to_pydatetime(),
    )


def test_score_forward_scores_only_post_freeze_bars_vs_equal_weight_benchmark() -> None:
    panel = _persistent_momentum_panel()
    pos = _momentum_position(panel, split=400)
    score = score_forward(pos, panel)
    assert isinstance(score, CrossSectionalForwardScore)
    # 800 bars, frozen at index 400 -> bars strictly after (401..799) = 399 scored.
    assert score.forward_bars == len(panel) - 401
    assert score.as_of == panel.index.max().to_pydatetime()
    assert score.beats_benchmark == (score.forward_sharpe > score.benchmark_sharpe)
    # a persistent long/short spread should beat holding the universe equal-weight, risk-adjusted.
    assert score.beats_benchmark is True
    # the equity curve has one point per forward bar; terminal == 1 + scalar total return.
    assert len(score.forward_equity) == score.forward_bars
    assert score.forward_equity[-1].strategy_equity == pytest.approx(1.0 + score.forward_return)
    assert score.forward_equity[-1].benchmark_equity == pytest.approx(1.0 + score.benchmark_return)


def test_score_forward_returns_zero_bar_score_before_any_forward_data() -> None:
    panel = _noise_panel()
    pos = CrossSectionalPosition(
        strategy_name="xs_momentum",
        parameters={"lookback": 126, "skip": 0, "quantile": 0.2},
        universe_symbols=list(panel.columns),
        cost_rate=0.001,
        frozen_at=panel.index.max().to_pydatetime(),  # nothing strictly after the last bar
    )
    score = score_forward(pos, panel)
    assert score.forward_bars == 0
    assert score.forward_return == 0.0
    assert score.beats_benchmark is False
    assert score.forward_equity == []


def test_score_forward_reconstructs_value_factor_from_stored_scores() -> None:
    panel = _noise_panel()
    scores = {f"S{i}": float(i) / 6.0 for i in range(6)}
    pos = CrossSectionalPosition(
        strategy_name="xs_value",
        parameters={"quantile": 0.2},
        universe_symbols=list(panel.columns),
        cost_rate=0.001,
        frozen_at=panel.index[400].to_pydatetime(),
        value_scores=scores,
    )
    score = score_forward(pos, panel)
    assert score.forward_bars > 0


def test_score_forward_raises_on_unknown_strategy() -> None:
    panel = _noise_panel()
    pos = CrossSectionalPosition(
        strategy_name="bogus",
        parameters={"quantile": 0.2},
        universe_symbols=list(panel.columns),
        cost_rate=0.001,
        frozen_at=panel.index[400].to_pydatetime(),
    )
    with pytest.raises(ValueError, match="unknown cross-sectional strategy"):
        score_forward(pos, panel)


def _returns(values: list[float]) -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=len(values), freq="B", tz="UTC")
    return pd.Series(values, index=idx)


def test_lifecycle_holds_during_the_grace_period() -> None:
    policy = CrossSectionalExitPolicy(min_forward_bars_before_exit=21)
    decision = lifecycle_from_forward_returns(_returns([-0.1] * 5), _returns([0.0] * 5), policy)
    assert decision.action == "hold"
    assert "grace period" in decision.reasons[0]


def test_lifecycle_retires_on_decayed_rolling_sharpe() -> None:
    # Persistent losses -> rolling Sharpe well below the floor -> retire.
    policy = CrossSectionalExitPolicy(min_forward_bars_before_exit=10, rolling_window_bars=30)
    fwd = _returns([-0.01] * 40)
    bench = _returns([0.0005] * 40)
    decision = lifecycle_from_forward_returns(fwd, bench, policy)
    assert decision.action == "retire"
    assert any("rolling Sharpe" in r for r in decision.reasons)


def test_lifecycle_retires_when_it_stops_beating_the_benchmark() -> None:
    # Positive but weak factor vs a stronger equal-weight benchmark -> retire on the benchmark rule.
    policy = CrossSectionalExitPolicy(
        min_forward_bars_before_exit=10, rolling_window_bars=30, min_rolling_sharpe=-100.0
    )
    rng = np.random.default_rng(3)
    fwd = _returns(list(rng.normal(0.0002, 0.01, 40)))
    bench = _returns(list(rng.normal(0.003, 0.005, 40)))  # much stronger, steadier
    decision = lifecycle_from_forward_returns(fwd, bench, policy)
    assert decision.action == "retire"
    assert any("benchmark" in r for r in decision.reasons)


def test_lifecycle_holds_a_healthy_factor() -> None:
    policy = CrossSectionalExitPolicy(min_forward_bars_before_exit=10, rolling_window_bars=30)
    fwd = _returns([0.004] * 40)  # steady gains, low vol
    bench = _returns([0.0] * 40)
    decision = lifecycle_from_forward_returns(fwd, bench, policy)
    assert decision.action == "hold"
    assert decision.reasons == []


def test_evaluate_lifecycle_holds_when_no_forward_data_yet() -> None:
    panel = _noise_panel()
    pos = CrossSectionalPosition(
        strategy_name="xs_momentum",
        parameters={"lookback": 126, "skip": 0, "quantile": 0.2},
        universe_symbols=list(panel.columns),
        cost_rate=0.001,
        frozen_at=panel.index.max().to_pydatetime(),
    )
    decision = evaluate_cross_sectional_lifecycle(pos, panel, CrossSectionalExitPolicy())
    assert decision.action == "hold"


def _graduated_experiment(
    strategy_name: str, universe: list[str], params: dict[str, float | int]
) -> CrossSectionalExperiment:
    gate = GateResult(
        passed=True,
        dsr_ok=True,
        pbo_ok=True,
        stability_ok=True,
        mintrl_ok=True,
        holdout_ok=True,
        required_track_record_years=1.0,
        gate_config_version="v",
    )
    graduate = Graduate(
        strategy_name=strategy_name,
        parameters=params,
        gate_result=gate,
        holdout_sharpe=1.0,
        holdout_total_return=0.1,
        holdout_n_bars=252,
    )
    trial = Trial(
        strategy_name=strategy_name,
        parameters=params,
        observed_sharpe=1.0,
        deflated_sharpe=0.6,
        pbo=0.1,
        parameter_stability_score=0.8,
    )
    return CrossSectionalExperiment(
        universe_symbols=universe,
        strategy_names=[strategy_name],
        gate_config=GateConfig(),
        trials=[trial],
        lifetime_trials=1,
        best_strategy_name=strategy_name,
        best_gate_result=gate,
        graduate=graduate,
    )


def test_freeze_cross_sectional_graduate_builds_an_open_position() -> None:
    panel = _persistent_momentum_panel()
    exp = _graduated_experiment(
        "xs_momentum", list(panel.columns), {"lookback": 126, "skip": 0, "quantile": 0.2}
    )
    now = panel.index[400].to_pydatetime()
    pos = freeze_cross_sectional_graduate(exp, frozen_at=now, cost_rate=0.001)
    assert pos.status == "open" and pos.frozen_at == now
    assert pos.strategy_name == "xs_momentum"
    assert pos.universe_symbols == list(panel.columns)


def test_freeze_raises_without_a_graduate() -> None:
    exp = _graduated_experiment("xs_momentum", ["A", "B"], {"quantile": 0.2}).model_copy(
        update={"graduate": None}
    )
    with pytest.raises(ValueError, match="no graduate"):
        freeze_cross_sectional_graduate(exp, frozen_at=exp.created_at)


def test_manage_book_promotes_a_new_graduate() -> None:
    panel = _persistent_momentum_panel()
    exp = _graduated_experiment(
        "xs_momentum", list(panel.columns), {"lookback": 126, "skip": 0, "quantile": 0.2}
    )
    # Freeze near the end so the new position is inside its grace period -> stays open.
    now = panel.index[-5].to_pydatetime()
    book = manage_cross_sectional_book([], [exp], lambda _p: panel, now=now)
    assert len(book) == 1
    assert book[0].status == "open" and book[0].strategy_name == "xs_momentum"


def test_manage_book_ignores_experiments_without_a_graduate() -> None:
    panel = _persistent_momentum_panel()
    non_grad = _graduated_experiment(
        "xs_momentum", list(panel.columns), {"lookback": 126, "skip": 0, "quantile": 0.2}
    ).model_copy(update={"graduate": None})
    book = manage_cross_sectional_book(
        [], [non_grad], lambda _p: panel, now=panel.index[-5].to_pydatetime()
    )
    assert book == []  # nothing to promote


def test_manage_book_retires_a_deteriorating_open_position_and_does_not_re_promote() -> None:
    panel = _noise_panel(n=800, seed=5)  # dollar-neutral factor ~0 vs a positive-drift benchmark
    exp = _graduated_experiment(
        "xs_momentum", list(panel.columns), {"lookback": 126, "skip": 0, "quantile": 0.2}
    )
    open_pos = freeze_cross_sectional_graduate(
        exp, frozen_at=panel.index[400].to_pydatetime(), cost_rate=0.001
    )
    now = panel.index.max().to_pydatetime()
    book = manage_cross_sectional_book([open_pos], [exp], lambda _p: panel, now=now)
    assert len(book) == 1  # the same graduate is NOT re-promoted alongside the open one
    retired = book[0]
    assert retired.status == "retired" and retired.retired_at == now
    assert retired.exit_reasons  # carries the reason(s) it was cut

    # A retired factor is kept as an honest record and never re-promoted.
    book2 = manage_cross_sectional_book(book, [exp], lambda _p: panel, now=now)
    assert len(book2) == 1 and book2[0].status == "retired"


@settings(max_examples=25, deadline=None)
@given(cut=st.integers(min_value=1, max_value=200))
def test_score_forward_is_truncation_invariant_no_lookahead(cut: int) -> None:
    """Appending future bars cannot change already-scored forward returns (rank on t, trade t+1)."""
    panel = _persistent_momentum_panel(n=700)
    pos = _momentum_position(panel, split=300)
    truncated = panel.iloc[: len(panel) - cut]
    full_equity = score_forward(pos, panel).forward_equity
    trunc_equity = score_forward(pos, truncated).forward_equity
    for i in range(len(trunc_equity)):
        assert full_equity[i].strategy_equity == pytest.approx(trunc_equity[i].strategy_equity)
