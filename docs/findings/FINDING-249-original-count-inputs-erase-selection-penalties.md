# FINDING-249: Original caller counts can erase trial-selection penalties

- **Status:** Resolved by ADR-295
- **Date:** 2026-10-16
- **Scope:** MinBTL count domain and both public searches' original prior counts

## Public-call evidence

`minbtl_years` checks only `n_trials < 1`, accepting boolean and fractional
counts. True, NumPy boolean and 1.0 can give a zero requirement. With a manually
authored valid report and holdout, GraduationGate propagates that requirement.
This demonstrates a public-call contract failure, not an actual production false
graduate. Ordinary search float priors fail upstream DSR validation, while
boolean priors lose their original type through addition.

`run_search` and `run_cross_sectional_search` lack an original nonnegative
integral prior guard. A negative prior can cancel evaluated hypotheses while
leaving a positive lifetime that passes ADR-190's downstream DSR count guard.
Exactly two bounded deterministic longitudinal calls used the same 800 manually
authored close bars, momentum/n_per_param=2/refine=False and default GateConfig,
without RNG, provider or store access. Both evaluated four concrete configs:

| Original prior | Returned lifetime | DSR selection penalty | MinTRL years |
|---:|---:|---:|---:|
| 0 | 4 | 6.212989165711466 | 0.008002595485372214 |
| -3 | 1 | 0 | 0 |

Both complete Experiment models passed authoritative JSON roundtrip. No
graduation decision, rate, power or calibration inference is reported.
Cross-sectional exposure is established by source inspection and shared pure
repricing; no panel search was run. Neither experiment schema currently binds
lifetime to current evaluated-config counts.

Installed NumPy's fixed-width addition introduces a separate representation
failure at the same boundary: `uint64(MAX) + 4` wraps to 3 before downstream
validation. Normalizing the original count to Python int first gives the exact
18446744073709551619. This scalar check is not a production/search measurement.

Receipts:

- `/tmp/qf-w42-s19-minbtl-count-review.json`, SHA256
  `f20bc8774562956d5df67fda6aa8ce68ce34378bd3c256970ff29e0d00056b55`.
- `/tmp/qf-w42-s19-negative-prior-review.json`, SHA256
  `4d5059d447c4f37a0ed52e2c84f8b21cc7929e20c43c35028e6f4996221fa88b`.

## Recorded consistency and correction boundary

A separate read-only scan of 3,318 committed single-name and cross-sectional
records found no negative/noninteger original lifetime count and no lifetime
below the sum of explicitly recorded current evaluated-config counts. Exactly
3,313 records had explicit current counts; five legacy/empty records could not
support that comparison. This checks recorded consistency, not truth of
historical priors, and does not reconstruct missing historical counts. Input
bytes were unchanged. Receipt: `/tmp/qf-w42-s19-stored-count-audit.json`.

ADR-295 requires original positive nonboolean Integral counts at MinBTL and
nonnegative nonboolean Integral priors at both search entries, before any work.
Accepted integral scalars normalize to Python int before lifetime addition.
Valid Python-count formulas, search/gate fingerprints, v14 calibration with
prior=0 and thresholds remain unchanged. Removing unsafe NumPy scalar wrap is
intentional; universal preservation of formerly accepted NumPy executions is
not claimed. Existing expected-max validation remains unchanged.

Historical schemas, lower-bound counters, generated files and frozen cohorts
are untouched. No production corruption or false graduate is established.
Sharpe overflow/underflow, nonfinite Sharpe, track-record/config guards and
persistence-schema hardening remain outside this correction.

## Verification

Before implementation, public behavioral tests produced 98 failures and 32
preserved controls: malformed count acceptance/type errors, work reached before
invalid-prior refusal, and NumPy maxima wrapping at actual orchestration addition.
Four overflow warnings occurred at the original lifetime-addition lines. No
missing-helper import was used as failure evidence.

All 136 new tests pass after correction. Public stubbed orchestration checks
show exact Python totals at repricing for zero/cumulative/NumPy signed and
unsigned maximum priors in both searches. Invalid priors refuse before frame,
registry or split access. MinBTL tests cover malformed original counts before
nonpositive-Sharpe shortcuts. Financial Hypothesis properties verify monotonic
count penalties and inverse-square Sharpe scaling within a bounded ordinary
domain. The default gate and v14 search hashes remain exact.

The focused suite passed 242 tests, including 106 existing gate, longitudinal,
cross-sectional and accounting regressions with refinement and cumulative priors.
Ruff, formatting and strict typing passed. Independent peer review approved the
source, tests and scientific scope and independently passed all 136 new tests.

Parent AST comparison confirms the three entry functions differ only in their
count guards and named docstrings, plus imports. Gate math/configs/grids,
selection and accounting are unchanged. All 996 other files in the earlier
tracked data/research/validation/data-layer/unit-test baseline remain byte-identical.
Receipt: `/tmp/qf-w42-s19-count-source-guard.json`.
Full foreground `make check-all` passed 11,551 backend tests (97.38% coverage)
and 381 frontend tests (97.66% statement coverage), with lint, formatting and
strict typing green. All verification completed before commit.
Scratch retention is not guaranteed.
