# FINDING-171: Power component counts accept impossible evidence

- **Date:** 2026-10-08
- **Severity:** High — component attribution validity
- **Status:** Resolved by ADR-221
- **Reproduced revision:** `ca6befde`

PowerCalibration accepts gate_pass_counts values True, False, string "1",
float 1.0, negative counts and values above n_symbols. These become frozen
component attribution and survive authoritative sweep reconstruction, despite
ADR-049 defining each count over successfully searched finalists with denominator
n_symbols. An impossible component count can misstate the gate bottleneck even
when the headline detection rate is coherent.

Independent review reproduced six malformed cases at N=2. All 72 component
entries across 12 committed power cells already satisfy original integer [0,N]
contracts. This is a synthetic durable-evidence defect, not an observed corrupt
committed artifact, wrong gate decision or reason to relax a threshold.

ADR-221 reuses original nonnegative integer validation and enforces the searched
denominator ceiling. Empty/partial mappings, existing keys and numeric integer
scalars remain supported. Composite/joint reconciliation and new key policy are
outside this slice. No threshold, estimator, fingerprint, source, sample,
workflow, generated data or component producer changes.

## Correction and verification

The pre-code baseline had 54 failing rejection cases and six preserved cases.
All 150 focused component/root/joint cases pass after correction. Independent
final review approved the complete slice, ran 119 relevant tests and confirmed
all 12 committed power cells / 72 component entries validate and round-trip
unchanged. Zero/N, numeric integer scalars, empty/partial/unknown-key mappings,
JSON and unchecked-copy reconstruction are covered. Full foreground delivery
verification is recorded in the session state; no generated record changes.
