# FINDING-204: Cross-sectional returns accept noncausal calendars

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** High — earlier returns consume future price and signal observations
- **Scope:** asset_returns and public portfolio propagation
- **Decision:** ADR-255
- **Prior art:** ADR-176/FINDING-108

## Evidence

Independent positive-price reproduction uses timestamps Jan03, Jan02, Jan04 with
A=[200,100,200] and B=[100,100,100]. The kernel produces A returns [0,-0.5,1]
and portfolio returns [-0.002,-0.504,-1.004]. The Jan02 result uses the Jan03
future price and lagged Jan03 signal. Duplicate Jan02, Jan02, Jan04 timestamps
also produce those finite outputs instead of refusing ambiguous observation identity.

ResearchDataset protects canonical production calendars. These are direct raw-panel
reproductions, not observed corrupt records, real cohort inference or measured false
graduates. No actual search, workflow, broker or generated record was changed.

## Correction and verification

ADR-255 applies ADR-176's unique ascending original-index policy at asset_returns.
Independent pre-code review preserves six exact native ordered-calendar cases and
passes all 227 affected engine/forward/search/IC tests under a scratch wrapper.

Before implementation, 11 calendar-refusal regressions failed while six ordered
calendar preservation cases passed. All 244 affected engine, forward, search and
IC tests pass after the two-line entry guard, including zero-exposure refusal,
Hypothesis source-permutation refusal and existing no-lookahead properties.
Independent final review approves six exact complete native asset-return and 24
portfolio-return comparisons across ordered generic/string/naive/non-UTC-aware,
empty and singleton calendars, missing signals and zero/nonzero costs. Caller
indexes, prices and signals remain unchanged. Removing only the guard restores
the published whole-module AST. The full foreground gate passes
5,156 backend and 363 frontend tests, with 97.78% backend and 97.63%
frontend statement coverage; lint and strict typing pass. No sorting, deduplication, timezone/cadence,
signal, cost or threshold policy changes.
