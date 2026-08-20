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
from app.research.lab.pool_report import DiagnosticSummary, summarize_pool

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "research_pool"
PORTFOLIO = DATA / "paper_portfolio.json"


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "n/a"


def _diagnostic(summary: DiagnosticSummary | None, finalists: DiagnosticSummary | None) -> str:
    """Three different facts that all used to print as "not measured" (ADR-051).

    A pool whose experiments predate ADR-038/039 carries no value at all; a pool that carries the
    value but graduated nothing has an empty gate-passer window; a pool with both has a number.
    Collapsing the first two reads as "we never measured it" when the truth is "nothing passed".
    """
    if summary is not None:
        return (
            f"median {summary.median:+.2f} | p95 {summary.p95:+.2f} | "
            f"max {summary.maximum:+.2f} (n={summary.n})"
        )
    if finalists is None:
        return "not measured (no experiment carries it — pre-ADR-038/039 pool)"
    return "no experiment passed the gate"


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

    # ADR-038/039/051: read these against data/null_calibration/*.json — the same statistics
    # measured on symbols with no edge by construction. A pool median at or below the null's is the
    # search producing what it produces from noise. The FINALIST row is the comparable one: the
    # null artifacts record one finalist per searched symbol, graduate or not.
    print("\nout-of-sample Sharpe (compare with data/null_calibration/ — same statistic, no edge):")
    for label, finalists, passers in (
        ("walk-forward", report.walk_forward_finalists, report.walk_forward_graduates),
        ("purged-CV", report.purged_cv_finalists, report.purged_cv_graduates),
    ):
        print(f"  {label:<13} finalists  : {_diagnostic(finalists, finalists)}")
        print(f"  {label:<13} gate passers: {_diagnostic(passers, finalists)}")

    book = report.book
    print(
        f"\nforward book: {report.n_open_positions} open — "
        f"{book.n_survivors} clear the bar (mean fwd Sharpe {_fmt(book.survivor_mean_forward_sharpe)}), "
        f"{book.n_non_survivors} do not ({_fmt(book.non_survivor_mean_forward_sharpe)}), "
        f"{book.n_unknown} unknown (frozen before ADR-033)"
    )


if __name__ == "__main__":
    main()
