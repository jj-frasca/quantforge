# ADR-198: Bind purged evaluation to embargo geometry

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 13, ISO 2026-W41
- **Resolves:** FINDING-134
- **Extends:** ADR-039, ADR-078, ADR-197

## Context

Purged evaluation can record a requested embargo without verifying that caller
train/test rows implement it. Overlap and negative aliases can yield finite OOS
diagnostics even though test data participated in selection. The normal split
generator is honest; the public evaluator needs its own row-identity boundary.

## Options Considered

1. Validate embargo identity, fold rows and the actual excluded interval.
2. Trust the generator by convention. Direct callers remain unprotected.
3. Rebuild supplied folds with a different embargo. Changes requested evidence.

## Decision

Keep existing performance/split-list/benchmark-shape precedence. Before scoring,
require nonnegative nonboolean numbers.Integral embargo, normalized to int.
Require one-dimensional signed/unsigned integer row arrays, nonnegative in-range
unique ascending rows. Empty integer arrays remain droppable without a score.
For kept folds require contiguous test rows and no train row in the closed
interval `[first_test - embargo, last_test + embargo]`. Compute endpoints with
Python ints to avoid unsigned wraparound. Reject malformed geometry with
ValueError without sorting, deduplicating, shrinking embargo or rebuilding rows.

Preserve singleton test blocks and training before and after the excluded
interval; purged CV remains intentionally noncausal. Keep selection, aggregation,
fold dropping, paired benchmark, split-generator defaults and lookback sizing.
The existing dropped-fold and kept-fold benchmark fixtures are enlarged to
respect their unchanged 100-bar embargo; assertions and thresholds remain intact.

## Consequences and limits

Reported embargo now describes the actual evaluated rows. RED cases precede
implementation and guard inclusive endpoints, source identity, negative aliases,
unsigned order, and input shape. Generated-split properties and accepted
before/after training protect existing semantics. No estimator, threshold,
calibration identity, workflow or generated data changes. Return-matrix evidence
validity is separate; these guards do not assert causal purged training.

## Reversal

Remove row/embargo checks and restore the impossible benchmark fixture. This
reopens FINDING-134 at the evaluator; the generator remains correctly purged.
