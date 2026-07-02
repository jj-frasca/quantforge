"""Drive a StrategyLab hunt on real max-history daily data (ADR-014/015/016).

Usage: PYTHONPATH=. uv run python scripts/run_hunt.py [SYMBOL ...]   (default: SPY QQQ AAPL)

Fetches the longest available daily history per symbol, searches every catalog strategy on the
in-sample split, scores the best on the SEALED holdout, and applies the deterministic gate.
Findings accumulate in a JSON research pool so the lifetime trial count compounds (the DSR/MinTRL
honesty flywheel). This is the agent-driven loop, run locally — never in CI (live network).
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

from app.data.sources.yfinance import YFinanceAdapter
from app.research.frames import bars_to_frame
from app.research.lab.experiment import JsonFileExperimentStore
from app.research.lab.gate import GateConfig
from app.research.lab.search import run_search
from app.research.strategies.catalog import STRATEGY_CATALOG

POOL = Path("/tmp/qf_pool.json")
START = datetime(2005, 1, 1, tzinfo=UTC)


def main() -> None:
    symbols = sys.argv[1:] or ["SPY", "QQQ", "AAPL"]
    names = [entry.name for entry in STRATEGY_CATALOG]
    adapter = YFinanceAdapter()
    store = JsonFileExperimentStore(POOL)
    end = datetime.now(UTC)

    for symbol in symbols:
        prior = store.trials_for_symbol(symbol)
        bars = adapter.fetch_price_bars(symbol, START, end)
        frame = bars_to_frame(bars)
        exp = run_search(
            frame, symbol, names, config=GateConfig(), prior_trials=prior, rationale="first hunt"
        )
        store.add(exp)

        span_years = (frame.index.max() - frame.index.min()).days / 365.25
        print(
            f"\n{'=' * 78}\n{symbol}  |  {len(frame)} daily bars  |  {span_years:.1f}y  "
            f"|  lifetime trials: {exp.lifetime_trials}\n{'=' * 78}"
        )
        print(f"{'strategy':<32}{'obs SR':>9}{'DSR':>9}{'PBO':>8}{'stability':>11}")
        for t in sorted(exp.trials, key=lambda x: x.deflated_sharpe, reverse=True):
            print(
                f"{t.strategy_name:<32}{t.observed_sharpe:>9.2f}{t.deflated_sharpe:>9.2f}"
                f"{t.pbo:>8.2f}{t.parameter_stability_score:>11.2f}"
            )

        g = exp.best_gate_result
        verdict = "GRADUATED ✅" if (g and g.passed) else "NO WINNER ❌"
        print(f"\nbest: {exp.best_strategy_name}  ->  {verdict}")
        if g and not g.passed:
            for reason in g.reasons:
                print(f"  - {reason}")
        if exp.graduate:
            gr = exp.graduate
            print(
                f"  holdout Sharpe {gr.holdout_sharpe:.2f}, holdout return "
                f"{gr.holdout_total_return * 100:.1f}%  params={gr.parameters}"
            )


if __name__ == "__main__":
    main()
