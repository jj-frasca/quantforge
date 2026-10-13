# ADR-281: Recover float64 excess dispersion underflow with anchored sample moments

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 8, ISO 2026-W42
- **Resolves:** FINDING-230 (remaining FINDING-113 IR/tracking-error coverage)
- **Extends:** ADR-272, ADR-279; uses ADR-209/212 numerical evidence principles

## Context and alternatives

Native float64 or classic Float64 excess [1e-200,2e-200,3e-200] publishes IR0/TE0
against a zero benchmark, though represented sample risk is positive. Exact
Fraction/Decimal800 gives IR31.74901573277509 and TE1.5874507866387544e-199.
The source beta repairs explicitly left this dispersion problem outside scope.

A naive maxabs-normalized variance recovery is rejected BEFORE implementation:
three nextafter neighbors of1e-200 give IR9.043156280963163e16 and
TE2.786637675724876e-215 versus exact IR1.0944783154858846e17 and
TE2.3024668139553476e-215, about 17–21% error. Scaling original near-constant
levels rounds differences into different observations. Clipping/flooring sigma
changes the estimator; universal moment replacement has unnecessary scope.

## Decision

Only for nonconstant EXCESS dtype native float64 or classic pandas Float64Dtype,
recover a collapsed zero sample dispersion or detected native sample-dispersion
underflow. Preserve original infinite/NaN dispersion refusal: if the underflow
probe raises, recompute under underflow-ignore solely to establish finiteness
before recovery. Positive finite dispersion without detected underflow retains
original mean/IR/TE operation order and values. Exact constants, narrow ADR-279,
native wider ADR-272 and other excess types keep their existing paths.

Recovery subtracts the first original float64 observation, rejects nonfinite
translated differences, normalizes by their positive finite maximum magnitude,
and computes pandas sample std(ddof1) of all translated normalized observations.
Translation preserves tiny near-constant differences before normalization.
Require a positive finite normalized std. No observations are dropped or repaired.

Use original math.fsum, never the normalized sum, to preserve cancellation and
subnormal residuals. Refuse fsum overflow; a true zero total gives IR0. Compute
IR using frexp(original_total) and frexp(delta_scale), dividing by normalized
std and sample count before final ldexp. Restore annualized TE from frexp(scale)
and frexp(normalized_std), multiplying mantissas by existing sqrt252 before
final ldexp. Refuse arithmetic/range failures or nonfinite final scalars.
A final float TE may legitimately round to zero while IR remains nonzero;
never reuse that rounded risk as the IR denominator.

This is the original sample risk and annualization, with bounded intermediate
range. The normalized delta array contains0 and±1 and all values within[-1,1],
so exact sample std lies between1/sqrt(2*(n-1)) andsqrt2. Mantissa calculations
stay bounded for n<=sys.maxsize; final ldexp determines representability.
No epsilon, validation threshold, calibration identity, schema, workflow or
record changes. Source beta/alpha, excess metadata, drawdown and caller state
remain. Global native-zero mean certification is a separate scope, not added.

## Evidence and precision limits

Independent prototype passed 326 Fraction/Decimal800 cases, including native and
masked float64, exponents-1074..-540, signed near-constant neighbors, cancellation,
3/100/4096-row subnormal examples, strict state and delta-overflow refusal.
At4096rows [0]*4095+[smallestsubnormal], TE correctly rounds0 while IR remains
.24803918541230538. Exact midpoint oracle uses Fraction squared statistics with
the existing rounded sqrt252 constant, integerisqrt and ties-to-even (ADR-212).

Pre-code audit found 6 one-output-ULP TE differences among 448subnormal cases in
the proposed property domain; wider audit found 15 among 1,138, maximum 1 ULP.
The broad property therefore claims at most 1 output ULP for subnormal statistics,
with nonzero/sign assertions and original domains retained; selected exact
fixtures remain exact. Normal outputs use 1e-12 relative oracle checks. This is
an explicit tested precision limit, not universal correct rounding or a changed
validation threshold.309 independent midpoint/boundary oracle checks passed.
Require repository RED before implementation, independent final review, complete
native/outside-family preservation, foreground make check-all and exact CI.

Already-rounded subtraction, nonzero native reduction precision, source-alpha
strict-state limitations and original overflowing variance refusal remain.
No historical market contamination is established.

## Reversal

Remove only the float64 underflow probe, dispatch and anchored recovery helper.
This reopens FINDING-230 while preserving other source/excess corrections.
