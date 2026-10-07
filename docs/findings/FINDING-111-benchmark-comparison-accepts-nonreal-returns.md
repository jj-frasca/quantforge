# FINDING-111: Benchmark comparison accepts nonreal returns

- **Date:** 2026-10-07
- **Severity:** High — one comparison mixes incompatible interpretations of input evidence
- **Status:** Resolved by ADR-179

## Evidence

Compare strategy `[0.01+2j, 0.02+3j, 0.03+4j]` with benchmark `[0.01, 0.02, 0.03]`.
The comparator publishes beta approximately 1, alpha approximately 0, relative drawdown 0 and
tracking error approximately 15.8745. Its float conversion discards imaginary components for
validation/drawdown; other operations retain complex inputs before further casts discard them.
Warnings do not prevent publication. Boolean `[True, False, True]` returns are also accepted and
publish annualized alpha approximately 168 against that benchmark. Numeric strings pass float
validation and then raise TypeError during original-Series subtraction instead of the comparator's
ValueError contract. Independent research-expert probes confirm complex and nullable-boolean cases.

## Correction and limits

ADR-179 validates both source dtypes as real nonboolean numeric before inner alignment. Invalid
objects, strings, booleans and complex values are rejected rather than reinterpreted. Complete
nullable numeric input and partial-overlap semantics remain intact; finite/positive-wealth checks
still concern aligned observations only. All estimators and thresholds remain unchanged. This is
a synthetic public-boundary defect, not evidence that committed pool or benchmark records contain
these payloads. Generated data remains untouched.
