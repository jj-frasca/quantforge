# FINDING-117: Standalone Sharpe accepts invalid return evidence

- **Date:** 2026-10-07
- **Severity:** Medium — a public helper silently reinterprets malformed evidence
- **Status:** Open — separate direct-helper boundary review required

## Evidence

Research-expert reproduction: sharpe_ratio([0.01,NaN]) returns zero; boolean
[True,False,True,False] returns approximately 13.747727. Complex
[0.01+1j,0.02+2j,0.03+1j,0.04+2j] returns approximately 0.687215 with a cast warning.
The primitive skips missingness or loses imaginary evidence rather than enforcing real numeric
complete returns. ADR-183 validates the interval wrapper only, not this public helper.

## Next action and limits

Audit direct Sharpe consumers and specify source validity before its short/constant shortcuts,
using failing tests first. Preserve complete finite signed samples and existing zero-variance
conventions; no missing-row repair, threshold change or estimator redesign. Checked engine search
paths already provide complete returns. No production or generated-data correction is claimed here.
