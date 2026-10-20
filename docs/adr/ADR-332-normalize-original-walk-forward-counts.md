# ADR-332: Normalize original walk-forward counts before geometry

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Codex autonomous session 8, ISO 2026-W43
- **Resolves:** FINDING-279
- **Extends:** ADR-038/197/295/330

## Context

The public walk-forward splitter trusts count annotations at runtime. A
fractional min_train=2.5 makes integer arange endpoints overlap training and
test rows. Bounded unsigned counts also wrap K+1 or the final room check,
producing empty/out-of-range folds. The ADR-197 evaluator refuses those rows;
no accepted leaky score, affected production record or false graduate is
established. The splitter still owes its own documented causal row contract.

## Options Considered

1. Reuse original nonboolean Integral validation and Python-int normalization.
   Preserves legitimate NumPy counts and native geometry, but tightens malformed
   input acceptance and error types.
2. Reject all non-Python ints. Simpler but excludes equivalent integral counts.
3. Trust downstream rejection. No code change, but direct splitter consumers
   continue receiving invalid expanding-window geometry.

## Decision

Use require_trial_count(minimum=0) for n_splits immediately before its existing
>=1 check, and n_obs immediately before its existing N>=K+1 check. Validate and
normalize explicit min_train after that relational check and before fold/base
arithmetic; None remains untouched and still chooses the computed fold size.
Retain all existing checks, formulas, slices, defaults and remainder behavior.
K must normalize before K+1; each optional base must normalize before the
final-room multiplication/addition. Do not round fractional counts or repair rows.

## Consequences and limits

Original boolean, fractional, string, complex, array and negative counts refuse
with ValueError. K0/N0/explicit base0 retain their established geometry errors
after original domain validation. Signed/unsigned Integral counts use exact
Python arithmetic; formerly wrapped executions deliberately change or refuse.
No new allocation cap is introduced for N/K; the existing observation-sized
arrays remain. Native Python counts, singleton forward windows, explicit early
training starts, expanding reuse of earlier test rows and the final remainder
remain valid. This guards row geometry, not strategy causality, provenance,
switching-account execution or feature-support assumptions.

Scoring, selection, thresholds, accounting-v14, stored evidence and frozen
cohorts remain. Normal search observations and requested default splits are
native integers; no new calibration or historical relabeling follows.

## Verification and reversal

Observe fractional and bounded unsigned failures before runtime edits.
Hypothesis checks exact integer geometry and causal row order across count
families, defaults and explicit starts. Lock malformed-domain rejection and
existing check precedence. Preserve 4,202 frozen valid Python geometry payloads
and the prior module AST except one import, three guarded assignments and the
splitter docstring. Independent review, foreground make check-all, individual
push and exact CI are required. Remove these guards to reverse, reopening
FINDING-279 while retaining its written evidence.
