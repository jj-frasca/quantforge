# ADR-363: Bind direct panel lifecycle evaluation to frozen columns

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session30, ISO2026-W43
- **Resolves:** FINDING-303
- **Extends:** ADR-025, ADR-140, ADR-149, ADR-168, ADR-252

## Context

Direct scoring checks exact ordered panel columns against the frozen universe
under ADR-252. Direct lifecycle evaluation omits that check and reconstructs both
factor and benchmark on any supplied universe. A deterministic eight-row example
holds on the complete frozen panel but retires on a subset under the same position
and policy. Managed calls already check identity before invoking either helper.

## Options considered

1. Apply the existing scorer's exact ordered-column guard to direct evaluation.
   This protects every lifecycle branch with one cheap comparison and preserves
   the matching-panel implementation.
2. Rely on the manager or the scorer. Direct evaluation remains callable without
   either boundary and can issue a verdict for a different frozen factor.
3. Reorder, subset or fill the panel automatically. This transforms evidence and
   can change ordered-universe tie handling or invent missing prices.

## Decision

After existing policy revalidation, before calendar access and no-forward returns,
require `list(panel.columns) == list(position.universe_symbols)` in
`evaluate_cross_sectional_lifecycle`. Mismatches raise `ValueError` with the
existing scorer's message. Preserve the remainder of the function exactly.

Do not normalize labels, reorder columns, fill data, change static maps or invent
an alternative tie policy. Exact matching panels retain their existing returns,
benchmark, lifecycle thresholds/defaults, grace branches, reasons and decisions.
Calendar/price validity, complete position reconstruction and no-forward source
validation remain separate policies; this decision does not expand them.

## Consequences and reversal

Direct scoring and lifecycle evaluation bind the same frozen ordered universe,
including when no forward bars exist. A manager call repeats a cheap identity
check; its acquisition and fail-soft behavior remain unchanged. No estimator,
schema, threshold, policy hash, longitudinal accounting-v14, generated record,
broker action or frozen calibration changes. The witness demonstrates a direct
synthetic defect, without establishing an affected actual book or graduate.

Remove only the new lifecycle column guard to reverse this decision and reopen
FINDING-303.
