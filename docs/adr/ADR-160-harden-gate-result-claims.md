# ADR-160: Harden deterministic gate-result claims

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 26 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-092
- **Extends:** ADR-015, ADR-016, ADR-102, ADR-147, and ADR-159

## Context

`GateResult` is the persisted statement of QuantForge's deterministic graduation decision. Its
`frozen=True` configuration is shallow, and its scalar fields are independently accepted: mutable
reasons can change after validation, `passed` can disagree with its component vector, and invalid
required-length, configuration-identity, or holdout-pair values can be serialized as a claim.
Outer artifacts protect many current persistence paths, but the shared result remains unsafe before
attachment and at direct consumers.

A read-only scan of committed JSON found 4,055 gate-result occurrences and no incompatibilities
with the stronger invariants below.

## Decision

`GateResult` will defensively copy its reasons into an immutable JSON-array-compatible container and
validate its claim at construction. `passed` must equal the conjunction of `dsr_ok`, `pbo_ok`,
`stability_ok`, `mintrl_ok`, `holdout_ok`, and `beats_buy_and_hold_ok`. The required track-record
length must be non-negative and not NaN, while positive infinity remains valid because ADR-015's
MinTRL is infinite for a non-positive Sharpe. The gate configuration version must be non-empty, and
structured holdout Sharpe and bar count must be present together or absent together for legacy
records.

Calibration's probability-DSR counterfactual boundary will reconstruct each supplied gate result
before inference, so an unchecked Pydantic copy cannot change the incumbent or candidate verdict.
This decision changes no component predicate, threshold, reason wording, MinTRL formula, candidate
probability rule, workflow, or generated data.

## Alternatives considered

1. **Rely on outer experiment/calibration freezing.** Rejected: direct construction and consumers
   still expose an incoherent shared claim before or without attachment.
2. **Compute `passed` as a property and remove the field.** Rejected: that changes the persisted
   schema and historical payload shape.
3. **Reject infinity.** Rejected: positive infinity is ADR-015's intentional MinTRL result for a
   non-positive observed Sharpe, not missing or invalid evidence.

## Consequences

- One gate result cannot drift after validation or disagree with its component vector.
- Legacy records may still omit both structured holdout fields; new evaluator results retain both.
- Counterfactual calibration fails closed on unchecked copies.
- All 4,055 committed gate-result occurrences remain compatible.

## Reversal

Restore a mutable reasons list or independent unvalidated verdict fields. That reopens FINDING-092.
