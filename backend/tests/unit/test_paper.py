"""Forward-testing / paper trading (ADR-019): freeze a graduate as of a date, then score its
performance ONLY on bars after that date — data it could not have been fit to. Deterministic and
pure over an injected frame (no network); the honest scoreboard is forward-Sharpe vs buy-and-hold."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from app.research.lab.experiment import Experiment, Graduate, Trial
from app.research.lab.gate import GateConfig, GateResult
from app.research.lab.paper import (
    ForwardEquityPoint,
    ForwardScore,
    JsonFilePaperPortfolio,
    PaperPosition,
    evaluate_forward,
    freeze_graduate,
)

_FREEZE = datetime(2020, 1, 1, tzinfo=UTC)


def _frame(n: int = 800, drift: float = 0.0005, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    closes = 100.0 * np.cumprod(1 + rng.normal(drift, 0.01, n))
    idx = pd.date_range("2018-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({"close": closes}, index=idx)


def _position(frozen_at: datetime = _FREEZE) -> PaperPosition:
    return PaperPosition(
        symbol="AAA", strategy_name="sma", parameters={"fast": 10, "slow": 30}, frozen_at=frozen_at
    )


def test_evaluate_forward_scores_only_bars_after_the_freeze() -> None:
    frame = _frame()
    score = evaluate_forward(_position(), frame)
    assert isinstance(score, ForwardScore)
    # Only bars strictly after the freeze date are counted as forward.
    expected_fwd = int((frame.index > _FREEZE).sum())
    assert score.forward_bars == expected_fwd
    assert 0 < score.forward_bars < len(frame)
    assert isinstance(score.forward_sharpe, float)
    assert isinstance(score.buy_and_hold_sharpe, float)
    assert score.beats_buy_and_hold == (score.forward_sharpe > score.buy_and_hold_sharpe)
    assert score.as_of == frame.index.max()


def test_no_forward_bars_yet_when_freeze_is_after_the_last_bar() -> None:
    frame = _frame()
    score = evaluate_forward(_position(datetime(2030, 1, 1, tzinfo=UTC)), frame)
    assert score.forward_bars == 0
    assert score.forward_return == 0.0
    assert score.beats_buy_and_hold is False
    assert score.forward_equity == []


def test_evaluate_forward_populates_a_normalized_forward_equity_series() -> None:
    """ADR-023: the forward equity index (base 1.0, compounding per bar) is served for the
    dashboard curve. Its terminal value must reconcile with the reported scalar returns."""
    frame = _frame()
    score = evaluate_forward(_position(), frame)
    # One point per forward bar.
    assert len(score.forward_equity) == score.forward_bars
    assert all(isinstance(p, ForwardEquityPoint) for p in score.forward_equity)
    # Timestamps are strictly after the freeze and strictly increasing.
    assert all(p.timestamp > _FREEZE for p in score.forward_equity)
    stamps = [p.timestamp for p in score.forward_equity]
    assert stamps == sorted(stamps) and len(set(stamps)) == len(stamps)
    # Terminal equity reconciles with the scalar total returns (index base 1.0).
    last = score.forward_equity[-1]
    assert last.strategy_equity == pytest.approx(1.0 + score.forward_return)
    assert last.buy_and_hold_equity == pytest.approx(1.0 + score.buy_and_hold_return)


def test_forward_equity_series_round_trips_through_the_json_store(tmp_path: object) -> None:
    """A persisted score with a series reloads intact (old scores without one default to [])."""
    import pathlib

    assert isinstance(tmp_path, pathlib.Path)
    frame = _frame()
    position = _position()
    scored = position.model_copy(update={"score": evaluate_forward(position, frame)})
    store = JsonFilePaperPortfolio(tmp_path / "pf.json")
    store.save([scored])
    reloaded = store.positions()[0]
    assert reloaded.score is not None
    assert len(reloaded.score.forward_equity) == scored.score.forward_bars  # type: ignore[union-attr]


def test_freeze_graduate_builds_a_position_from_a_graduated_experiment() -> None:
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
    exp = Experiment(
        symbol="CRM",
        strategy_names=["trend_filtered_mean_reversion"],
        gate_config=GateConfig(),
        trials=[
            Trial(
                strategy_name="trend_filtered_mean_reversion",
                parameters={"z_window": 51},
                observed_sharpe=1.0,
                deflated_sharpe=0.5,
                pbo=0.1,
                parameter_stability_score=0.8,
            )
        ],
        lifetime_trials=1,
        graduate=Graduate(
            strategy_name="trend_filtered_mean_reversion",
            parameters={"z_window": 51, "z_threshold": 2.25, "trend_window": 350},
            gate_result=gr,
            holdout_sharpe=0.44,
            holdout_total_return=0.08,
            holdout_n_bars=1000,
        ),
    )
    pos = freeze_graduate(exp, frozen_at=_FREEZE)
    assert pos.symbol == "CRM"
    assert pos.strategy_name == "trend_filtered_mean_reversion"
    assert pos.parameters == {"z_window": 51, "z_threshold": 2.25, "trend_window": 350}
    assert pos.frozen_at == _FREEZE


def test_freeze_graduate_rejects_a_non_graduate() -> None:
    exp = Experiment(
        symbol="X", strategy_names=[], gate_config=GateConfig(), trials=[], lifetime_trials=0
    )
    with pytest.raises(ValueError, match="graduate"):
        freeze_graduate(exp, frozen_at=_FREEZE)


def test_position_and_score_round_trip_json() -> None:
    pos = _position().model_copy(update={"score": evaluate_forward(_position(), _frame())})
    assert PaperPosition.model_validate_json(pos.model_dump_json()) == pos


def test_portfolio_add_persists_and_dedups(tmp_path) -> None:
    path = tmp_path / "portfolio.json"
    writer = JsonFilePaperPortfolio(path)
    assert writer.add(_position()) is True
    assert writer.add(_position()) is False  # same symbol+strategy -> no dup

    reader = JsonFilePaperPortfolio(path)
    positions = reader.positions()
    assert len(positions) == 1
    assert positions[0].symbol == "AAA"


def test_portfolio_save_round_trips_scores(tmp_path) -> None:
    path = tmp_path / "portfolio.json"
    scored = _position().model_copy(update={"score": evaluate_forward(_position(), _frame())})
    JsonFilePaperPortfolio(path).save([scored])
    loaded = JsonFilePaperPortfolio(path).positions()
    assert loaded == [scored]
    assert loaded[0].score is not None and loaded[0].score.forward_bars > 0


def test_portfolio_is_empty_when_file_absent(tmp_path) -> None:
    assert JsonFilePaperPortfolio(tmp_path / "nope.json").positions() == []


# ---- lifecycle / exits (ADR-020) ------------------------------------------------------------

from app.research.lab.paper import (  # noqa: E402
    ExitPolicy,
    LifecycleDecision,
    evaluate_lifecycle,
    lifecycle_from_returns,
)


def _series(vals: list[float]) -> pd.Series:
    return pd.Series(vals, index=pd.date_range("2022-01-01", periods=len(vals), freq="B"))


def test_grace_period_holds() -> None:
    d = lifecycle_from_returns(_series([0.001] * 10), _series([0.0] * 10), ExitPolicy())
    assert isinstance(d, LifecycleDecision)
    assert d.action == "hold" and "grace" in d.reasons[0]


def test_healthy_forward_holds() -> None:
    rng = np.random.default_rng(1)
    fwd = _series(list(rng.normal(0.0015, 0.004, 100)))
    bh = _series(list(rng.normal(-0.001, 0.004, 100)))
    d = lifecycle_from_returns(fwd, bh, ExitPolicy())
    assert d.action == "hold" and d.reasons == []


def test_decayed_rolling_sharpe_exits() -> None:
    policy = ExitPolicy(require_beat_buy_and_hold_forward=False, max_forward_drawdown=10.0)
    rng = np.random.default_rng(0)
    fwd = _series(list(rng.normal(-0.002, 0.008, 100)))
    d = lifecycle_from_returns(fwd, _series(list(rng.normal(0.0, 0.008, 100))), policy)
    assert d.action == "exit" and any("rolling Sharpe" in r for r in d.reasons)


def test_forward_drawdown_breach_exits() -> None:
    policy = ExitPolicy(
        require_beat_buy_and_hold_forward=False,
        min_rolling_sharpe=-100.0,
        max_forward_drawdown=0.05,
    )
    vals = [-0.03] * 12 + [0.0005] * 90  # ~30% drop then drift up
    d = lifecycle_from_returns(_series(vals), _series([0.0] * 102), policy)
    assert d.action == "exit" and any("drawdown" in r for r in d.reasons)


def test_stops_beating_buy_and_hold_forward_exits() -> None:
    policy = ExitPolicy(min_rolling_sharpe=-100.0, max_forward_drawdown=10.0)  # only the B&H rule
    rng = np.random.default_rng(2)
    fwd = _series(list(rng.normal(0.0005, 0.01, 100)))
    bh = _series(list(rng.normal(0.003, 0.008, 100)))
    d = lifecycle_from_returns(fwd, bh, policy)
    assert d.action == "exit" and any("buy-and-hold" in r for r in d.reasons)


def test_exit_policy_version_hash_is_deterministic_and_sensitive() -> None:
    assert ExitPolicy().version_hash == ExitPolicy().version_hash
    assert ExitPolicy(max_forward_drawdown=0.2).version_hash != ExitPolicy().version_hash


def test_evaluate_lifecycle_holds_when_no_forward_data() -> None:
    pos = _position(datetime(2030, 1, 1, tzinfo=UTC))
    d = evaluate_lifecycle(pos, _frame(), ExitPolicy())
    assert d.action == "hold"


def test_evaluate_lifecycle_runs_on_a_real_frame() -> None:
    d = evaluate_lifecycle(_position(), _frame(), ExitPolicy())
    assert d.action in {"hold", "exit"}
