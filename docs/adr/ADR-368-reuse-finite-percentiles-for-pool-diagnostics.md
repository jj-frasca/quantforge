# ADR-368: Reuse finite percentiles for pool diagnostics

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Codex autonomous session31, ISO2026-W43
- **Resolves:** FINDING-308
- **Extends:** ADR-051, ADR-079, ADR-162, ADR-217

## Context

`pool_report._summarize` can turn finite validated Trial diagnostics into an
infinite median or a p95 outside the source range. ADR-217 already supplies the
same native-first numerical recipe for calibration summaries but explicitly did
not adopt it for report consumers.

## Decision

Keep `_summarize`'s values comprehension exactly. Delegate its median, linear
p95, maximum and empty-sample branch to the existing calibration `_percentiles`
helper. Use its returned tuple to populate the existing `DiagnosticSummary`,
retaining `n=len(values)`. Extend the existing calibration import; do not change
the helper or introduce a numerical framework.

This explicitly inherits ADR-217's finite-real nonboolean input guard and local
overflow/invalid handling. Normal validated Trial statistics are builtin finite
floats. Empty/all-missing samples remain None; invalid present evidence refuses
without filtering or inventing observations. This is not full graph validation
of arbitrary unchecked Trial copies.

Finite native summaries retain their exact floating-point answers. Only nonfinite
median/p95 arithmetic uses the helper's exact rational endpoint interpolation
with unchanged binary virtual indexes `(n-1)*0.5` and `(n-1)*0.95`, rounded once
to float. Maximum, caller error policy and inputs remain unchanged.

## Alternatives and limits

Duplicating the interpolation adds another implementation to audit. Clipping or
dropping large scores changes evidence. Normalizing all scores can change native
rounding or lose small terms. Refusing finite representable summaries discards
valid diagnostic information. Reuse adds a private-helper dependency within the
same lab package; the module already imports calibration and no new cycle is
introduced.

The selected-trial population, graduate/finalist distinction, nullable filtering,
counts, schemas, linear estimator, thresholds, search identity, accounting-v14,
generated files and frozen cohorts remain unchanged. Other report reducers,
manual summary construction and finite-native precision remain separate scopes.
No affected production record, engine output or gate verdict is established.

## Reversal

Restore the native numerical suffix and remove the helper import from
`pool_report`. This reopens FINDING-308; calibration behavior remains unchanged.
