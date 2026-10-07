# ADR-202: Refuse unmeasurable OOS Sharpe moments

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 13, ISO 2026-W41
- **Resolves:** FINDING-140, FINDING-141
- **Extends:** ADR-199, ADR-201, ADR-038, ADR-039, ADR-044

## Context

OOS diagnostic helpers repeat PBO's native variance-as-flat and rounded-constant
defects (FINDING-140/141). Original real complete finite inputs alone cannot certify
the derived moments. Training selection, selected test evidence and controls all
need the same measurability contract.

## Decision

In both scalar Sharpe helpers, retain singleton zero and assign exact constant
blocks zero before moments. For other blocks compute the original one-dimensional
sample standard deviation, mean and annualized score with the original operation
order. Under local overflow, underflow, invalid and divide handling, require
finite mean, finite strictly positive dispersion and finite score; otherwise raise
ValueError. Apply this uniformly to training, selected OOS and benchmark scoring.

Do not rescale moments, drop folds to hide bad evidence, change reselection,
geometry, result aggregation or thresholds. Advance the calibration accounting
identity to `whole-search-budgeted-robust-iqr-pbo-oos-constant-v7` because corrected
constant blocks change finite diagnostics and can change selection. Old identity
cannot match this procedure; replacement distributions remain unmeasured until
authorized sole-writer calibration refresh. No generated data edits or dispatch.

## Verification and limits

RED tests cover nonconstant mean/variance failures in train, selected test and
benchmark blocks under ordinary and strict modes, both public evaluators. Exact
constant, singleton, mixed and nearly constant blocks retain the defined policy;
representable blocks match an independent one-dimensional score oracle. Identity
tests retain historical v5/v6 fingerprints while pinning v7. Ordinary cancellation,
finite quotient underflow and extreme fold-aggregation arithmetic remain separate.

## Reversal

Restore the former guarded sample-Sharpe helpers and v6 accounting identity. This
reopens FINDING-140/141 and restores their historical diagnostic semantics.
