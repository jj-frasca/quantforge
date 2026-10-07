# ADR-192: Validate PSR original scalar evidence

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-127
- **Extends:** ADR-054, ADR-190

## Context

PSR accepts fractional history and nonfinite/boolean Sharpe or moment evidence while producing
ordinary probabilities. Probability DSR delegates to PSR and inherits the boundary. Production
whole-search accounting supplies measured finite scalar inputs and catches ValueError as unmeasured.
The existing minimum-history check needs to remain first; raw-kurtosis and variance restrictions
are outside this source-validity correction.

## Options Considered

1. Validate original count/scalars at PSR entry before the existing formula checks.
2. Validate only probability DSR. Leaves direct PSR and future consumers unprotected.
3. Clamp/repair malformed scalars. Invents scores, distribution shape or observed history.

## Decision

Require n_returns to be a nonboolean numbers.Integral count >=2, then normalize to Python int.
Validate this first, preserving minimum-history precedence. Require observed_sr, benchmark_sr,
skew and raw kurtosis to be finite float-representable nonboolean numbers.Real scalars, normalized
to float, before the original variance/formula checks. Reject malformed evidence with ValueError.

Keep the existing raw-kurtosis restriction, positive variance guard, native PSR standard error,
normal CDF, per-period units and probability DSR delegation unchanged. Source inputs are not
repaired and no new scalar rate bounds apply. Gates, calibration identity and thresholds remain.

## Consequences and limits

Malformed source evidence cannot create an ordinary measured probability. RED tests cover count
and each scalar, precedence and wrapper propagation; existing normal-standard-error, equality,
skewness and history properties protect the estimator. Valid signed scores/benchmarks, numpy
integral/real and Fraction scalars remain supported. Probability accounting retains its existing
ValueError-to-unmeasured policy. Extreme finite formula arithmetic and margin-form observed-source
validity are separate questions; this source boundary does not claim to fix them. No generated
data, workflow or paid-service changes.

## Reversal

Remove the original-source checks. This reopens FINDING-127.
