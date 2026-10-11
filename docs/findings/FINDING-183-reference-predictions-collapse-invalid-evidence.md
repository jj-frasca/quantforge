# FINDING-183: Nonfinite or complex predictions can become reference scores

- **Date:** 2026-10-09
- **Severity:** Medium — invalid conditional-mean evidence can produce finite effect sizes
- **Status:** Corrected by ADR-233
- **Affected:** generic oracle_sharpe_of

## Reproduction

On closes [100,101,100,101,100], a generic all-positive-infinity conditional
mean reports 0.06839665216352; negative infinity reports the negative score.
np.sign maps infinity to a finite position before the derived-return checks.
All 1+1j predictions report 0.04836373655528254 with ComplexWarnings; all 1j
report zero while imaginary components are discarded. All-NaN means deliberately
report zero without warning under the established missing-prediction convention.
Independent research review reproduced these deterministic direct-call defects.
No new searches, random draws, corrupt committed artifacts or revised rates
were observed.

## Proposed boundary

Validate the original prediction Series as real nonboolean numeric evidence;
allow missing means explicitly but require every present value to be finite.
Do not coerce/retype valid input, require complete predictions, alter missing
startup/reindex/sign/cost/native scoring, certify arbitrary prediction causality
or change methods/defaults/thresholds/fingerprints/data. Infinite or complex
expectations cannot establish a finite real conditional-mean claim simply
because sign collapses them. Short-history shortcuts need the same policy.
A separate ADR/TDD/review/full gate must precede any implementation.

## Correction verification

TDD observed 30 failures and 21 preserved cases before the prediction guard.
All 407 parent-focused cases passed. Independent final review approved all
five paths with 550 relevant tests, 14 exact existing AR/band producer
comparisons and six missing/nullable/sparse/unmatched/empty comparisons with
nonmutation checks. Original Series scoring, startup and error precedence
remain intact. Session 31 independently re-reviewed the inherited five paths:
550 focused tests and 49 additional probes passed, including 24 exact AR/band
producer scores. Fresh foreground make check-all passed 4,212 backend tests
(97.65% coverage) and 363 frontend tests (97.63% statements), with lint and
type checks green. No generated records or thresholds changed.
