# ADR-220: Validate joint-calibration original scalar evidence

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Codex autonomous session 19, ISO 2026-W41
- **Resolves:** FINDING-170
- **Extends:** ADR-102, ADR-103, ADR-213, ADR-219

## Context

The canonical joint calibration record still accepts coerced probability,
locked-holdout score and history evidence. Matching a legitimate incumbent
projection does not validate the original scalar. An exact probability outside
[0,1] can round into the interval before its current field constraints run.

## Decision

Reuse existing before-coercion guards on CalibrationSymbolVerdict's three
measurement fields: nullable original finite real nonboolean probability in
[0,1], finite float-representable real nonboolean holdout score, and positive
nonboolean integer holdout bar count. Preserve current field constraints and
exact equality with both embedded GateResult holdout projections.

Preserve None as an unmeasured probability, signed/zero scores, ordinary numeric
scalars, JSON shapes and absent legacy joint records. Authoritative null/power
reconstruction inherits the guards without imputing, filtering or clamping.
GateResult's scalar policy is outside this slice; no new symbol policy, root or
component reconciliation is introduced. The strict probability >0.95 rule,
ADR-102 eligibility/decision criteria, thresholds, estimators, search/gate
fingerprints, workflows, sources and generated artifacts remain unchanged.

## Alternatives

Relying on projection equality is insufficient: coercion can make malformed
originals match legitimate incumbent evidence. Consumer-only guards leave the
standalone canonical record invalid. Reuse of established guards keeps one
original-value contract without changing the gate's statistical procedure.

## Verification

Observe failures before code. Verify standalone and JSON rejection, exact bounds
before rounding, nullable/threshold endpoints, signed numeric scalars, projection
mismatches and unchecked nested reconstruction. Independently census committed
joint records and round-trip artifacts unchanged, review the complete slice and
run the full foreground delivery gate.

## Reversal

Remove the three before-coercion validators. This restores acceptance of coerced
or originally out-of-range canonical evidence and is not recommended.
