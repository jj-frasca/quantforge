# ADR-085: Remeasure the panel-null observed statistic on the frozen source

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-021
- **Extends:** ADR-081

## Context

ADR-081 freezes exact source identity for generated null panels, but its real `T_d` is copied from
the retained research pool. Current eligible data contains five searches per symbol over five days
and 131 distinct history lengths from 7,440 to 8,120 rows. Each null panel instead contains one
search per symbol on one exact common 7,400-row calendar. Median-collapsing repeats gives every
symbol equal weight, but it does not make the observed search unit match the null search unit.

The panel source already contains the correct observed sample. A randomization-style comparison
should apply the same statistic once to that observed panel and once to each jointly resampled
panel. No production measurement has run, so the correction can be frozen before seeing an answer.

## Options considered

1. **Keep the pool-derived observed statistic and disclose approximate calendars.**
   - Pro: no additional searches in preparation.
   - Con: leaves history, regime, and repeat aggregation confounded with the panel-null result.
2. **Persist source start/end dates on future experiments and wait for a rebuilt cohort.**
   - Pro: improves general experiment provenance.
   - Con: exact endpoints still would not make five-search medians comparable to one null search,
     and enough retained rows would take days to accumulate.
3. **Select one retained experiment per symbol.**
   - Pro: matches the one-search count.
   - Con: no stored field proves its exact calendar matches the frozen source; choosing among five
     rows also introduces an unnecessary selection rule.
4. **Search the exact observed prepared panel once per symbol.**
   - Pro: makes observed and null arms share the same symbol set, rows, calendar, production policy,
     and code; adds only one panel beside 400 planned null panels.
   - Con: preparation becomes computational rather than fetch-only and must fail before artifact
     creation if any observed primary diagnostic is absent.

## Decision

Choose option 4. The persisted pool determines eligibility only. After preparing the exact common
source panel, the preparation job constructs the same fingerprint-checked production search used by
batch jobs and executes it once on each observed symbol frame. It validates symbol, row count,
search fingerprint, gate fingerprint, and paired walk-forward diagnostic exactly as a null panel
does. Any missing or invalid primary result fails preparation; no post-result symbol filtering is
allowed. Purged-CV remains nullable per symbol under ADR-081/082.

The resulting source-matched `PanelSymbolExcess` values replace the pool-derived values before the
final `PanelNullCohort` is bound and serialized. Increment the diagnostic identity so no pre-change
manifest can be merged or interpreted as this procedure. The observed searches are scratch
measurement inputs only: they are not appended to the research pool and do not write `data/*.json`.

The 7,400-row target, 39-symbol eligible cohort, 30-symbol floor, 400 null replicates, inference,
gate, search policy, and every validation threshold remain unchanged. The workflow remains unspent.

## Consequences

- Observed and null panel statistics are the same function of exact calendar-aligned inputs.
- The artifact's source dates/digest and code revision now identify the data and implementation
  that produced its observed statistic, not only its null replicates.
- Preparation performs one full observed panel search, a 0.25% addition to the planned 400-panel
  null workload.
- Pool values still provide a non-sign-based eligibility boundary but no longer enter inference.

## Reversal

Restoring pool-derived repeat medians would restore FINDING-021 and requires a new ADR before any
measurement. Once an ADR-085 artifact exists, never reinterpret it under the older diagnostic
identity.
