# ADR-309: Bind holdout verdicts to their binary64 projection

- **Status:** Accepted
- **Date:** 2026-10-17
- **Deciders:** Codex autonomous session 28, ISO 2026-W42
- **Resolves:** FINDING-256 predicate-projection gap
- **Extends:** ADR-160/301

## Context

ADR-301 validates original finite holdout scalars while preserving native
comparisons. FINDING-256 demonstrates a positive exact Fraction that passes the
strict holdout and benchmark predicates but publishes zero Sharpe. Finite float
inspection does not ensure predicate preservation. Conversely, NumPy float32
comparison with a Python-float threshold can round that threshold: native
float32(0.1)>0.1 is false, while its Python-float projection is greater than 0.1.
Simply switching comparisons to floats would change a native verdict.

These are direct accepted numeric inputs, not established production corruption,
a market false graduate or a changed calibration rate. GateResult does not store
the benchmark score or actual threshold, so it alone cannot replay those predicates.

## Options considered

1. Refuse only verdict-changing projections, preserving native comparisons.
   Provides a narrow consumption contract without new thresholds or schemas.
2. Normalize operands before deciding. Changes native comparison semantics,
   including the demonstrated false-to-true NumPy boundary; rejected.
3. Require exact float round trips. Rejects harmless same-side rounding such as
   Fraction(1,3), beyond the demonstrated defect; rejected.
4. Persist exact source scalars and complete comparison evidence. Potentially
   useful, but a much larger schema/provenance change; deferred.

## Decision

Adopt option 1. After existing original-bundle validity and wealth checks, compute
all original gate predicates unchanged. Before reasons or result construction,
compare the native holdout verdict to `float(sharpe)>config.holdout_sharpe_min`
and the native benchmark verdict to the existing short-circuited policy using
`float(sharpe)>float(buy_and_hold_sharpe)`. Refuse any disagreement in either
direction with ValueError, even if another component fails. Do not substitute
projected predicates as the decision. Publish the checked Python-float Sharpe
snapshot so its evidence is the same projection inspected by this guard.

An explicitly disabled benchmark remains inactive: no benchmark-order coherence
restriction is imposed in that mode. Original whole-bundle scalar validation
still applies. Preserve coherent native verdicts, original operands, reasons,
strict comparisons, config fields/hash and thresholds. No epsilon, rounding
repair, nextafter adjustment or exact-representability requirement is added.
This explicitly narrows acceptance of originally valid real inputs whose native
predicates are not preserved in their binary64 projection.

This is a predicate contract while original inputs/config are available, not
standalone GateResult replay or benchmark provenance. Keep count normalization
exact in Python int without a binary64 count cap. Keep the original total-return
wealth predicate and acceptance, including exact return > -1 that rounds to -1;
that scalar is not a GateResult field. Downstream Graduate wealth representability
and other serialization boundaries remain separate. No complete holdout
serialization-coherence claim is made.

No HoldoutScore/score_on_holdout, GateResult/Graduate field, estimator, source,
search/gate threshold, accounting-v14, fingerprint, generated artifact or frozen
cohort changes. No new calibration or source run is authorized.

## Verification and reversal

Observe actual RED before implementation for positive underflow, nonzero-floor
and benchmark equality collapse, both NumPy mismatch directions, and refusal
with another component false. Preserve disabled-benchmark coherence controls,
ordinary scalar families, same-side Fraction rounding, true equalities, signed
zero, nextafter neighbors, original return/count contracts and source nonmutation.
Use independent Hypothesis predicate/projection checks. Intentionally update the
existing F256 witness test to retain its arithmetic witness and require refusal;
do not delete or skip it. Other existing tests remain unchanged.

Compare the 288 pre-change hand-built ordinary GateResult payloads exactly,
independently review source and test scope, run full foreground make check-all,
then individually publish and verify exact master CI. Removing only the guard
and restoring direct source-score publication reverses this acceptance policy
and reopens F256; thresholds and historical artifacts never move.
