"""Horizon power calibration driver (ADR-042) — the follow-up ADR-041 named.

Usage: PYTHONPATH=. uv run python scripts/horizon_power_calibration.py [N_SYMBOLS] [SEED]
           [--half-life H] [--deviation-share S] [--out PATH]
       (default: 50 symbols, seed 0, half-life 3 bars, share 0.409, print only)

Historically, ADR-041 reported 54% detection of planted TRENDING controls and 6% of
mean-reverting controls at the same reported reference score. It could not separate
weak mean-reversion-family performance from a horizon mismatch: lag-1 reversion
versus RSI-14/Bollinger-20. This driver plants band reversion at a STATED half-life.

ADR-042's historical horizon comparison used half-lives 1-5 with a matched reported
reference score (~2.6). Longer half-lives change the stationary predictable fraction
of deviation-component log-return variance, `(1 - rho) / 2`. This is not a finite-
sample simple-return variance or Sharpe bound. Low detection must be interpreted
under the stated source and reference conventions; it establishes neither a
strategy ceiling nor a bound on catalog power.

Expensive (one full search per symbol) and NEVER in CI; writes no pooled data — a synthetic symbol
is not a hypothesis about a real one.
"""

import sys
from pathlib import Path
from statistics import median

from app.research.backtesting.engine import DEFAULT_COST_RATE
from app.research.lab.calibration import (
    PowerCalibration,
    mean_reverting_edge,
    measure_power,
    oracle_sharpe_of,
)
from app.research.lab.history import CALIBRATION_N_BARS
from app.research.strategies.catalog import STRATEGY_CATALOG

# ADR-051/063: shared synthetic calibration length from app/research/lab/history.py.
# Actual hunt histories can differ; comparisons require matched recorded history.
# `--n-bars` overrides it.


def _flag(name: str) -> str | None:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def _report(result: PowerCalibration) -> None:
    print(
        f"planted process     : {result.edge}\n"
        "reference convention: historical driver uses log-mean signs scored on simple returns; "
        "supplied method/source law not recorded\n"
        "reference limits    : filter startup/posterior not certified; "
        "no cost-aware optimum, sample maximum or no-edge conclusion (FINDING-159)"
    )
    print(
        f"reversion half-life : {result.half_life} bars (deviation share {result.deviation_share})"
    )
    print(f"gate config version : {result.gate_config_version}")
    print(f"search config version: {result.search_config_version}")
    print(f"adaptive refinement : {result.refine} (span {result.refine_span:.2f})")
    print(f"symbols searched    : {result.n_symbols}")
    if result.n_bars:
        print(f"bars per symbol     : {median(result.n_bars):.0f} (supplied synthetic history)")
    print(f"detected            : {result.n_detected}")
    print(f"DETECTION RATE      : {result.detection_rate:.1%}  <- power of the gate as such")
    if result.gate_pass_counts:
        passes = " | ".join(
            f"{name} {count}/{result.n_symbols}" for name, count in result.gate_pass_counts.items()
        )
        print(f"gate component pass : {passes}")
    print(
        f"clear ADR-018 bar   : {result.n_clear_deflation_bar} (bar {result.deflation_bar:.2f})"
        "  <- power against the standard we actually hold to"
    )
    pct = result.oracle_sharpe_percentiles
    if pct is not None:
        print(
            f"latent reference gross: median {pct[0]:+.2f} | p95 {pct[1]:+.2f} | max {pct[2]:+.2f} "
            "(realized gross sign-reference strategy score)"
        )
    net_pct = result.net_oracle_sharpe_percentiles
    if net_pct is not None:
        print(
            f"latent reference net: median {net_pct[0]:+.2f} | p95 {net_pct[1]:+.2f} | "
            f"max {net_pct[2]:+.2f} (ADR-055: the same 10bp the catalog pays on turnover)"
        )
    capture = result.capture_ratio
    if capture is not None:
        print(
            f"capture vs gross reference: {capture:.1%}  <- median finalist in-sample Sharpe / "
            "median gross latent reference Sharpe (selection-biased)"
        )
    net_capture = result.net_capture_ratio
    if net_capture is not None:
        print(
            f"  net of costs      : {net_capture:.1%}  <- selected in-sample finalist / "
            "net latent reference; both sides "
            "pay the same costs (ADR-055)"
        )
    # ADR-061: compare the specified historical price-based filtered log-mean sign rule.
    # Its net score does not certify the posterior or bound all causal strategies (F159).
    if result.achievable_oracle_sharpes:
        achievable = median(result.achievable_oracle_sharpes)
        print(
            f"filtered reference net: {achievable:+.2f} "
            "(ADR-061: specified historical filtered log-mean sign rule)"
        )
    achievable_capture = result.achievable_capture_ratio
    if achievable_capture is not None:
        print(
            f"  capture vs filtered reference: {achievable_capture:.1%}  <- selected in-sample "
            "finalist / specified filtered net reference"
        )
    elif result.achievable_oracle_sharpes:
        print(
            "  capture vs filtered reference: REFUSED under existing evidence/denominator "
            "requirements; this does not establish absence of tradeable edge"
        )
    if result.errors:
        print(f"unsearchable        : {len(result.errors)} symbol(s)")


def main() -> None:
    out = _flag("--out")
    half_life_flag = _flag("--half-life")
    share_flag = _flag("--deviation-share")
    n_bars_flag = _flag("--n-bars")
    value_options = {"--out", "--half-life", "--deviation-share", "--n-bars"}
    consumed_positions = {
        i + 1 for i, arg in enumerate(sys.argv[1:], start=1) if arg in value_options
    }
    positional = [
        arg
        for i, arg in enumerate(sys.argv[1:], start=1)
        if not arg.startswith("--") and i not in consumed_positions
    ]

    n_symbols = int(positional[0]) if positional else 50
    seed = int(positional[1]) if len(positional) > 1 else 0
    half_life = float(half_life_flag) if half_life_flag else 3.0
    share = float(share_flag) if share_flag else 0.409
    n_bars = int(n_bars_flag) if n_bars_flag else CALIBRATION_N_BARS

    planted = {
        f"BAND{i:04d}": mean_reverting_edge(
            n_bars, seed=seed + i, half_life=half_life, deviation_share=share
        )
        for i in range(n_symbols)
    }
    strategies = [entry.name for entry in STRATEGY_CATALOG]
    print(
        f"measuring power against {n_symbols} band-reverting symbols x {n_bars} bars over "
        f"{len(strategies)} strategies (half-life {half_life} bars, deviation share {share}, "
        f"seed {seed})...\n"
    )
    result = measure_power(
        {name: p.frame for name, p in planted.items()},
        strategies,
        oracle_sharpes={
            name: oracle_sharpe_of(p.frame, p.conditional_mean) for name, p in planted.items()
        },
        net_oracle_sharpes={
            name: oracle_sharpe_of(p.frame, p.conditional_mean, cost_rate=DEFAULT_COST_RATE)
            for name, p in planted.items()
        },
        # ADR-061: historical price-based filtered log-mean sign reference, net of costs.
        # This specified rule does not certify a recoverable-edge bound (FINDING-159).
        achievable_oracle_sharpes={
            name: oracle_sharpe_of(
                p.frame, p.achievable_conditional_mean, cost_rate=DEFAULT_COST_RATE
            )
            for name, p in planted.items()
        },
        edge="band_reversion",
        half_life=half_life,
        deviation_share=share,
    )
    _report(result)

    if out:
        Path(out).write_text(result.model_dump_json(indent=2) + "\n")
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
