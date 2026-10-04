# FINDING-098: Direct research datasets accept invalid price frames

- **Date:** 2026-10-04
- **Severity:** High — trusted research input bypasses canonical structural validity
- **Status:** Resolved by ADR-167

## Evidence

Direct `ResearchDataset(frame=..., quality_report=passed_report, ...)` and `dataclasses.replace`
validate report identity and index structure but accept missing/duplicate or MultiIndex columns, NaN/infinite or
nonpositive prices, inverted OHLC, negative volume, nonnumeric object-valued cells, and timestamps
outside the advertised half-open acquisition range. Discovery, forward scoring, panel assembly,
and paper sizing trust this dataset type and its passed report. Some downstream pandas operations
fill or drop missing prices, allowing invalid inputs to change the sample instead of failing here.

TDD regressions construct valid checked data, replace its frame with one malformed intrinsic
attribute at a time, and require rejection at the dataset boundary. Before correction these cases
are accepted. Boundary/property tests preserve close-only inputs, finite valid OHLC, and aware
non-UTC calendars without interpreting them as new provenance.

## Impact and limits

Production adapter preparation already quality-checks canonical PriceBars. This finding concerns
direct construction and injected providers; no committed dataset corruption is demonstrated.
Intrinsic frame validation does not prove a supplied passed report was computed on the supplied
prices. No local guard can reconstruct omitted vendor/adjustment evidence honestly.

## Correction

ADR-167 enforces canonical numeric frame structure, value geometry, and requested-range membership
on the retained snapshot. It rejects rather than repairs invalid observations. No quality heuristic,
methodology threshold, financial formula, or generated record changes.
