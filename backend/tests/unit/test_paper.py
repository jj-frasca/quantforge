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
