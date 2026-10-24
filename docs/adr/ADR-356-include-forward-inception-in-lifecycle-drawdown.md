# ADR-356: Include forward inception in lifecycle drawdown

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session 26, ISO 2026-W43
- **Extends:** ADR-020, ADR-025, ADR-073, ADR-110, ADR-168
- **Resolves:** FINDING-296

## Context

Both lifecycle routines build equity from forward returns, then measure drawdown
starting at the first post-return observation. An initial loss disappears from
the peak history. With `[-.35] + [.009, .011] * 50` and a flat benchmark, both
default policies report zero drawdown and hold, despite the initial 35% loss
exceeding their unchanged 25%/30% limits. ADR-110 corrected this accounting
omission in BacktestMetrics, but these lifecycle consumers remain separate.

## Options Considered

1. **Prepend unit wealth to each existing lifecycle equity series.**
   - Pro: includes every forward return using the existing native compounding and
     drawdown formula; preserves source dtype and existing early branches.
   - Con: allocates one additional series and intentionally changes decisions
     whose worst drawdown was hidden by the omitted baseline.
2. **Route lifecycle through BacktestMetrics or log-space reconstruction.**
   - Pro: shares a complete-return accounting path.
   - Con: adds unrelated metrics or changes compounding/rounding/refusal behavior.
3. **Retain the post-first-return baseline and relabel the statistic.**
   - Pro: preserves historical decisions.
   - Con: the existing risk trigger still ignores a loss after forward inception.

## Decision

After each existing lifecycle equity cumprod, prepend a unit-wealth observation
with the same dtype and a fresh positional index before calling max_drawdown.
Retain the exact original compounding, drawdown reduction, rolling windows,
comparisons, policy defaults/hashes, reason strings, input guards, grace and
single-name zero-trade branches. Do not change raw max_drawdown, forward score
curves, broker execution, calibration identities or generated records.

## Consequences

Initial forward losses now participate in the cumulative risk limit, including
when later recovery makes the rolling Sharpe healthy. This can close/retire
future positions under the existing policy; historical decisions and data are
not restated. The extra baseline is internal and adds no persisted forward bar
or fabricated timestamp. It does not repair extreme native cumprod arithmetic,
certify provider evidence, reconcile account-level trades or alter graduation.
Tests must cover default-policy decision changes, exact threshold equality,
later peaks, native dtype preservation, grace/no-trade behavior and independent
bounded wealth-path properties. Required full gates and independent research
review precede publication.

## Reversal

Remove the two baseline prepend statements. This reopens FINDING-296.
