# FINDING-236: Level-scaled volatility recovery erases tiny represented dispersion

- **Status:** Corrected by ADR-287
- **Date:** 2026-10-13
- **Scope:** Descriptive annualized volatility, original native/classic Float64

## Reproduction

For signs +/-1 and n=3,4,7, construct
`sign * (1e-200 + arange(n) * ulp(1e-200))`, as native or classic nullable
Float64. Public BacktestMetrics.from_series accepts annualized volatility
2.786637675724876e-215, 3.2177320244274214e-215 and 5.526636244048101e-215.
Exact centered Fraction variance and agreeing Decimal 200/800 targets are
2.3024668139553476e-215, 2.9724718752147705e-215 and 4.973896795977967e-215.
Errors are respectively 21.0284%, 8.2511% and 11.1128% high. Twelve signed/dtype
cases are complete, finite, nonconstant accepted false risk measurements.

Native variance underflows. Recovery scales levels before centering, erasing
original represented near-equal spacing. ADR-208 expressly left nearconstant
precision unresolved; ADR-286 corrected the separate scorer, not this field.

## Correction and limits

ADR-287 anchors represented differences only for finite failed original Float64
STD. Ordinary native results, nonfinite STD, annualization-only failure and other
source families retain previous behavior. Positive subnormal risk remains valid;
nonconstant final rounded zero still refuses under ADR-208. Subnormal control
cases permit one output ULP, certified against exact squared midpoints; universal
correct rounding is not established.

This descriptive field does not change trial accounting: v11 stays and calibration
remains unmeasured. Historical v10 frozen cohorts remain attributed and untouched.
No threshold or generated record changes; no actual false graduation or market
contamination is established.

## Evidence

Independent scratch scope approved twelve public reproductions, 180 Fraction/
Decimal oracles, 22 exact midpoint checks, 306 exact baseline cases and 79 draft
plus 235 unchanged volatility/engine tests. Repository Ruff passed. Genuine
public baseline RED and production verification will be recorded separately.

Session 11 resumed the three interrupted documentation/test paths before sync.
Fresh public baseline observed 38 failures and 41 preserved controls: 36 literal
nearconstant measurements, the Hypothesis property and the missing-helper routing
contract. Four explicit finite/nonfinite STD-underflow provenance cases were added
before production; final baseline observed 42 failures and 41 preserved controls.
Only then was anchored recovery implemented. All 420 focused new/existing
volatility, engine and anchored-Sharpe tests passed.

Independent final review approved 83 new tests, 300 exact original-HEAD comparisons
for ordinary/outside-family/nonfinite-STD paths, 120 Fraction/Decimal 200/800
nearconstant checks, 22 exact subnormal midpoint controls and eight complete
public other-field comparisons. AST comparison certified all other production
functions/classes and the original level-scaled fallback unchanged. Caller source
and NumPy error state were preserved. The full foreground `make check-all` passed
10,870 backend tests (97.44% coverage) and 363 frontend tests (97.63% statements),
with Ruff lint/format and strict mypy, ESLint and TypeScript checks green.
