# FINDING-117: Standalone Sharpe accepts invalid return evidence

- **Date:** 2026-10-07
- **Severity:** Medium — a public helper silently reinterprets malformed evidence
- **Status:** Resolved — ADR-185

## Evidence

Research-expert reproduction: sharpe_ratio([0.01,NaN]) returns zero; boolean
[True,False,True,False] returns approximately 13.747727. Complex
[0.01+1j,0.02+2j,0.03+1j,0.04+2j] returns approximately 0.687215 with a cast warning.
The primitive skips missingness or loses imaginary evidence rather than enforcing real numeric
complete returns. ADR-183 validates the interval wrapper only, not this public helper.

## Correction and limits

ADR-185 reuses the complete finite real nonboolean numeric validator before standalone Sharpe
shortcuts. Thirteen failing malformed-source and missing-padding cases preceded the correction.
Valid numeric empty/singleton/constant, nullable numeric and finite signed samples retain native
scores. Direct consumer review found no intended invalid-source contract. No missing-row repair,
threshold change, estimator redesign or generated-data modification. Extreme finite arithmetic
remains a separate limitation.
