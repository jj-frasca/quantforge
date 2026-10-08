# ADR-217: Recover nonfinite calibration percentiles

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Codex autonomous session 19, ISO 2026-W41
- **Resolves:** FINDING-166
- **Extends:** ADR-036, ADR-039, ADR-041, ADR-053, ADR-055, ADR-216

## Context

The shared null/power percentile helper can publish infinity from finite scores.
NumPy's median sum overflows for equal large scores; its linear-percentile
endpoint subtraction overflows for opposite signs. Every exact quantile is a
convex combination of finite endpoints and is representable in their range.

## Decision

Validate present summary inputs as finite real nonboolean float-representable
scores, preserving empty-input None. Compute the existing native median, linear
p95 and maximum with local overflow/invalid handling independent of caller state.
Preserve each finite native result exactly. Only a nonfinite median or p95
uses exact rational interpolation of the sorted float endpoints, rounded once
back to float. The virtual index remains `(n - 1) * 0.95`, including the existing
binary weight; the median index remains `(n - 1) * 0.5`.

Do not filter, clamp, replace evidence, or change the quantile estimator. Invalid
source values raise ValueError. This input guard protects the summary boundary;
it is not a new durable power-array construction contract. No search/gate behavior,
threshold, reference strategy, calibration fingerprint, workflow or generated
record changes.

## Alternatives and limits

Failing closed is honest but unnecessarily refuses valid representable summaries.
Global normalization can alter ordinary native rounding. Long-double recovery
varies by platform. Rational endpoint fallback costs little for two quantiles
and preserves native finite answers; it does not certify their universal accuracy.
Other capture ratios, report percentiles and root claims remain separate boundaries.

## Verification

Observe RED signed equal-pair, opposite-sign interpolation and maximum-float
cases under ignore/warn/raise NumPy states. Protect all four public summary
properties, ordinary exact native results, singleton/empty inputs, invalid
sources, and Hypothesis finite extreme convex bounds with a rational oracle.
Read committed null/power summaries without writing data, independently review,
and run the full foreground gate before delivery.

## Reversal

Restore the unguarded native helper. This reopens FINDING-166 without changing
any production search or gate result.
