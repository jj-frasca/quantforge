# FINDING-196: Capture comparison trusts unbound cell identity

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** Medium — mislabeled paired research evidence
- **Scope:** ADR-057 compare_power_sweeps nested identity
- **Decision:** ADR-247
- **Prior art:** FINDING-035 / ADR-103, probability comparator

## Evidence

Independent synthetic direct PowerSweep constructors accepted a cell's process
or gate differing from its header, identical actual searches under apparently
changed search headers, and 7400-versus-9247-bar cells under matched 7400 headers.
Each produced an attributable capture delta of 0.5. Matching the headers does not
establish that the records actually measured the advertised process/procedure.

This is remaining ADR-103 nested-binding coverage at the capture consumer,
separate from the corrected duplicate-key path. It does not establish a corrupt
production artifact, changed calibration rate or false graduate. No real cohort,
search, committed power input or generated artifact was rerun.

## Correction and verification

ADR-247 binds cell edge/gate/search and recorded native median-history summaries
to the sweep header without importing strong-cell completeness. A 14-line consumer
guard checks those claims before endpoint reading, preserving earlier header and
duplicate refusals and normalizing native history-summary overflow to ValueError.

Before implementation, 20 identity regressions failed and nine preservation cases
passed. Independent review approved 69 combined identity/key/delta tests, 120
exact complete published-baseline row comparisons, and 16 additional persisted
or unchecked-copy mismatch probes. Baseline comparisons cover modern, legacy,
partial, mixed, heterogeneous, original 10**310 histories and direct empty states.
The original int(median) contract, including fractional truncation, is retained.

The full foreground backend/frontend delivery gate is required before shipping.
Legacy and descriptive history contracts remain; no attribution, reference or
threshold changes. Producer/schema and embedded-verdict binding remain separate.
