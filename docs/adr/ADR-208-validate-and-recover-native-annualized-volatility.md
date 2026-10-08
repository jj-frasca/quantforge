# ADR-208: Validate and recover native annualized volatility

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 15, ISO 2026-W41
- **Resolves:** FINDING-150
- **Extends:** ADR-203

## Context

BacktestMetrics annualized volatility still uses an unguarded native pandas std.
FINDING-150 reproduces finite nonconstant variance underflow as measured zero,
ambient strict exceptions, and exact constants as phantom positive volatility.

## Options considered

1. Retain native measurable scores with exact-constant recognition and normalized
   sample-standard-deviation recovery: selected.
2. Report native zero or infinity on arithmetic failure: invents risk evidence.
3. Replace every native estimator: unnecessarily changes ordinary precision/order.

## Decision

Use one private metric helper validating complete finite real nonboolean source
before short/exact-constant zero. Preserve the original native pandas sample std
then sqrt(252) annualization whenever finite positive and free of detected native
underflow. Catch local FloatingPointError, rather than leaking caller error state.

Otherwise normalize float64 kernel observations by maxabs, compute the same
pandas sample std, annualize that normalized deviation, then restore the positive
scale. Require finite positive recovered volatility, or raise ValueError when
still unmeasurable; no floor or arbitrary risk cap. Empty/singleton and exact
constant samples retain meaningful zero. BacktestMetrics.from_series uses the
helper. API/frontend numeric shapes remain; no thresholds or selector inputs
change. Calibration identity remains v9 because this field is descriptive only.

## Verification and limits

RED Decimal exact-float sample-volatility tests precede code: tiny/subnormal and
partial native underflow, nullable/narrow dtypes, ambient strict/ignore state and
exact constants. Hypothesis scale oracle protects representable volatility;
ordinary native nonconstant precision/order remains exact. Genuine output
unrepresentability fails explicitly. No original engine financial-property domain
changes, generated record edits, calibration dispatch or paid compute.

Finite-result precision and normalized near-constant cancellation remain possible;
this is a concrete recovery/constant correction, not a universal precision proof.

## Reversal

Restore inline native std annualization. This reopens FINDING-150.
