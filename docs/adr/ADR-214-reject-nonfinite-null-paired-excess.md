# ADR-214: Reject nonfinite null paired excess

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Codex autonomous session 17, ISO 2026-W41
- **Resolves:** FINDING-160
- **Extends:** ADR-080, ADR-213

## Context

ADR-213 validates individual finite diagnostic scores. Subtracting two finite
floats can nevertheless overflow; `1e308 - (-1e308)` becomes infinity.
Both authoritative null pairing paths currently pass this derived evidence
to report percentile calculations.

## Decision

Validate every emitted difference in `NullCalibration.paired_excess` using
the existing finite float-representable score guard. Raise `ValueError` for
nonfinite differences in either symbol-paired or complete legacy-array use.
Do not clamp, drop pairs, invent zero/None or change denominators.

Preserve signed/zero finite arithmetic, nullable unmeasured paired diagnostics,
the complete-array legacy guard and existing symbol identity. No threshold,
search procedure, reference arithmetic, fingerprint, workflow or data changes.

## Alternatives and limits

Rejecting large finite operands would impose an arbitrary score threshold and
reject pairs whose difference is representable. Dropping only overflowing pairs
would change the measured population. Checking only inside the report leaves
other callers unsafe; the pairing method owns its output contract.

This is a derived-null-difference contract, not validation of every root scalar,
real-side report difference or subsequent percentile operation. No actual
corrupted committed artifact or wrong published verdict is claimed.

## Verification

Eight test-first cases cover both overflow signs, both OOS diagnostic families
and both pairing schemas. Twelve preserved cases cover negative/zero finite
differences and unmeasured pairs. Review committed artifacts read-only, test
affected consumers and run the full mandatory foreground repository gate.

## Reversal

Remove the finite guards around the two differences; this reopens FINDING-160.
