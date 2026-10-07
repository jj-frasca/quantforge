# ADR-197: Enforce walk-forward causal row geometry

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 13, ISO 2026-W41
- **Resolves:** FINDING-133
- **Extends:** ADR-038, ADR-068

## Context

The split generator enforces temporal causality but the public evaluator trusts
caller-provided splits. Future/overlapping training rows and negative NumPy row
aliases can produce ordinary finite results labelled walk-forward. Duplicate
rows also change observation weighting under the advertised train/test counts.

## Options Considered

1. Validate caller row geometry at evaluation before selection/scoring.
2. Accept only regenerated default splits. Needlessly removes temporal gaps and
   caller-specified causal windows.
3. Sort, deduplicate or clamp supplied rows. Changes the requested evidence.

## Decision

Keep existing performance-shape, nonempty-splits and benchmark-shape precedence.
For each split, require both arrays to be one-dimensional, nonempty integer rows
(signed or unsigned, excluding boolean). Require every row in `[0,n_obs)`,
strictly increasing unique row order, and the train block to end before the test
block starts. Raise ValueError before selection when geometry is malformed.
Use the existing out-of-range error for either lower or upper bound violations.

Preserve causal gaps, singleton blocks, all generator-produced expanding splits
and earlier test rows legitimately entering later train windows. No training
minimum, new cross-split independence assumption or default split redesign.
Selection, ties, score formula, efficiency and paired benchmark remain unchanged.

## Consequences and limits

Direct evaluator callers cannot label reverse-time or overlapping selection as
causal walk-forward. RED regressions precede code; Hypothesis checks rejection
of overlapping row geometry, and current causal selection invariants remain.
No score estimator, diagnostic default, gate, threshold, calibration identity,
workflow or generated record changes. This validates row geometry only, not
every return-matrix boundary or strategy's signal causality.

## Reversal

Restore upper-bound-only row checks. This reopens FINDING-133 at the evaluator.
