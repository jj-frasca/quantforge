# FINDING-102: Overflow can hide benchmark-relative drawdown

- **Date:** 2026-10-04
- **Severity:** Medium — valid-domain numerical stress can erase relative risk
- **Status:** Resolved by ADR-171

## Evidence

For 2,000 observations of +50% in both series followed by strategy -20% / benchmark +20%,
`BenchmarkComparator.compare` reports benchmark-relative drawdown 0.0. The independent oracle is
`0.8 / 1.2 - 1 = -1/3`: every preceding relative wealth value is exactly one. Both standalone
compound paths overflow, their ratio becomes NaN, and pandas' minimum skips the unobserved tail.
Every input is finite and greater than -1, within ADR-112's public comparator domain.

## Impact and limits

The defect understates relative drawdown under a reproducible synthetic stress path. It does not
show a committed experiment is wrong or that ordinary market prices reach this condition. The
backtest engine has additional absolute-wealth guards, so the standalone comparator's broad domain
does not imply every such path can reach an API result. Other scalar statistics are not audited by
this finding.

## Correction

ADR-171 evaluates the same relative-wealth definition using cumulative log differences and running
log peaks, with the pre-return baseline retained. Tests reproduce overflow/underflow prefixes and
compare moderate paths to an independent product-ratio oracle. No data or threshold changes.
