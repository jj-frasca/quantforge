# FINDING-096: Research dataset frames can drift after quality checks

- **Date:** 2026-10-04
- **Severity:** High — acquisition evidence can describe different prices from those scored
- **Status:** Resolved by ADR-165

## Evidence

`ResearchDataset` is a frozen dataclass with a mutable public DataFrame field. Direct construction
retains the caller's frame. Mutating that source, `dataset.frame.loc`, its numpy values, or its
DatetimeIndex backing array changes later research inputs while `dataset.evidence()` retains the
same quality-report UUID and acquisition identity. Production acquisition creates its own frame,
but any consumer can still mutate the public frame before another consumer scores it.

Deterministic regressions exercise source and exposed-frame price, calendar, column, and metadata
edits and assert the original snapshot remains available. Before correction those assertions fail.
A plain `DataFrame.copy(deep=True)` also shares index storage, so both axes require explicit copies.

## Impact and limits

Single-name discovery, cross-sectional panel assembly, forward lifecycle scoring, and paper sizing
consume this boundary. A mutation can disconnect derived evidence from the checked observations.
No claim is made that a committed generated record was affected; there is no audit trail for prior
in-process edits. This is an ownership defect, not proof the quality heuristics certify data truth.
Direct construction with fabricated passed evidence and arbitrary object-valued cells remain
separate concerns; canonical acquisition supplies numeric OHLCV from checked PriceBars.

## Correction

ADR-165 captures a private snapshot and returns independent working copies with independent axes.
Constructor and dataclass replacement behavior stay compatible. No methodology threshold,
financial statistic, generated JSON, or acquisition behavior changes.
