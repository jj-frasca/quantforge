# FINDING-120: Sortino invalid evidence and target return zero

- **Date:** 2026-10-07
- **Severity:** Medium — invalid evidence is confused with absent downside
- **Status:** Resolved — ADR-187

## Evidence

sortino_ratio([.01,NaN,-.02]) returns 0.0, as do [.01,inf], [True,False] and the invalid
singleton [NaN]. Its short-history and nonfinite semi-deviation shortcuts hide malformed source
observations. On complete [.01,-.02], target=NaN, +inf or -inf also returns 0.0. The documented
ADR-107 zero convention describes valid short/no-downside samples, not invalid targets/evidence.

## Correction and limits

ADR-187 validates the target first as a finite float-representable real nonboolean scalar, then
validates complete finite real nonboolean numeric source evidence before shortcuts. Seventeen
failing source/target cases preceded correction. Independent excess-square oracles protect finite
signed/nullable returns and the full-sample downside denominator; Fraction/numpy scalar target
compatibility is retained.
No gate changes or generated-data changes. Extreme finite semi-deviation arithmetic is separate.
