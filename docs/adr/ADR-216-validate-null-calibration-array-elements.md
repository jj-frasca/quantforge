# ADR-216: Validate null-calibration array elements

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Codex autonomous session 17, ISO 2026-W41
- **Resolves:** FINDING-165
- **Extends:** ADR-037, ADR-067, ADR-080, ADR-158, ADR-213, ADR-215

## Context

Root scalar and canonical-leaf guards do not protect legacy arrays. Nonfinite
diagnostic scores and invalid/coerced history values survive construction and
merge, reaching percentile or matched-history consumers as apparent evidence.

## Decision

Validate each present null-array element before Pydantic coercion using the
same intrinsic contracts as canonical leaves: scores are finite real nonboolean
numbers; bar counts are positive nonboolean integers; holdout years are finite
and strictly positive. Share the holdout-years guard with the canonical leaf.
Element annotations preserve container parsing and JSON array shapes.

Do not clamp/drop elements, invent missing values or change denominators.
Signed/zero finite scores and supported numeric scalars remain valid. Empty
optional arrays remain unmeasured. Partial legacy arrays retain their raw
diagnostic use and existing complete-array excess-pairing refusal. Existing
canonical projection validation and defensive merge reconstruction inherit
the element guards.

## Alternatives and limits

Validating only canonical diagnostics leaves historical-schema inputs unsafe.
Requiring all arrays to be complete would change legacy missing-measurement
semantics. Filtering bad values silently changes the measured population.

This validates present elements, not a new length/nonempty contract, maximum or
deflation-bar recomputation, or every subsequent arithmetic operation. It does
not certify power-array elements or percentile overflow. No statistic, threshold,
methodology fingerprint, workflow or generated artifact changes.

## Verification

Observe original-value/JSON and unchecked-copy merge failures before the patch.
Protect signed/zero numeric scores, positive numpy history, Fraction years,
tuple parsing, empty unmeasured and partial unpairable legacy arrays. Read all
committed null artifacts without writes, review independently and run affected
consumers plus the mandatory full foreground gate before delivery.

## Reversal

Restore unguarded primitive list annotations and the duplicated leaf-years body;
this reopens FINDING-165 without changing valid calibration arithmetic.
