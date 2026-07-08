"""Portfolio manager (ADR-020): one loop that PROMOTES new graduates, MONITORS open positions, and
EXITS deteriorating ones. Exit/hold is forced via the ExitPolicy so the orchestration is tested
independently of data specifics."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from app.research.lab.experiment import Experiment, Graduate, Trial
from app.research.lab.gate import GateConfig, GateResult
from app.research.lab.paper import ExitPolicy, PaperPosition
from app.research.lab.portfolio_manager import manage_portfolio

_NOW = datetime(2024, 6, 1, tzinfo=UTC)
_ALWAYS_EXIT = ExitPolicy(min_rolling_sharpe=100.0)  # rolling Sharpe never >= 100 -> always exits
_NEVER_EXIT = ExitPolicy(
    min_rolling_sharpe=-100.0, max_forward_drawdown=100.0, require_beat_buy_and_hold_forward=False
)


def _frame() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    closes = 100.0 * np.cumprod(1 + rng.normal(0.0005, 0.01, 400))
    idx = pd.date_range("2022-01-01", periods=400, freq="B", tz="UTC")
    return pd.DataFrame({"close": closes}, index=idx)


def _provider(symbol: str) -> pd.DataFrame:
    return _frame()


def _graduate_exp(symbol: str) -> Experiment:
    gr = GateResult(
        passed=True,
        dsr_ok=True,
        pbo_ok=True,
        stability_ok=True,
        mintrl_ok=True,
        holdout_ok=True,
        required_track_record_years=1.0,
        gate_config_version="v",
    )
    return Experiment(
        symbol=symbol,
        strategy_names=["sma"],
        gate_config=GateConfig(),
        trials=[
            Trial(
                strategy_name="sma",
                parameters={"fast": 10, "slow": 30},
                observed_sharpe=1.0,
                deflated_sharpe=0.5,
                pbo=0.1,
                parameter_stability_score=0.8,
            )
        ],
        lifetime_trials=1,
        graduate=Graduate(
            strategy_name="sma",
            parameters={"fast": 10, "slow": 30},
            gate_result=gr,
            holdout_sharpe=0.5,
            holdout_total_return=0.1,
            holdout_n_bars=252,
        ),
    )


def _open_position(frozen_at: datetime = datetime(2022, 3, 1, tzinfo=UTC)) -> PaperPosition:
    return PaperPosition(
        symbol="AAA", strategy_name="sma", parameters={"fast": 10, "slow": 30}, frozen_at=frozen_at
    )


def test_promotes_a_new_graduate() -> None:
    out = manage_portfolio([], [_graduate_exp("CRM")], _provider, exit_policy=_NEVER_EXIT, now=_NOW)
    assert len(out) == 1
    assert out[0].symbol == "CRM" and out[0].status == "open" and out[0].frozen_at == _NOW


def test_does_not_duplicate_an_already_held_name() -> None:
    existing = _open_position().model_copy(update={"symbol": "CRM"})
    out = manage_portfolio(
        [existing], [_graduate_exp("CRM")], _provider, exit_policy=_NEVER_EXIT, now=_NOW
    )
    assert len(out) == 1  # not re-added


def test_exits_a_deteriorating_open_position() -> None:
    out = manage_portfolio([_open_position()], [], _provider, exit_policy=_ALWAYS_EXIT, now=_NOW)
    assert out[0].status == "closed"
    assert out[0].closed_at == _NOW
    assert out[0].exit_reasons  # has reasons
    assert out[0].score is not None  # final score recorded


def test_keeps_a_healthy_open_position_and_updates_score() -> None:
    out = manage_portfolio([_open_position()], [], _provider, exit_policy=_NEVER_EXIT, now=_NOW)
    assert out[0].status == "open"
    assert out[0].score is not None and out[0].score.forward_bars > 0


def test_does_not_re_evaluate_closed_positions() -> None:
    closed = _open_position().model_copy(
        update={"status": "closed", "closed_at": _NOW, "exit_reasons": ["prior exit"]}
    )
    out = manage_portfolio([closed], [], _provider, exit_policy=_ALWAYS_EXIT, now=_NOW)
    assert out[0].status == "closed" and out[0].exit_reasons == ["prior exit"]


def test_experiment_without_a_graduate_is_skipped() -> None:
    no_grad = Experiment(
        symbol="X", strategy_names=[], gate_config=GateConfig(), trials=[], lifetime_trials=0
    )
    out = manage_portfolio([], [no_grad], _provider, exit_policy=_NEVER_EXIT, now=_NOW)
    assert out == []


def test_closed_name_is_not_re_promoted() -> None:
    closed = _open_position().model_copy(
        update={"symbol": "CRM", "status": "closed", "closed_at": _NOW}
    )
    out = manage_portfolio(
        [closed], [_graduate_exp("CRM")], _provider, exit_policy=_NEVER_EXIT, now=_NOW
    )
    assert len(out) == 1 and out[0].status == "closed"  # a cut loser isn't re-added
