# ADR-225: Bind modern null diagnostic holdout years to canonical bars

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Codex autonomous session 21, ISO 2026-W41
- **Resolves:** FINDING-175
- **Extends:** ADR-080, ADR-102, ADR-158, ADR-213, ADR-224

## Context

A null diagnostic with present joint evidence accepts any finite positive
holdout_years independently of the canonical holdout_n_bars. Root projection
agreement and modern graduate reconciliation do not bind these two histories.
Native calibration derives them from the same sealed holdout; all 400 committed
modern records currently agree. The defect is independently reproduced.

## Decision

At NullSymbolDiagnostics validation, when calibration_verdict is present, require
holdout_years exactly equal to calibration_verdict.holdout_n_bars / 252, using the
existing daily annualization constant. Refuse contradictory attribution rather
than overwriting either measurement. Existing authoritative nested reconstruction
and merge inherit the leaf guard.

Keep absent legacy verdicts and nullable probabilities. This establishes no total
n_bars versus holdout-bars relationship, split-fraction policy, root summary/bar
recomputation, power-array relationship or new embedded-gate-version boundary.
No source, scorer, gate predicate, threshold, fingerprint, workflow, JSON shape or
generated-data changes.

## Alternatives and limits

Root-only validation leaves standalone diagnostics unsafe. Tolerance permits
contradictory exact producer projections without a measurement-error rationale.
Inferring history or requiring joints on old artifacts invents missing evidence.
Broader provenance/summary contracts require separate reproduced findings.

## Verification

Observe direct/JSON and unchecked root/merge failures before code. Protect exact
noninteger-year ratios, nullable probabilities, absent legacy verdicts and a
Hypothesis history projection invariant. Read-only round-trip all eight committed
artifacts and independently review native producer agreement; run affected
consumers and the full foreground gate before individual delivery.

## Reversal

Remove the conditional leaf relationship guard; false history attribution becomes
acceptable again without changing valid calibration arithmetic.
