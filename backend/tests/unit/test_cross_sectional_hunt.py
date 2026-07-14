"""Cross-sectional hunt orchestration (ADR-024 integration). Builds a price panel from a resilient
per-symbol frame provider, runs the search with the pool's cumulative prior-trial count (the MinTRL
flywheel), and persists the experiment. Injectable over provider + store so it is unit-testable
without network — the analog of scheduled_hunt.hunt_and_promote for the cross-sectional dimension."""

import numpy as np
import pandas as pd
import pytest

from app.research.cross_sectional.hunt import (
    price_panel_from_frames,
    run_cross_sectional_hunt,
)
from app.research.cross_sectional.store import InMemoryCrossSectionalStore


def _frame(n: int, seed: int, start: str = "2015-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    closes = 100.0 * np.cumprod(1.0 + rng.normal(0.0003, 0.01, n))
    idx = pd.date_range(start, periods=n, freq="B", tz="UTC")
    return pd.DataFrame({"close": closes}, index=idx)


def _provider(frames: dict[str, pd.DataFrame]):
    def provide(symbol: str) -> pd.DataFrame:
        if symbol not in frames:
            raise ValueError(f"no data for {symbol}")
        return frames[symbol]

    return provide


def test_price_panel_from_frames_keeps_only_common_complete_dates() -> None:
    a = _frame(10, 1, start="2020-01-01")
    b = _frame(10, 2, start="2020-01-08")  # starts a week later -> partial overlap
    panel = price_panel_from_frames({"A": a["close"].to_frame(), "B": b["close"].to_frame()})
    assert list(panel.columns) == ["A", "B"]
    assert panel.index.min() == b.index.min()  # intersection starts at the later series' start
    assert not panel.isna().any().any()  # complete rows only


def test_run_cross_sectional_hunt_persists_and_returns_the_experiment() -> None:
    frames = {s: _frame(560, i) for i, s in enumerate(["A", "B", "C", "D"])}
    store = InMemoryCrossSectionalStore()
    result = run_cross_sectional_hunt(
        ["A", "B", "C", "D"],
        _provider(frames),
        store=store,
        strategy_names=["xs_reversal"],
        quantiles=(0.2, 0.3),
    )
    assert result.experiment.universe_symbols == ["A", "B", "C", "D"]
    assert result.panel_bars == 560
    assert result.errors == {}
    assert store.all() == [result.experiment]  # persisted


def test_run_cross_sectional_hunt_is_resilient_to_a_bad_symbol() -> None:
    frames = {s: _frame(560, i) for i, s in enumerate(["A", "B", "C"])}
    store = InMemoryCrossSectionalStore()
    result = run_cross_sectional_hunt(
        ["A", "B", "C", "BAD"],
        _provider(frames),
        store=store,
        strategy_names=["xs_reversal"],
        quantiles=(0.2, 0.3),
    )
    assert "BAD" in result.errors
    assert result.experiment.universe_symbols == ["A", "B", "C"]  # the rest still ran


def test_run_cross_sectional_hunt_chains_prior_trials_from_the_store() -> None:
    frames = {s: _frame(560, i) for i, s in enumerate(["A", "B", "C"])}
    store = InMemoryCrossSectionalStore()
    kwargs = {"store": store, "strategy_names": ["xs_reversal"], "quantiles": (0.2, 0.3)}
    first = run_cross_sectional_hunt(["A", "B", "C"], _provider(frames), **kwargs)
    second = run_cross_sectional_hunt(["A", "B", "C"], _provider(frames), **kwargs)
    # the second run's MinTRL denominator includes the first run's trials (the flywheel).
    assert second.experiment.lifetime_trials > first.experiment.lifetime_trials


def test_run_cross_sectional_hunt_needs_at_least_two_symbols() -> None:
    frames = {"A": _frame(560, 0)}
    store = InMemoryCrossSectionalStore()
    with pytest.raises(ValueError, match="at least 2 symbols"):
        run_cross_sectional_hunt(["A", "BAD"], _provider(frames), store=store)
