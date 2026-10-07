# FINDING-120: Sortino invalid evidence and target return zero

- **Date:** 2026-10-07
- **Severity:** Medium — invalid evidence is confused with absent downside
- **Status:** Open — separate source and target boundary review required

## Evidence

sortino_ratio([.01,NaN,-.02]) returns 0.0, as do [.01,inf], [True,False] and the invalid
singleton [NaN]. Its short-history and nonfinite semi-deviation shortcuts hide malformed source
observations. On complete [.01,-.02], target=NaN, +inf or -inf also returns 0.0. The documented
ADR-107 zero convention describes valid short/no-downside samples, not invalid targets/evidence.

## Next action and limits

Specify finite real target and complete finite real nonboolean numeric source contracts before
shortcuts. Preserve finite signed returns, target semantics and full-sample downside denominator.
No gate changes or generated-data changes. Extreme finite semi-deviation arithmetic is separate.
