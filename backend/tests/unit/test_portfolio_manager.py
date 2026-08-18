"""Portfolio manager (ADR-020): one loop that PROMOTES new graduates, MONITORS open positions, and
EXITS deteriorating ones. Exit/hold is forced via the ExitPolicy so the orchestration is tested
independently of data specifics."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from app.research.lab.experiment import Experiment, Graduate, Trial
from app.research.lab.gate import GateConfig, GateResult
from app.research.lab.paper import ExitPolicy, ForwardScore, PaperPosition
from app.research.lab.portfolio_manager import deflation_cohorts, manage_portfolio

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


def test_a_bad_data_fetch_keeps_the_position_and_does_not_crash_the_book() -> None:
    # Regression (prod 2026-08-04): the daily consolidation monitors held positions via a live
    # yfinance fetch. When yfinance is flaky (a malformed bar -> decimal.InvalidOperation, an
    # ArithmeticError), ONE position's fetch must NOT crash the whole managed book — that position
    # is left unchanged this cycle while the healthy ones are still monitored.
    from decimal import InvalidOperation

    good = _open_position().model_copy(update={"symbol": "GOOD"})
    bad = _open_position().model_copy(update={"symbol": "BAD"})

    def flaky_provider(symbol: str) -> pd.DataFrame:
        if symbol == "BAD":
            raise InvalidOperation("[<class 'decimal.ConversionSyntax'>]")
        return _frame()

    out = manage_portfolio([good, bad], [], flaky_provider, exit_policy=_NEVER_EXIT, now=_NOW)
    by_symbol = {p.symbol: p for p in out}
    assert len(out) == 2
    assert by_symbol["GOOD"].status == "open" and by_symbol["GOOD"].score is not None  # monitored
    assert by_symbol["BAD"].status == "open"  # left unchanged, not crashed, not exited


def test_experiment_without_a_graduate_is_skipped() -> None:
    no_grad = Experiment(
        symbol="X", strategy_names=[], gate_config=GateConfig(), trials=[], lifetime_trials=0
    )
    out = manage_portfolio([], [no_grad], _provider, exit_policy=_NEVER_EXIT, now=_NOW)
    assert out == []


def test_newly_promoted_reports_positions_absent_from_the_prior_book() -> None:
    from app.research.lab.portfolio_manager import newly_promoted

    held = _open_position().model_copy(update={"symbol": "OLD"})
    before = [held]
    fresh = _open_position().model_copy(update={"symbol": "NEW", "strategy_name": "adx"})
    after = [held, fresh]
    promoted = newly_promoted(before, after)
    assert [(p.symbol, p.strategy_name) for p in promoted] == [("NEW", "adx")]


def test_newly_promoted_is_empty_when_nothing_new() -> None:
    from app.research.lab.portfolio_manager import newly_promoted

    held = _open_position()
    assert newly_promoted([held], [held]) == []


def test_closed_name_is_not_re_promoted() -> None:
    closed = _open_position().model_copy(
        update={"symbol": "CRM", "status": "closed", "closed_at": _NOW}
    )
    out = manage_portfolio(
        [closed], [_graduate_exp("CRM")], _provider, exit_policy=_NEVER_EXIT, now=_NOW
    )
    assert len(out) == 1 and out[0].status == "closed"  # a cut loser isn't re-added


# ---- ADR-033: the deflation verdict is threaded through promotion, and reported by cohort --------


def _scored_position(
    symbol: str, *, survives: bool | None, forward_sharpe: float | None
) -> PaperPosition:
    score = None
    if forward_sharpe is not None:
        score = ForwardScore(
            forward_bars=63,
            forward_return=0.05,
            forward_sharpe=forward_sharpe,
            buy_and_hold_return=0.03,
            buy_and_hold_sharpe=0.4,
            beats_buy_and_hold=True,
            as_of=_NOW,
        )
    return PaperPosition(
        symbol=symbol,
        strategy_name="rsi_mean_reversion",
        parameters={"window": 14},
        frozen_at=_NOW,
        score=score,
        survives_universe_deflation=survives,
    )


def test_promotion_records_the_universe_deflation_verdict_on_the_new_position() -> None:
    out = manage_portfolio(
        [],
        [_graduate_exp("CRM")],
        _provider,
        exit_policy=_NEVER_EXIT,
        now=_NOW,
        universe_n_symbols=607,
    )
    assert out[0].universe_n_symbols == 607
    assert out[0].survives_universe_deflation is not None


def test_promotion_without_a_universe_leaves_the_verdict_unknown() -> None:
    out = manage_portfolio([], [_graduate_exp("CRM")], _provider, exit_policy=_NEVER_EXIT, now=_NOW)
    assert out[0].survives_universe_deflation is None


def test_deflation_cohorts_splits_the_book_and_excludes_the_unknowns() -> None:
    # Positions frozen before ADR-033 carry None. They are NOT assigned a cohort — counting them
    # as failures would fabricate a control group out of missing metadata.
    book = [
        _scored_position("A", survives=True, forward_sharpe=1.5),
        _scored_position("B", survives=True, forward_sharpe=0.5),
        _scored_position("C", survives=False, forward_sharpe=-0.4),
        _scored_position("D", survives=None, forward_sharpe=9.9),
    ]
    cohorts = deflation_cohorts(book)
    assert cohorts.n_survivors == 2
    assert cohorts.n_non_survivors == 1
    assert cohorts.n_unknown == 1
    assert cohorts.survivor_mean_forward_sharpe == pytest.approx(1.0)
    assert cohorts.non_survivor_mean_forward_sharpe == pytest.approx(-0.4)


def test_deflation_cohorts_ignores_positions_with_no_forward_score_yet() -> None:
    book = [_scored_position("A", survives=True, forward_sharpe=None)]
    cohorts = deflation_cohorts(book)
    assert cohorts.n_survivors == 1  # still counted in the book
    assert cohorts.survivor_mean_forward_sharpe is None  # but no score to average


def test_deflation_cohorts_of_an_empty_book_is_all_zeros() -> None:
    cohorts = deflation_cohorts([])
    assert (cohorts.n_survivors, cohorts.n_non_survivors, cohorts.n_unknown) == (0, 0, 0)
    assert cohorts.survivor_mean_forward_sharpe is None
