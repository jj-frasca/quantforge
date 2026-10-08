# ADR-221: Validate power component-count evidence

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Codex autonomous session 19, ISO 2026-W41
- **Resolves:** FINDING-171
- **Extends:** ADR-049, ADR-158, ADR-218

## Context

ADR-049 defines component attribution as counts of successfully searched
finalists, with denominator n_symbols. PowerCalibration freezes but currently
coerces mapping values and accepts negative or above-denominator counts.

## Decision

Validate each original gate_pass_counts value as a nonnegative nonboolean
integer before coercion, using the established count guard. Require every
present count to be at most n_symbols. Sweep reconstruction inherits both
contracts through the authoritative model.

Preserve empty legacy attribution, partial mappings, zero/all-passing counts,
numeric integer scalars, mapping key semantics and JSON shape. Do not infer
missing counts, filter observations or change the component producer.

Known-component count versus composite/joint-verdict reconciliation is a
separate relationship contract. This slice adds no key/completeness policy,
threshold, procedure fingerprint, source, estimator, workflow or data changes.

## Alternatives

Relying on a producer or report check leaves malformed frozen evidence valid.
Casting strings/floats or clamping impossible counts manufactures attribution.
Requiring all six keys would remove existing unmeasured/partial compatibility
without being needed to validate each present count.

## Verification

Observe failing original-value/range tests before code. Verify JSON and unchecked
mapping reconstruction, zero/N integer boundaries, empty/partial/existing key
semantics and unchanged committed-cell round-trips. Obtain independent review
and pass the full foreground delivery gate.

## Reversal

Remove the original-value alias and upper-bound check, restoring acceptance of
coerced or impossible component attribution. Not recommended.
