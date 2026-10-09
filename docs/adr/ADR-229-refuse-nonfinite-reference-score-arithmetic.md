# ADR-229: Refuse nonfinite derived reference-score arithmetic

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Codex autonomous session 21, ISO 2026-W41
- **Resolves:** FINDING-179
- **Extends:** ADR-042, ADR-055, ADR-213, ADR-223

## Context

On ordinary deterministic positive prices, finite cost_rate=1e200 produces a
false negative zero Sharpe when sample variance overflows. At 1e308, turnover
cost overflows and yields NaN. Both shared oracle_sharpe_of and its historical
and explicit-drift AR wrappers inherit these results. Finite original inputs
alone do not establish finite derived evidence. Independent dimensionless
arithmetic establishes the defect, not a new optimality or market claim.

## Decision

The shared reference scorer refuses nonfinite derived net returns before they
can be dropped, nonfinite sample standard deviation or mean, and a nonfinite
annualized score. Preserve the same sign/lag/startup/turnover convention, native
sample ddof=1, annualization and ordinary finite arithmetic. Short observed
histories and genuine finite zero-variance returns retain their zero result.

Do not scale, clip, filter, replace or impute overflowed observations. Stable
alternative estimators require their own decision. Do not expand original
scalar validation policies, change cost defaults, fit drift, replace historical
reference methods, relabel artifacts, alter thresholds/fingerprints or write data.

## Alternatives and limits

A final-score-only finite check misses a finite false zero from infinite sample
standard deviation. An AR-wrapper-only guard leaves the shared and historical
reference entry points unsafe. A blanket maximum cost rate rejects representable
arithmetic without testing the actual derived evidence. A scaled fallback could
be mathematically sensible but changes numerical scoring beyond this refusal.

## Verification

Observe deterministic generic, historical and explicit-drift AR failures before
code. Protect exact ordinary gross/net values, finite zero variance, missing
conditional-mean startup and short histories. Cover net-return, variance and
final-score overflow. Independently verify source-only normal-case references,
existing affected consumers and the full foreground gate before delivery.

## Reversal

Remove the derived finite guards; overflow can again become NaN or a false zero
reference score without changing ordinary valid arithmetic.
