# ADR-174: Validate Monte Carlo risk return evidence

- **Status:** Accepted
- **Date:** 2026-10-05
- **Deciders:** Codex autonomous session 1, ISO 2026-W41
- **Resolves:** FINDING-106
- **Extends:** ADR-173, ADR-014 Phase 0

## Context

The risk estimator silently drops missing observations and accepts booleans and returns at or
below -1. Its finite GBM-path guard cannot detect incomplete history or repair return evidence
incompatible with positive multiplicative wealth.

## Options Considered

1. Reject malformed return observations before estimating moments. This makes the measured
   sample explicit while preserving complete valid inputs.
2. Keep dropping missing rows. This computes a different history with no declared missing-data rule.
3. Fill, coerce, or clip observations. This invents returns or changes the supplied wealth history.

## Decision

Require a real, nonboolean numeric pandas return Series with at least two observations, all finite
and strictly greater than -1. Complete nullable numeric dtypes are supported. Missing values raise
rather than being dropped. Use the original complete Series for the unchanged annualized mean and
sample-standard-deviation formulas, seeded GBM simulation, probabilities and percentiles. No
calendar/timezone requirement is added; generic ordered or other existing index types remain valid.

## Consequences and limits

Undefined observations cannot become apparently measured risk. This introduces a deliberate
ValueError for formerly permissive invalid direct inputs, matching the simulator's fail-closed
policy. Finite negative returns above -1 and constant/zero series remain supported. No loss
threshold, estimator, generated record, broker action, workflow, or API schema changes.
Input validity does not establish iid returns, predictive power, or stable extreme moment arithmetic.

## Reversal

Restore dropna and permissive dtype/value acceptance. This reopens FINDING-106.
