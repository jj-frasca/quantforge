"""Universe hunt (ADR-014): run the search across many symbols, resiliently (one bad symbol
never kills the run), and rank the results into a cross-symbol leaderboard. Widening the universe
is the honest way to find edges — trial counts are per-symbol, so more names = more independent
shots, not a bigger overfitting penalty on any one name."""

import numpy as np
import pandas as pd

from app.data.fundamentals import FundamentalCriteria, FundamentalSnapshot
from app.research.lab.experiment import Experiment, InMemoryExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.universe import rank_experiments, run_universe_hunt

_LENIENT = GateConfig(
    dsr_min=-100.0,
    pbo_max=1.01,
    stability_min=-1.0,
    holdout_sharpe_min=-100.0,
    require_beat_buy_and_hold=False,
)


def _trend(seed: int, drift: float, n: int = 1500) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    closes = 100.0 * np.cumprod(1 + rng.normal(drift, 0.01, n))
    idx = pd.date_range("2016-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({"close": closes}, index=idx)


def _provider(frames: dict[str, pd.DataFrame]):
    def provide(symbol: str) -> pd.DataFrame:
        if symbol not in frames:
            raise ValueError(f"no data for {symbol}")
        return frames[symbol]

    return provide


def test_universe_hunt_runs_every_symbol_and_records_to_the_pool() -> None:
    frames = {"AAA": _trend(1, 0.0005), "BBB": _trend(2, 0.0005)}
    store = InMemoryExperimentStore()
    result = run_universe_hunt(["AAA", "BBB"], ["sma", "momentum"], _provider(frames), store=store)
    assert len(result.experiments) == 2
    assert result.errors == {}
    assert store.trials_for_symbol("AAA") == 2
    assert store.trials_for_symbol("BBB") == 2


def test_a_failing_symbol_is_captured_and_others_still_run() -> None:
    frames = {"GOOD": _trend(1, 0.0005)}  # "BAD" absent -> provider raises
    result = run_universe_hunt(["GOOD", "BAD"], ["sma", "momentum"], _provider(frames))
    assert len(result.experiments) == 1
    assert result.experiments[0].symbol == "GOOD"
    assert "BAD" in result.errors


def test_leaderboard_ranks_graduates_first_then_by_deflated_sharpe() -> None:
    # Strong trend + lenient gate -> both graduate; ranking is by holdout/DSR.
    frames = {"HI": _trend(1, 0.0012), "LO": _trend(2, 0.0011)}
    result = run_universe_hunt(
        ["HI", "LO"], ["sma", "momentum"], _provider(frames), config=_LENIENT
    )
    rows = rank_experiments(result.experiments)
    assert {r.symbol for r in rows} == {"HI", "LO"}
    assert all(r.strategy_name for r in rows)
    # Sorted by (graduated, deflated_sharpe) descending: each row ranks >= the next.
    keys = [(r.graduated, r.deflated_sharpe) for r in rows]
    assert keys == sorted(keys, reverse=True)


def test_fundamentals_provider_applies_the_veto_per_symbol() -> None:
    frames = {"AAA": _trend(1, 0.0012)}
    bad = FundamentalSnapshot(
        symbol="AAA",
        cik=1,
        entity_name="x",
        fiscal_year=2024,
        form="10-K",
        accession_number="a",
        source_url="http://x",
        revenue=1.0,
        revenue_growth_yoy=-0.5,
        net_margin=-0.2,
    )
    result = run_universe_hunt(
        ["AAA"],
        ["sma", "momentum"],
        _provider(frames),
        config=_LENIENT,
        fundamentals_provider=lambda s: bad,
        fundamental_criteria=FundamentalCriteria(),
    )
    exp = result.experiments[0]
    assert exp.fundamental_screen is not None and exp.fundamental_screen.passed is False
    assert exp.graduate is None  # vetoed despite lenient technicals


def test_empty_universe_returns_nothing() -> None:
    result = run_universe_hunt([], ["sma"], _provider({}))
    assert result.experiments == []
    assert rank_experiments(result.experiments) == []


def test_rank_skips_experiments_with_no_trials() -> None:
    empty = Experiment(
        symbol="AAA", strategy_names=[], gate_config=GateConfig(), trials=[], lifetime_trials=0
    )
    assert rank_experiments([empty]) == []
