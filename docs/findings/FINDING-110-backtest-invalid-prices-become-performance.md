# FINDING-110: Invalid backtest prices become performance evidence

- **Date:** 2026-10-07
- **Severity:** High — missing or economically invalid prices produce publishable results
- **Status:** Resolved by ADR-178

## Evidence

Independent synthetic direct-engine reproduction with full-long signals and zero cost:
`[100, NaN, 110]` publishes `[0, 0, 0]` net returns and flat wealth. Missing first or last
observations in `[NaN, 100, 110]` or `[100, 110, NaN]` publish +10% total return. Negative
prices `[-100, -110, -121]` publish +21%. Singleton zero or infinite prices and boolean
prices publish flat results. pct_change's undefined changes become zero through fillna,
including invalid first observations that cannot be detected from later scaled wealth.

## Correction and limits

ADR-178 validates every supplied price before return arithmetic: real nonboolean numeric dtype,
finite and strictly positive values. Object/string/complex payloads are rejected, not coerced.
Complete nullable numeric prices, empty numeric histories, the legitimate first-period zero,
and sparse signal alignment remain supported. No missing prices are filled or removed. This is
an intrinsic direct-input defect, not evidence that a committed generated experiment used these
inputs; production quality lineage remains separate. No data or methodology thresholds change.
