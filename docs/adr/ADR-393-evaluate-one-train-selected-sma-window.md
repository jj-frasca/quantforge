# ADR-393: Evaluate one train-selected SMA continuation window

- **Status:** Accepted
- **Date:** 2026-10-28
- **Deciders:** Codex autonomous session12, ISO2026-W44
- **Relates:** ADR-048/293/391/392; FINDING-332 remains open

## Context

ADR-392 isolates single-SMA adaptive selection using supplied training prices.
F332 still needs outer evaluation of that adaptive operation. Before designing
an expanding-window summary, compose the selector with one forward realization.
Independent research review approved this bounded contract before adoption;
ADR-392 and its test-oracle portability repair are published and CI-green.

## Options Considered

1. **One unused continuation-window primitive (chosen).**
   - Pro: directly tests the selection and realization information boundaries.
   - Con: no aggregate nested estimator, production integration or calibration.
2. **Full expanding-window evaluation now.**
   - Pro: would provide a complete diagnostic.
   - Con: aggregation, geometry, failure policy and attribution deserve another
     decision; combining them obscures the fundamental boundary tests.
3. **Reuse the full-search realized refined matrix.**
   - Pro: cheaper and already available in production.
   - Con: does not measure train-only adaptive candidate construction (F332).

## Decision

Add unused `evaluate_sma_train_window` beside the ADR-392 selector. Inputs are
caller-declared search-side prices, exclusive positional train_end/test_end and
the selector's explicit settings. Normalize original nonboolean Integral ends
before arithmetic, requiring 1<=train_end<test_end<=len(frame) before engine work.
Materialize only frame.iloc[:test_end] and validate its entire price/calendar/
column domain before selection. Extract ADR-392's unchanged frame validation
into a shared private helper; preserve its selector validation order and rules.

Select using only the train prefix. Reconstruct the winning SMA and run it once
on the used prefix at the selector's normalized cost. Slice its net test returns
afterward. Compute gross holding pct_change on the used prefix before slicing,
so the first test return retains the last training close. Score both slices
with native backtesting.metrics.sharpe_ratio, retaining finite complete sample,
singleton/constant conventions and all native failures. Require both sequences
to contain exactly test_end-train_end observations; no partial result on failure.

Return a frozen primitive dataclass with exclusive endpoints, unchanged frozen
selection trace, tuple net/gross-hold test returns, their two scores and method
`nested-sma-native-metrics-continuation-v1`. Hypotheses equal selection hypotheses;
physical engine calls equal selection calls plus one continuation call. Gross
holding needs no engine call. These are local compute counts, not lifetime/DSR N.

Later test prices cannot affect selection; later post-test rows cannot affect
the complete window result when the materialized prefix (including dtype,
schema and calendar) is identical. A later string assignment may coerce an
entire pandas column and thus change that prefix; no prefix normalization or
arbitrary suffix-mutation immunity is promised. Invalid native-Float64 prices
or calendar defects strictly after test_end are ignored.

## Consequences and verification

This measures one train-selected fixed-config continuation. Internal turnover
costs continue across the boundary; no flat start, switched account, stitched
policy or additional benchmark cost model is claimed (ADR-293). Native metrics
has a distinct identity from production WF's separately guarded Sharpe. No full
run_search/ValidationEngine parity, caller holdout exclusion, source provenance,
PIT availability, improvement, gate or calibration claim follows. No caller,
writer, threshold, fingerprint, v14, generated record or frozen cohort changes.

TDD before implementation: independent native engine/holding oracles; exact
first-test return and turnover; singleton blocks, warmup/ties and active
refinement; selection invariant under test changes and complete-result
invariant under later native-Float64/calendar changes; malformed geometry and
used-prefix data refusal before calls; failure propagation and actual counts.
Use Hypothesis for information-boundary invariants. Preserve original selector
tests, run independent research review and foreground make check-all, then
publish individually with safe synchronization and exact CI verification.

Reversal removes the unused window helper/result/tests and its cold contract;
the unchanged selector can retain its private frame helper. Retain this ADR and
F332 as the decision record. Full nested aggregation remains separate work.
