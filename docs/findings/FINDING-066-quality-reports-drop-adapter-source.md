# FINDING-066: Persisted quality reports drop adapter-source identity

- **Severity:** High
- **Status:** Resolved by ADR-135
- **Found:** 2026-09-26, Codex autonomous session 26
- **Affects:** `DataQualityReport`, `DataQualityEngine`, TimescaleDB quality-report storage

## Finding

ADR-118 validates every ingestion batch against the producing adapter source, but the resulting
`DataQualityReport` records only symbol, check time, issues, and pass/fail. Its SQL row has the same
omission. Once persisted separately from the bars, a passing report cannot identify whether it
described yfinance, Alpaca, or another future vendor. An experiment manifest that retains only the
quality-report identifier therefore cannot reconstruct the vendor identity the gate actually
checked.

This is distinct from FINDING-065: source-filtered reads prevent accidental vendor mixing, but they
do not repair the durable evidence record created at ingestion.

## Required correction

Persist the checked adapter source on every new pipeline quality report and its database row.
Legacy/direct reports with no acquisition identity remain explicitly `None`; homogeneous direct
engine calls may derive their single bar source. Mismatched evidence records the expected adapter,
while the issue context retains the disagreeing bar sources. Add a nullable migration for existing
rows; do not infer historical vendors.
