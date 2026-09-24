# ADR-123: Clamp Monte Carlo paths to a strictly-positive floor

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 104
- **Resolves:** FINDING-051

## Context

`MonteCarloSimulator.simulate` documents and ARCHITECTURE.md §8 requires that every GBM path value
is strictly positive. That is true in exact arithmetic but not in float64: a sufficiently extreme
`sigma` (unbounded above by validation) over a realistic horizon (e.g. 252 steps) drives the true
compounded value below float64's smallest representable double for a real fraction of paths, and
`np.cumprod` floors those to exactly `0.0`. This was confirmed to be genuine mathematical underflow,
not a fixable precision-order artifact of `cumprod` specifically (a log-space cumulative-sum
reformulation rescues under 0.1% of the affected entries in the reproduction case — the rest are
below `log(5e-324)`, unrepresentable by any float64 regardless of computation order).

## Options Considered

1. **Clamp the returned `paths` array to `np.finfo(np.float64).tiny` (the smallest positive
   representable double).**
   - Pro: makes the documented invariant true by construction for any input that already passes
     the function's own validation (`s0 > 0`, `sigma >= 0`), with one line. Statistically
     indistinguishable from the unclamped result for every downstream consumer — `analyze_strategy_
     risk`'s `terminal_return`/`max_drawdown_per_path` already read `-1.0` (not `NaN`) for an exact
     `0.0` path value; a `~5e-324` floor changes that to `-0.999...994` differing from `-1.0` in a
     digit no `loss_threshold in (0, 1]` comparison or percentile statistic can distinguish.
   - Con: doesn't change the fact that the underlying model has degenerated to "essentially all
     wealth lost" at this parameter regime — but that is the honest description of what GBM at
     4000%+ annualized vol over a year actually implies, not something to paper over further.
2. **Reformulate `simulate` in log-space (cumsum of log-returns, single `exp()` at the end) instead
   of clamping.**
   - Con: measured above to rescue under 0.1% of the affected entries in the reproduction case — the
     rest are genuinely below the smallest representable double regardless of computation order, so
     this alone does not make the invariant hold; it would still need a clamp on top.
3. **Add an upper bound on `sigma` and reject anything beyond it.**
   - Con: an arbitrary ceiling with no principled value to pick, and `analyze_strategy_risk`'s
     sigma is derived from realized data, not chosen by a caller — rejecting it converts a
     reporting nuance into a hard failure for a caller who has no obvious remediation.

Chose option 1: smallest possible diff, makes the invariant genuinely true rather than documented-
but-false, and has no observable effect on any existing consumer's statistics.

## Decision

`simulate()`'s return statement changes from `return paths` to
`return np.maximum(paths, np.finfo(np.float64).tiny)`. No change to the validation, drift/diffusion
math, or shape contract.

## Consequences

- `MonteCarloSimulator.simulate`'s strict-positivity invariant (ARCHITECTURE.md §8 #8) now holds by
  construction for the function's full validated input domain, not just the range the existing
  Hypothesis test happened to cover.
- No observable change to `analyze_strategy_risk`'s reported statistics (`prob_terminal_loss`,
  `prob_max_drawdown_exceeds`, percentiles) — a path that previously read exactly `0.0` now reads
  `~5e-324`, a difference no `(0, 1]`-scale threshold or percentile can register.
- Any future direct consumer of raw path values (e.g. `np.log(paths)`) is now safe from a
  `-inf`/divide-by-zero on an extreme-but-valid input.

## Reversal

Revert to `return paths`. Not recommended — reintroduces FINDING-051's silently-false invariant at
extreme (if unrealistic) sigma.
