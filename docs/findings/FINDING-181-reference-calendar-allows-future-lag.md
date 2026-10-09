# FINDING-181: Unordered reference calendars allow a future AR lag

- **Date:** 2026-10-09
- **Severity:** High for malformed direct calls — future evidence can enter a prediction
- **Status:** Corrected by ADR-231
- **Affected:** shared generic and both AR reference scorer entries

## Reproduction

At ADR-230 revision 815f7a9c, closes [100, 121, 110, 115, 112] indexed
January 1, 3, 2, 4, 5 produce historical/explicit AR Sharpe 16.80845273757858
(phi=-0.3, drift=0, cost=0). January 2's prediction is -0.063, derived from
January 3's +0.21 return: a positional preceding row is later in calendar time.
Generic constant-long scoring returns 4.242843662263942 on the same evidence.
Duplicate dates January 1, 2, 2, 3, 4 also yield those finite scores.

Independent research review reproduced all results. These are deterministic
malformed direct calls, not evidence that production generator calendars or
committed calibrations are corrupt. No searches, random draws, threshold changes
or revised rates are involved.

## Correction boundary

ADR-231 requires unique ascending original source indexes before returns and
short-history shortcuts at the shared helper. Never sort or deduplicate. Keep
ordered generic, naive/aware, empty/singleton histories and native arithmetic.
The source calendar check cannot establish arbitrary supplied prediction-series
causality, acquisition lineage or actual daily cadence.

## Verification

TDD observed 25 failures and 33 preserved cases before the two index checks.
All 229 parent-focused cases passed. Independent review approved all five paths
with 372 relevant tests and 14 exact existing AR/band producer comparisons.
Full foreground `make check-all PYTEST_WORKERS=8` passed: 4,034 backend and
363 frontend tests, with lint, typing and coverage green. No fixture correction
or threshold/default/fingerprint change was needed.
