# ADR-138: Bind cross-sectional panels to quality-checked evidence

- **Status:** Accepted
- **Date:** 2026-09-27
- **Deciders:** Codex autonomous session 28 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-069
- **Extends:** ADR-006, ADR-024, ADR-136, and ADR-137

## Context

A cross-sectional experiment is one claim over a rectangular panel, not a collection of
independent single-name backtests. The production driver currently bypasses the quality gate and
stores only the final column names. ADR-137's `ExperimentManifest` cannot represent the many
quality-report identities that jointly produce one portfolio return series.

## Options Considered

1. **Store a panel manifest with one component per retained symbol.**
   - Pro: represents the actual joint evidence and keeps the durable claim self-contained.
   - Con: introduces a panel-specific lineage schema.
2. **Attach one ordinary experiment manifest per symbol.**
   - Pro: reuses an existing model.
   - Con: falsely describes one panel result as many single-symbol backtests and duplicates shared
     strategy/configuration identity.
3. **Store reports for every requested symbol before panel filtering.**
   - Pro: records the complete acquisition attempt.
   - Con: conflates skipped short-history inputs with the evidence that actually entered the claim.

## Decision

The production cross-sectional hunt accepts only `ResearchDataset` inputs, so each successfully
fetched series has already passed `DataQualityEngine`. After short-history and common-calendar
filtering, persist the complete passed reports for exactly the retained columns plus one frozen
panel manifest. Its ordered components bind symbol, source, adapter version, requested half-open
range, and report UUID; shared fields bind experiment identity and timestamp, executed git
revision, selected strategy and parameter hash, validation-config hash, and the equal-weight
universe benchmark. All retained datasets must name the same executed revision.

Per-symbol fetch or quality failures remain skippable and recorded as hunt errors. The minimum
panel-width rule still fails the run when too little valid evidence survives. Existing and
synthetic `CrossSectionalExperiment` rows retain nullable lineage and are never backfilled.

## Consequences

- Every new production panel claim proves which quality evidence entered each retained column.
- A quality failure cannot enter search merely because frame normalization succeeded.
- Short-history symbols are not misrepresented as contributors to the persisted result.
- The JSON pool grows by the complete reports, trading size for self-contained auditability.

## Reversal

Remove the dataset-only hunt boundary and panel lineage fields. This would restore unchecked,
non-reproducible panel claims and is not recommended.
