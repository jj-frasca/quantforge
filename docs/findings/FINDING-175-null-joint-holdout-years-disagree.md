# FINDING-175: Null diagnostic years can contradict canonical holdout bars

- **Date:** 2026-10-09
- **Severity:** Medium — durable holdout-history attribution can be false
- **Status:** Corrected by ADR-225
- **Affected:** NullSymbolDiagnostics, enclosing null artifacts and merge

## Evidence

A modern 7,400-bar null record with canonical holdout_n_bars=1480 accepted
holdout_years=100 before ADR-225 when its enclosing list projection is changed to the same
value. Standalone construction and single-shard merge retained the contradiction.
The canonical interval is 1480/252 years, about 5.873 years, not 100.

The producer derives both fields from the same sealed holdout. Finite positive
years and positive integral bars do not establish that equality. ADR-224 now
judges survival from canonical bars, so this remaining metadata gap does not
change its repaired survivor count; it can still misstate history in durable
calibration reporting and consolidation's displayed median-history bar.

All 400 modern joint records in the two committed 7,400-bar null artifacts have
coherent years/bars. Six other artifacts retain absent legacy joints. No corrupt
committed record, new false positive or candidate-comparison result was observed.

## Proposed correction boundary

ADR-225 binds a diagnostic's holdout_years to its present canonical verdict's
holdout_n_bars/252 at the authoritative leaf. Preserve absent verdicts and nullable
probabilities. Do not conflate total n_bars with holdout bars, infer a split fraction,
recompute all root summaries or add power-array/embedded-gate-version policy.
ADR-103 already checks embedded gate versions at the probability consumer boundary.
No threshold, estimator, fingerprint, producer, source or generated-data change.


## Correction and test evidence

The authoritative diagnostic leaf now refuses holdout_years different from its
present canonical holdout_n_bars/252. Legacy absent verdicts remain unconstrained
by unavailable canonical evidence; None candidate probabilities remain valid.
Root and merge reconstruction inherit the guard without rewriting history.

TDD observed 12 failures and eight preserved cases before the correction.
Direct/JSON leaves, enclosing roots and unchecked copies are covered alongside
legacy absence, noninteger-year ratios and an exact Hypothesis projection oracle.
All 321 affected tests passed. Independent review passed 95 cases, including all
20 new cases and native producer/merge checks. All eight committed artifacts
round-trip and single-shard merge unchanged; all 400 modern history projections
agree with their canonical holdout bars. Full foreground `make check-all` passed
3,777 backend tests and 363 frontend tests, including lint, typing and coverage.
