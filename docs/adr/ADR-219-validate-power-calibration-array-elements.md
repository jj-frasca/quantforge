# ADR-219: Validate power-calibration array elements

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Codex autonomous session 19, ISO 2026-W41
- **Resolves:** FINDING-169
- **Extends:** ADR-041, ADR-055, ADR-158, ADR-216, ADR-218

## Context

Valid root counts cannot certify present reference, finalist, category, history
or probability array elements. Power construction and sweep reconstruction retain
nonfinite/coerced scores and invalid history as durable methodology evidence.

## Decision

Use the existing before-coercion element contracts on gross/net/achievable
reference scores, finalist observed scores and category-score lists: finite
float-representable real nonboolean values. Present bar counts are positive
nonboolean integers and holdout years finite and strictly positive. Present
finalist probability elements are original real nonboolean values in [0,1],
with None retained only for this existing nullable measurement.

Reuse null element aliases and probability guards. Preserve signed/zero scores,
numeric scalars, tuple/list parsing, JSON shapes, optional empty arrays and partial
legacy measurements with their existing capture refusal. Sweep reconstruction
inherits these contracts without filtering, clamping, inferred values or new
array-length/relationship checks.

This does not validate process parameters, category keys, component counts,
strategy-name identity or standalone joint-verdict original types. No reference
rule, estimator, search/gate behavior, threshold, methodology fingerprint,
workflow or generated record changes. Active frozen searches retain their
loaded revision and unchanged native procedure attribution.

## Alternatives and limits

Validating only at percentile access leaves durable evidence and capture inputs
unsafe. Filtering invalid values changes the observed population. Requiring
complete arrays would change legacy unmeasured semantics. Other artifact
relationships need separate reproduced findings.

## Verification

Observe RED direct/JSON and unchecked-copy sweep tests first. Protect numeric
scalar types, signed/zero scores, probability None/endpoints, optional empty and
partial arrays. Audit all committed power cells read-only, independently review,
and run affected consumers plus the full foreground gate before delivery.

## Reversal

Restore primitive list element annotations. This reopens FINDING-169 without
changing valid power arithmetic.
