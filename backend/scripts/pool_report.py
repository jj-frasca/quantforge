"""Print the honest state of the research programme (ADR-033 reporting).

Usage: PYTHONPATH=. uv run python scripts/pool_report.py

Reads the committed per-symbol research pool (ADR-032) and the paper book and reports: search
effort, the graduate funnel, how many graduates clear the ADR-018 universe-deflation bar, the
closest near-misses, and the forward performance of the deflation cohorts. Read-only — writes
nothing, touches no network, so it is safe to run at any time.
"""

from pathlib import Path

from app.research.lab.experiment import PartitionedExperimentStore
from app.research.lab.frontier import describe_frontier
from app.research.lab.paper import JsonFilePaperPortfolio
from app.research.lab.pool_report import summarize_pool

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "research_pool"
PORTFOLIO = DATA / "paper_portfolio.json"


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "n/a"


def main() -> None:
    report = summarize_pool(
        PartitionedExperimentStore(POOL).all(), JsonFilePaperPortfolio(PORTFOLIO).positions()
    )

    print(f"{'=' * 82}\nQUANTFORGE — state of the research programme\n{'=' * 82}")
    print(
        f"searched : {report.n_experiments} experiments over {report.n_symbols} symbols "
        f"({report.n_trials} lifetime trials — the DSR/MinTRL denominator)"
    )
    print(
        f"graduates: {report.n_graduate_experiments} graduate experiments -> "
        f"{report.n_leaderboard_graduates} distinct symbols"
    )
    print(
        f"DEFLATION: {report.n_surviving_deflation} of {report.n_leaderboard_graduates} clear the "
        f"ADR-018 best-of-{report.n_symbols} bar — the rest are not distinguishable from "
        f"selection luck"
    )

    # ADR-043: the bar above says what must be OBSERVED; this says what must be TRUE for that
    # observation to happen 80% of the time. Their difference is estimation noise, which is why an
    # edge sitting exactly at the bar is a coin flip rather than a graduate.
    if report.frontier is not None:
        f = report.frontier
        print(
            f"RESOLUTION: an edge must be a TRUE annualized Sharpe of {f.detectable_sharpe:.2f} to "
            f"clear that bar 80% of the time ({f.holdout_years:.1f}y holdout, SE {f.standard_error:.2f})"
        )
        halved = describe_frontier(max(2, f.n_symbols // 2), f.holdout_years)
        doubled = describe_frontier(f.n_symbols, f.holdout_years * 2)
        print(
            f"            halving the universe -> {halved.detectable_sharpe:.2f}; doubling the "
            f"holdout -> {doubled.detectable_sharpe:.2f}. History is the stronger lever."
        )

    if report.near_misses:
        print("\nclosest to the bar (holdout Sharpe vs its own threshold):")
        print(f"  {'symbol':<8}{'strategy':<32}{'holdout':>9}{'bar':>7}{'ratio':>7}{'yrs':>6}")
        for m in report.near_misses:
            print(
                f"  {m.symbol:<8}{m.strategy_name:<32}{m.holdout_sharpe:>9.2f}{m.bar:>7.2f}"
                f"{m.ratio_to_bar:>7.2f}{m.holdout_years:>6.1f}"
            )

    # ADR-038/039: read these against data/null_calibration/*.json — the same statistics measured
    # on symbols with no edge by construction. A pool median below the null's p95 means the gate is
    # admitting what the pipeline produces from noise.
    for label, summary in (
        ("walk-forward", report.walk_forward_graduates),
        ("purged-CV", report.purged_cv_graduates),
    ):
        if summary is None:
            print(f"\n{label:<13} OOS Sharpe of gate passers: not measured (pre-ADR-038/039 pool)")
        else:
            print(
                f"\n{label:<13} OOS Sharpe of gate passers: median {summary.median:+.2f} | "
                f"p95 {summary.p95:+.2f} | max {summary.maximum:+.2f} (n={summary.n}) "
                f"-- compare with data/null_calibration/"
            )

    book = report.book
    print(
        f"\nforward book: {report.n_open_positions} open — "
        f"{book.n_survivors} clear the bar (mean fwd Sharpe {_fmt(book.survivor_mean_forward_sharpe)}), "
        f"{book.n_non_survivors} do not ({_fmt(book.non_survivor_mean_forward_sharpe)}), "
        f"{book.n_unknown} unknown (frozen before ADR-033)"
    )


if __name__ == "__main__":
    main()
