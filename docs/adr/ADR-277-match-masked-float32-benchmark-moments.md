# ADR-277: Match masked Float32 benchmark variance to covariance precision

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 6, ISO 2026-W42
- **Resolves:** FINDING-226
- **Extends:** ADR-268, ADR-269, ADR-270

## Context

Classic masked Float32 neighbors of .1 compared to themselves publish beta0.4
and annual alpha15.120002746582031 instead of beta1/alpha0. Exact native constant
detection correctly observes variation. Installed masked variance uses np.var on
float32 arrays, while Series.cov explicitly extracts float64 arrays; native
variance remains positive, so existing underflow recovery preserves the wrong
ratio. Plain float32/float16 controls on this fixture remain beta1/alpha0.

## Options considered

1. Promote only a classic masked Float32 benchmark to plain float64 for native
   variance, matching the covariance path that already uses float64. Use matched
   plain float64 arrays if existing underflow recovery fires on that branch.
2. Replace covariance only. Wrong side: numerator is already float64, and the
   masked denominator narrows independently.
3. Add a new anchored float64 moment helper or rewrite every source path. Broader
   operation/compatibility change than the demonstrated denominator defect needs.
4. Treat finite native beta as accurate. Preserves a demonstrated neutrality error.

## Decision

Keep original source/alignment guards and exact constant detection first. Existing
integer and genuine native wider beta branches take precedence. In the remaining
native branch, only classic pandas Float32Dtype benchmarks use a temporary plain
float64 Series for sample variance. Retain original Series.cov, which already
extracts float64 observations; preserve the original Float32 source and metadata.

If ADR-268's existing underflow recovery is required for such a benchmark, build
both normalized strategy and benchmark Series from the original aligned float64
arrays divided by their original scales. This prevents normalized masked Float32
variance from repeating the mismatch. Keep the existing normalized covariance/
variance, scale restoration and validation. Do not compute new unused moments;
np.cov's existing unused strategy variance can still trigger recovery.

Every other benchmark dtype and all constant/wider/integer branches retain their
original paths. Beta may change family-wide for masked Float32 benchmarks; alpha
naturally uses corrected beta through its original formula. Original means,
excess/IR/TE/drawdown, metadata, source guards and caller state stay. No threshold,
calibration identity, workflow, generated record or schema changes.

## Evidence and limits

Independent scratch: 420 original Fraction beta oracles across 21 partner dtypes,
n3,4,7,16,128 and origins .1/.5/1/-.1; tiny strategy and Float32 subnormal benchmark
recovery; installed pandas source confirms precision mismatch. A temporary public
prototype passed all 446 proposed tests, including self-neutrality, state and
ownership. Repository RED must still be observed before production. Add meaningful
Hypothesis affine invariants, constants/guards/missing/overlap and full outside-path
preservation, independent final review, foreground make check-all and exact master CI.

Source float32 means/excess/dispersion, original float64 centering, large integer
partner covariance and very uneven normalization retain separate limits. Tiny
public tests use caller-ignore because unchanged alpha/mean arithmetic has no
whole-comparator strict-state guarantee. This corrects matched precision, not
universal accuracy or historical market contamination.

## Reversal

Restore original masked benchmark variance and original normalized operands for
that branch. This reopens FINDING-226 without affecting other dtype paths.
