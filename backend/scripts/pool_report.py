"""Print the honest state of the research programme (ADR-033 reporting).

Usage: PYTHONPATH=. uv run python scripts/pool_report.py

Reads the committed per-symbol research pool (ADR-032) and the paper book and reports: search
effort, the graduate funnel, how many graduates clear the ADR-018 universe-deflation bar, the
closest near-misses, and the forward performance of the deflation cohorts. Read-only — writes
nothing, touches no network, so it is safe to run at any time.
"""

from pathlib import Path

from app.research.lab.calibration import NullCalibration
from app.research.lab.experiment import PartitionedExperimentStore
from app.research.lab.frontier import describe_frontier
from app.research.lab.paper import JsonFilePaperPortfolio
from app.research.lab.pool_report import (
    EXCESS_STATISTIC,
    DiagnosticSummary,
    compare_with_null,
    summarize_pool,
)

DATA = Path(__file__).resolve().parents[2] / "data"
POOL = DATA / "research_pool"
NULL_CALIBRATION = DATA / "null_calibration"
PORTFOLIO = DATA / "paper_portfolio.json"


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "n/a"


def _short(version: str) -> str:
    """Abbreviate a 64-char fingerprint but never the `legacy-unspecified` sentinel, which becomes
    unreadable and looks like a hash prefix when truncated."""
    return version if len(version) <= 18 else f"{version[:12]}…"


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
    experiments = PartitionedExperimentStore(POOL).all()
    report = summarize_pool(experiments, JsonFilePaperPortfolio(PORTFOLIO).positions())

    print(f"{'=' * 82}\nQUANTFORGE — state of the research programme\n{'=' * 82}")
    print(
        f"searched : {report.n_experiments} experiments over {report.n_symbols} symbols "
        f"({report.n_trials} lifetime trials — sum of per-symbol DSR/MinTRL denominators)"
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
    # ADR-052: a median over two search families is a blend of two procedures, and the comparison
    # below is only meaningful against a calibration artifact carrying the SAME fingerprint.
    if report.search_config_versions:
        families = " | ".join(
            f"{_short(version)} ({count})"
            for version, count in report.search_config_versions.items()
        )
        print(f"\nsearch families in the pool (fingerprint, experiments): {families}")
    if report.median_n_bars is not None:
        print(
            f"median searched history: {report.median_n_bars} bars "
            "-- descriptive only; ADR-064 matches each null against its own subset below, so a "
            "pool spanning two history cohorts is read against both rather than refused"
        )

    # ADR-060: the leaderboard and the capture reading both treat the selected FAMILY as
    # informative. This says how far ahead of the runner-up it was, on the scale that decides
    # whether that lead means anything.
    separation = report.category_separation
    if separation is not None:
        print("\nwhich KIND of strategy the search selects (ADR-060):")
        for category, sharpe in sorted(separation.medians.items(), key=lambda kv: -kv[1]):
            share = separation.winner_shares.get(category, 0.0)
            print(
                f"  {category:<16} median best-in-category Sharpe {sharpe:+.3f}   wins {share:.0%}"
            )
        if separation.standard_error is None:
            print(
                f"  median lead over the runner-up: {separation.median_gap:+.3f} -- NOT JUDGED: "
                "the pool does not state the history it was searched over"
            )
        else:
            verdict = (
                "separable from noise"
                if separation.separable
                else "INSIDE one standard error -- the family the search picks is not "
                "distinguishable from the runner-up"
            )
            print(
                f"  median lead over the runner-up: {separation.median_gap:+.3f} against a Sharpe "
                f"standard error of {separation.standard_error:.3f} -> {verdict}"
            )

    print("\nout-of-sample Sharpe (compare with data/null_calibration/ — same statistic, no edge):")
    for label, finalists, passers in (
        ("walk-forward", report.walk_forward_finalists, report.walk_forward_graduates),
        ("purged-CV", report.purged_cv_finalists, report.purged_cv_graduates),
    ):
        print(f"  {label:<13} finalists  : {_diagnostic(finalists, finalists)}")
        print(f"  {label:<13} gate passers: {_diagnostic(passers, finalists)}")

    # ADR-054: the gate's verdict is the MARGIN one. This says how often the paper's probability
    # form would have said the same thing about the same finalist — the measurement any future
    # case for switching the gate has to be built on. The reference level is a reading level, not
    # a threshold: nothing gates on it.
    if report.statistic_agreement is not None:
        a = report.statistic_agreement
        print(
            f"\nmargin vs the paper's DSR (reference P > {a.probability_reference:.2f}, "
            f"n={a.n} finalists, median P {a.median_probability:.3f}):"
        )
        print(
            f"  agree: {a.both_pass} both pass, {a.both_fail} both fail | "
            f"disagree: {a.margin_only} margin only, {a.probability_only} probability only "
            f"({(a.margin_only + a.probability_only) / a.n:.1%})"
        )
    else:
        print(
            "\nmargin vs the paper's DSR: not measured — no finalist in the pool carries a "
            "probability (pre-ADR-054 rows)."
        )

    # ADR-051: the comparison itself, not an instruction to go and do it. `comparable` guards it —
    # a difference between runs that resolved different search families, or were judged on
    # different history lengths, is not a finding about the universe, and both have happened here.
    calibrations = [
        NullCalibration.model_validate_json(path.read_text())
        for path in sorted(NULL_CALIBRATION.glob("*.json"))
    ]
    rows = compare_with_null(report, calibrations, experiments)
    if (
        rows
        and all(not row.comparable for row in rows)
        and "legacy-unspecified" in (report.search_config_versions or {})
    ):
        print(
            "\nNOTE: the pool predates ADR-052, so it cannot state the search family it used and "
            "no comparison below is formally valid.\n      It resolves itself after the next "
            "discovery run writes rows that carry the fingerprint."
        )
    if rows:
        print("\nvs the null (finalist window on both sides):")
        for row in rows:
            # ADR-072: `real_below_null_p5` is set only on the centered row, where zero means the
            # same thing on both sides. The raw rows keep ADR-038's one-sided criterion verbatim.
            if row.real_exceeds_null_p95:
                verdict = "SEPARATES"
            elif row.real_below_null_p5:
                verdict = "SEPARATES BELOW (real median < null p5 -- the search subtracts)"
            elif row.statistic == EXCESS_STATISTIC:
                verdict = "does not separate (real median inside the null band)"
            else:
                verdict = "does not separate (real median <= null p95)"
            if not row.comparable:
                verdict = f"NOT COMPARABLE -- {row.mismatch}"
            # ADR-064: the matched history IS the sample the real median was taken over, so it
            # belongs on the same line as the median rather than in a footnote.
            matched = (
                f"{row.matched_n} matched @ {row.matched_n_bars} bars"
                if row.matched_n_bars is not None
                else f"{row.matched_n} matched"
            )
            print(
                f"  {row.statistic:<13} vs {row.null_mode:<14} "
                f"real {row.real_median:+.3f} (n={row.real_n}, {matched}) | "
                f"null median {row.null_median:+.3f} "
                f"p5 {row.null_p5:+.3f} p95 {row.null_p95:+.3f} (n={row.null_n}) "
                f"-- {verdict}"
            )
        if not any(row.statistic == EXCESS_STATISTIC for row in rows):
            # ADR-068: the raw rows above are denominated in each side's own drift. Saying so is
            # the point of the line — a reader who does not see the excess must know it is missing.
            print(
                "  walk-forward excess: NOT MEASURED -- the pool, the null artifacts, or both "
                "predate ADR-068's benchmark; re-search and re-dispatch before reading a lead"
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
