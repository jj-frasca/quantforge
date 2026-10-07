# FINDING-116: Missing rows manufacture Sharpe-interval precision

- **Date:** 2026-10-07
- **Severity:** High — missing evidence creates interval eligibility and precision
- **Status:** Resolved by ADR-183

## Evidence

Independent research-expert reproduction: rng seed 123 normal(0.001,0.01,126) returns have
annualized Sharpe 2.95631033 and correctly return no interval below the one-year minimum.
Append 126 NaNs: the same 126 observations now produce a 95% interval [0.97942570,4.93319496].
Append 882 NaNs instead: the unchanged point estimate gets [1.96786801,3.94475265], half that
width. pandas mean/std skip NaNs while years=len(returns)/252 counts them. Missing evidence alone
crosses the history minimum and manufactures apparent precision.

## Correction and limits

ADR-183 validates complete finite real nonboolean numeric input before sample-length shortcuts.
Confidence-domain validation retains first precedence; finite short histories remain None. The
minimum history and interval formula are unchanged, as are complete nullable/signed samples and
constant-series semantics. This does not establish source cadence or robust dependence coverage.
The public helper defect is not evidence of corrupted generated records; checked engine paths
already provide complete returns. No data or gate threshold changes.
