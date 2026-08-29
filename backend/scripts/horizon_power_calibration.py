"""Horizon power calibration driver (ADR-042) — the follow-up ADR-041 named.

Usage: PYTHONPATH=. uv run python scripts/horizon_power_calibration.py [N_SYMBOLS] [SEED]
           [--half-life H] [--deviation-share S] [--out PATH]
       (default: 50 symbols, seed 0, half-life 3 bars, share 0.409, print only)

ADR-041 found the catalog detects 54% of planted TRENDING edges and 6% of mean-reverting ones at
the same effect size, and could not separate two explanations: the mean-reversion family is weak,
or its planted process reverted at lag 1 while RSI-14/Bollinger-20 act over many bars. This plants
band reversion at a STATED half-life instead, so the horizon is the swept parameter.

Read the sweep in two tiers (ADR-042). Half-lives 1-5 at a matched effect size (oracle ~2.6) are the
horizon test. Half-lives 10 and 20 cannot reach that effect size at equity volatility — only
`(1 - rho) / 2` of the deviation's variance is predictable one bar ahead — so a low detection rate
there is a fact about the model's ceiling, not evidence about the catalog.

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

# ADR-051/063: the length a real hunt actually sees, matching the null and ADR-041 power drivers so
# the three stay comparable without an adjustment — defined once in app/research/lab/history.py.
# `--n-bars` overrides it.


def _flag(name: str) -> str | None:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def _report(result: PowerCalibration) -> None:
    print(f"planted process     : {result.edge}")
    print(
        f"reversion half-life : {result.half_life} bars (deviation share {result.deviation_share})"
    )
    print(f"gate config version : {result.gate_config_version}")
    print(f"search config version: {result.search_config_version}")
    print(f"adaptive refinement : {result.refine} (span {result.refine_span:.2f})")
    print(f"symbols searched    : {result.n_symbols}")
    if result.n_bars:
        print(f"bars per symbol     : {median(result.n_bars):.0f} (the hunt's own history length)")
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
            f"oracle Sharpe       : median {pct[0]:+.2f} | p95 {pct[1]:+.2f} | max {pct[2]:+.2f} "
            "(the effect size actually planted, measured not derived)"
        )
    net_pct = result.net_oracle_sharpe_percentiles
    if net_pct is not None:
        print(
            f"oracle NET of costs : median {net_pct[0]:+.2f} | p95 {net_pct[1]:+.2f} | "
            f"max {net_pct[2]:+.2f} (ADR-055: the same 10bp the catalog pays on turnover)"
        )
    capture = result.capture_ratio
    if capture is not None:
        print(
            f"CAPTURE UPPER BOUND : {capture:.1%}  <- median finalist in-sample Sharpe / "
            "median oracle Sharpe (selection-biased)"
        )
    net_capture = result.net_capture_ratio
    if net_capture is not None:
        print(
            f"  net of costs      : {net_capture:.1%}  <- the comparable ratio: both sides now "
            "pay the same costs (ADR-055)"
        )
    # ADR-061: the oracle above knows the process's LATENT deviation. This one is what an optimal
    # causal filter could have formed from prices, which is the only benchmark a strategy could
    # ever have reached — at a one-bar half-life it is essentially zero.
    if result.achievable_oracle_sharpes:
        achievable = median(result.achievable_oracle_sharpes)
        print(
            f"oracle a FILTER could form: {achievable:+.2f} net "
            "(ADR-061: Kalman with true parameters — the recoverable edge)"
        )
    achievable_capture = result.achievable_capture_ratio
    if achievable_capture is not None:
        print(
            f"  capture vs achievable: {achievable_capture:.1%}  <- the honest ratio for a "
            "process whose state is latent"
        )
    elif result.achievable_oracle_sharpes:
        print(
            "  capture vs achievable: REFUSED -- the recoverable edge is inside its own Sharpe "
            "standard error, so there is nothing to express a fraction of"
        )
    if result.errors:
        print(f"unsearchable        : {len(result.errors)} symbol(s)")


def main() -> None:
    out = _flag("--out")
    half_life_flag = _flag("--half-life")
    share_flag = _flag("--deviation-share")
    n_bars_flag = _flag("--n-bars")
    consumed = {out, half_life_flag, share_flag, n_bars_flag} - {None}
    positional = [a for a in sys.argv[1:] if not a.startswith("--") and a not in consumed]

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
        # ADR-061: the same oracle a causal Kalman filter could form from PRICES, which is the
        # honest denominator for a process whose state is latent.
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
