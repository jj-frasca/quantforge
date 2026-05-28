# ADR-007: Vectorized backtesting on pandas/numpy (not vectorbt)

- **Status**: Accepted
- **Date**: 2026-05-28
- **Deciders**: Joe Frasca

## Context
The research engine needs a backtester fast enough for parameter sweeps but only as accurate
as research requires (institutional fill/queue/impact modelling is explicitly out of scope —
ADR-001). The original stack named **vectorbt** for NumPy-vectorized backtesting. Before
committing to it we verified it actually installs on the target toolchain (Python 3.12).

**Finding (2026-05-28):** vectorbt does not install here. `uv run --with vectorbt` fails
resolving/building its dependency chain: vectorbt 1.0.0 → numba 0.65.1 → **llvmlite 0.47.0**,
whose native build fails on this macOS / Python 3.12 environment. This is the
exact risk flagged in ARCHITECTURE.md §0.5 item 6.

## Options Considered
1. **Plain vectorized pandas/numpy backtester (hand-rolled).**
   - Pro: no numba/llvmlite/LLVM build dependency; pandas + numpy are already present
     (transitive via yfinance) and install cleanly on 3.12; full control over the equity-curve
     math; easy to keep the oracle tests honest with closed-form baselines.
   - Con: we write and test the vectorized P&L/portfolio math ourselves (bounded — it's a
     small, well-understood kernel).
2. **vectorbt.**
   - Pro: batteries-included vectorized backtesting and parameter sweeps.
   - Con: does not build here (llvmlite/numba); heavy native toolchain dependency; would block
     the whole research engine on an environment issue. Rejected.
3. **Event-driven backtester.**
   - Pro: most realistic ordering.
   - Con: ~100× slower for sweeps; realism we don't need at research scope (ADR-001). Rejected.

## Decision
Implement a **plain vectorized backtester on pandas/numpy**. Returns are computed by
vectorized operations over aligned price/signal series; transaction costs are applied on
position changes. No numba, no vectorbt.

The buy-and-hold oracle test (ARCHITECTURE.md §8) compares the engine to an **analytic
closed-form** buy-and-hold equity curve derived directly from prices, rather than to vectorbt
(which isn't installed). This is a stronger check — an independent calculation, not another library.

## Consequences
- Backtest engine deps are just pandas + numpy (promoted to direct dependencies in Phase 3).
- The vectorized P&L kernel is ours to test; the §8 oracle tests (buy-and-hold match,
  zero-signal flat, long/short symmetry, monotonic cost impact, SPY-vs-SPY benchmark) guard it.
- If a future need for vectorbt arises and its build situation improves, this can be revisited
  with a new ADR; nothing in the engine's public interface assumes vectorbt.
- Sweeps are vectorized over numpy arrays; good enough for the parameter ranges in scope.
