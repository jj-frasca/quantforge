# FINDING-174: Modern null headlines can contradict canonical joint evidence

- **Date:** 2026-10-09
- **Severity:** High — durable Type-I evidence can omit an incumbent false graduate
- **Status:** Corrected by ADR-224
- **Affected:** NullCalibration construction and authoritative merge reconstruction

## Reproduced evidence

Before ADR-224, independent valid-typed synthetic examples passed validation:

1. One complete incumbent joint passer (holdout Sharpe 2, history 252 bars,
   nullable candidate probability) coexists with zero advertised graduates,
   empty graduate list and rate zero. merge_calibrations retains the omitted
   passage rather than rejecting the contradictory input.
2. A correct advertised graduate and joint passer at N=1 accepts zero survivors,
   although strict Sharpe 2 > ADR-018's zero bar yields one survivor.
3. A graduate named UNSEARCHED, with holdout Sharpe -2, can replace the canonical
   passing symbol A and its score 2 while counts/rate remain intrinsically coherent.
4. A genuine incumbent nonpasser can coexist with an advertised graduate.

ADR-215 binds counts to the graduate list and rate; ADR-102 records the complete
joint verdict for every searched symbol. Neither proves that these two stories
agree. ADR-222 already resolves the corresponding power-artifact count gap.

## Scope and compatibility

The committed census found eight null artifacts: two 7,400-bar files contain
400 complete joint records; six retain absent legacy joint evidence. All are
coherent N=200, zero-graduate/zero-survivor measurements and all eight canonical
JSON round-trips pass. This finding is an evidence-boundary defect reproduced
synthetically, not an observed corrupt artifact or new false-positive result.

ADR-224 conditionally binds complete joint evidence to graduate count,
exact passing-symbol membership, graduate locked-holdout score/history, and
strict survival at each passer's own history and the enclosing N. Preserve
absent legacy joints, nullable candidate probabilities and graduate order freedom.
Do not infer unmeasured margins or bind the trial-wide maximum DSR summary to
selected-finalist statistics; those are distinct measurements.

No threshold, gate predicate, source, fingerprint, probability rule, search,
workflow or generated data change is authorized by this finding.


## Correction and TDD evidence

The conditional complete-joint boundary now binds graduate count, passing-symbol
membership, exact graduate holdout projections and strict per-record survival.
Existing count/list equality and complete unique diagnostics make duplicate
or substituted graduates fail; valid graduate ordering is preserved. Empty
legacy joints and None candidate probabilities retain their meanings. Authoritative
merge rejects unchecked contradictory inputs before consolidation.

Before correction, the regression suite observed 19 failures and eight preserved
cases. The tests include direct and JSON construction, hostile unchecked merges,
strict zero-bar equality, mixed holdout histories, native combined-N re-judgment,
legacy absence and an independent own-history Hypothesis count oracle. Selected
margins and trial-wide maxima remain separate, and no missing statistic is inferred.

Verification: 27 focused and 244 affected cases passed. Independent review
passed the new cases plus four native calibration/pairing/joint/merge checks.
All eight committed null artifacts passed parsing, canonical JSON round-trip
and single-shard merge equality; only the NullCalibration executable definition
changed. The initial full gate caught two pre-existing scalar-copy fixture cases that
embedded an incumbent passer while advertising no graduate. Their root now
contains the matching graduate/survivor; original corruption inputs and scalar
rejection assertions are preserved. All 84 final joint/scalar/comparison cases
pass. The fresh full foreground gate passed 3,757 backend and 363 frontend tests;
independent final review approved all six paths, including the fixture correction.
