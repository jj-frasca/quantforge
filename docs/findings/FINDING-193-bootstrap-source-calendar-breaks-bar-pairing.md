# FINDING-193: Bootstrap source calendar can break return/bar pairing

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** Medium — null source identity and marginal preservation
- **Scope:** bootstrap_null source calendar
- **Decision:** ADR-244

## Evidence

A source with index [0, 1, 1, 2] yields three close returns but five geometry
rows through source.loc[returns.index]. With closes [100, 110, 99, 118.8] and
open/close ratios [1, 1.01, 1.02, 1.03], seed 11 draws return position 2 six
times in 20 rows. Those draws receive open/close 1.01 instead of the paired
source bar's 1.03. This violates the source-bar tuple preservation claimed by
ADR-036/037. A reversed unique calendar is also accepted and computes returns
using reversed observation adjacency.

These are synthetic direct-call defects. Production source calendars normally
come from canonical bars; no actual corrupt source, changed Type-I rate or
false graduate is inferred. No real cohort, search or generated data was rerun.

## Correction and verification

ADR-244 specifies unique increasing source identity before return calculation,
without sorting or deleting evidence. The two-predicate guard implements this
boundary after the existing n_bars refusal and before price access or RNG.

Before implementation, the final regression suite observed eight failures and
17 preserved cases. All 25 cases pass after the guard, including exact seeded
paired OHLCV, generic/naive/aware/irregular calendars, caller nonmutation,
empty/singleton refusals and nonidentity Hypothesis permutations. Independent
review approved 180 exact published-baseline DataFrame comparisons across source
dtypes, calendars, seeds, draw lengths and starting prices; patched return/RNG
probes refused malformed sources before either operation. Removing only the
guard restores the published full-module AST.

The full foreground backend/frontend delivery gate is required before shipping.
Source-value and broader geometry contracts remain separate; no calibration
threshold or method identity changes.
