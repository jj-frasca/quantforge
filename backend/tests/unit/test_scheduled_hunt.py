"""Scheduled mass-test → auto-promotion wiring (WP-F, ADR-020). `hunt_and_promote` composes the
universe hunt with the WP-A managed portfolio: every pool graduate we don't already hold is frozen
as an OPEN position. Wiring is tested independently of data specifics — the hunt is driven with a
tiny symbol set (or none) and promotion is asserted against a fake in-memory portfolio."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from app.research.lab.experiment import (
    Experiment,
    Graduate,
    InMemoryExperimentStore,
    Trial,
)
from app.research.lab.gate import GateConfig, GateResult
from app.research.lab.paper import PaperPosition
from app.research.lab.scheduled_hunt import hunt_and_promote
from app.research.lab.value_filter import ValueGateConfig
from app.research.valuation import UndervaluationScore

_NOW = datetime(2024, 6, 1, tzinfo=UTC)


class _FakePortfolio:
    def __init__(self, positions: list[PaperPosition] | None = None) -> None:
        self._positions = list(positions or [])
        self.saved: list[PaperPosition] | None = None

    def positions(self) -> list[PaperPosition]:
        return list(self._positions)

    def save(self, positions: list[PaperPosition]) -> None:
        self._positions = list(positions)
        self.saved = list(positions)


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


def _non_graduate_exp(symbol: str) -> Experiment:
    return Experiment(
        symbol=symbol, strategy_names=[], gate_config=GateConfig(), trials=[], lifetime_trials=0
    )


def test_hunt_and_promote_promotes_a_pool_graduate() -> None:
    pool = InMemoryExperimentStore()
    pool.add(_graduate_exp("CRM"))
    portfolio = _FakePortfolio()

    result = hunt_and_promote([], ["sma"], _provider, pool=pool, portfolio=portfolio, now=_NOW)

    assert [p.symbol for p in result.positions] == ["CRM"]
    assert result.positions[0].status == "open" and result.positions[0].frozen_at == _NOW
    assert [p.symbol for p in result.promoted] == ["CRM"]
    assert portfolio.saved is not None and portfolio.saved[0].symbol == "CRM"


def test_hunt_and_promote_ignores_non_graduates() -> None:
    pool = InMemoryExperimentStore()
    pool.add(_non_graduate_exp("X"))
    portfolio = _FakePortfolio()

    result = hunt_and_promote([], ["sma"], _provider, pool=pool, portfolio=portfolio, now=_NOW)

    assert result.positions == []
    assert result.promoted == []


def test_hunt_and_promote_does_not_re_add_a_held_name() -> None:
    pool = InMemoryExperimentStore()
    pool.add(_graduate_exp("CRM"))
    existing = PaperPosition(
        symbol="CRM", strategy_name="sma", parameters={"fast": 10, "slow": 30}, frozen_at=_NOW
    )
    portfolio = _FakePortfolio([existing])

    result = hunt_and_promote([], ["sma"], _provider, pool=pool, portfolio=portfolio, now=_NOW)

    assert len([p for p in result.positions if p.symbol == "CRM"]) == 1
    assert result.promoted == []


def _uscore(symbol: str, score: float | None) -> UndervaluationScore:
    return UndervaluationScore(
        symbol=symbol,
        cik=1,
        entity_name="x",
        fiscal_year=2024,
        form="10-K",
        accession_number="a",
        source_url="http://x",
        current_price=50.0,
        pe_ratio=10.0,
        pe_percentile=0.3,
        ps_ratio=2.0,
        ps_percentile=0.3,
        intrinsic_value_per_share=55.0,
        margin_of_safety=0.1,
        growth_rate_used=0.03,
        fcf_is_net_income_proxy=False,
        score=score,
        flags=[],
    )


def _long_provider(symbol: str) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    closes = 100.0 * np.cumprod(1 + rng.normal(0.0004, 0.01, 1500))
    idx = pd.date_range("2015-01-01", periods=1500, freq="B", tz="UTC")
    return pd.DataFrame({"close": closes}, index=idx)


def test_hunt_and_promote_forwards_value_provider_and_config_to_the_hunt() -> None:
    # ADR-023 wiring (WP-J): a value_provider records the score on each hunted name; a value_config
    # additionally pre-screens out names below min_score before they are ever hunted.
    pool = InMemoryExperimentStore()
    portfolio = _FakePortfolio()
    scores = {"CHEAP": _uscore("CHEAP", 0.8), "RICH": _uscore("RICH", 0.1)}

    result = hunt_and_promote(
        ["CHEAP", "RICH"],
        ["sma"],
        _long_provider,
        pool=pool,
        portfolio=portfolio,
        now=_NOW,
        refine=False,
        value_provider=lambda s: scores[s],
        value_config=ValueGateConfig(min_score=0.5),
    )

    hunted = {e.symbol for e in result.hunt.experiments}
    assert hunted == {"CHEAP"}  # RICH pre-screened out, never hunted
    assert "RICH" in result.hunt.filtered
    recorded = result.hunt.experiments[0].undervaluation_score
    assert recorded is not None and recorded.score == 0.8


def test_hunt_and_promote_runs_the_hunt_and_records_experiments() -> None:
    pool = InMemoryExperimentStore()
    portfolio = _FakePortfolio()

    def long_provider(symbol: str) -> pd.DataFrame:
        rng = np.random.default_rng(1)
        closes = 100.0 * np.cumprod(1 + rng.normal(0.0004, 0.01, 1500))
        idx = pd.date_range("2015-01-01", periods=1500, freq="B", tz="UTC")
        return pd.DataFrame({"close": closes}, index=idx)

    result = hunt_and_promote(
        ["AAA"], ["sma"], long_provider, pool=pool, portfolio=portfolio, now=_NOW, refine=False
    )

    assert result.hunt.experiments  # the hunt ran on the universe and produced an experiment
    assert pool.all()  # and accumulated it in the pool (the trial flywheel)
