# ADR-248: Reject masked OOS split row identities

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 33, ISO 2026-W41
- **Resolves:** FINDING-197
- **Extends:** ADR-197, ADR-198, ADR-199
- **Relates to:** ADR-038, ADR-039, ADR-200, ADR-202

## Context

The OOS evaluators refuse masked return evidence but materialize caller train/test
indexes with np.asarray before retaining their masks. Missing row identities become
ordinary storage indexes and participate in selection, scoring and reported counts.
A synthetic hidden training row changes the selected configuration; entirely masked
training is also scored. This is split identity, separate from return validity.

## Options Considered

1. Retain original row sources and refuse any true mask before scoring or fold drop.
2. Fill or compress masked indexes. Invents or removes the requested observations.
3. Reject every MaskedArray. Rejects complete all-false-mask evidence by container.

## Decision

In both public evaluators retain the original train/test index sources. After
existing row geometry checks for kept blocks, require no true source mask before
selection, benchmark scoring or OOS scoring. In purged evaluation also check
masked identity before dropping an empty integer fold. Preserve existing matrix,
benchmark, embargo and row-geometry refusal precedence. Raise ValueError rather
than filling, compressing, sorting or choosing masked storage observations.

All-false masks retain exact ordinary-array results. Signed/unsigned integer
indexes, numeric lists, causal gaps, singleton blocks, generated splits and valid
empty purged folds retain existing behavior. No score, selection, aggregation,
embargo, diagnostic default or threshold changes. Canonical complete inputs keep
the current calibration identity; no workflow dispatch or generated data edits.

## Verification and reversal

Observe both evaluators' train/test partial/all-mask failures before code. Assert
refusal precedes scoring and empty-fold dropping, preserve source masks/storage
and exact all-false results, and use Hypothesis over split masks. Independently
review and run the full foreground gate before delivery. Removing original-source
mask checks reopens FINDING-197; return-mask guards alone do not cover this gap.
