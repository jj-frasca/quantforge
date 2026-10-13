# ADR-279: Preserve narrow excess sample moments in float64

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 6, ISO 2026-W42
- **Resolves:** FINDING-228
- **Prerequisite:** ADR-278

## Context

Against same-dtype zero benchmark, native float16 [1e-6,2e-6,3e-6] and native or
classic masked Float32 [1e-24,2e-24,3e-24] publish information ratio and tracking
error zero despite represented nonconstant excess. Narrow sample variance
underflows before its square root. Large float32 samples instead overflow
variance and decline, although sample standard deviation remains measurable.
ADR-278 first corrected the source benchmark precision mismatch so expanding
excess-moment availability does not retain that known false beta.

Promoting only variance is insufficient: newly measurable excess [A,tiny,-A]
loses its nonzero mean through ordinary narrow summation, and the float32
examples lose it even in float64. Valid original sources [A,tiny,0] and [0,0,A] reproduce this with float16 A256/tiny1e-6 or
float32 A1e20/tiny1e-24; unchanged source alpha stays finite.

## Options considered

1. Float64 sample standard deviation plus stable fsum mean for the original
   narrow excess observations. Preserve the public excess Series.
2. Promote only standard deviation. Introduces false zero information ratio in
   cancellation cases newly accepted by the wider variance path.
3. Replace all comparator moments or subtraction. Unnecessary scope expansion.
4. Clip, floor dispersion or introduce an epsilon. Alters the estimator/evidence.

## Decision

After the exact constant-excess guard, use temporary float64 observations for
native float16/float32 or classic masked Float32 EXCESS only. Calculate sample
standard deviation with ddof1 and mean with math.fsum divided by sample count.
Use these moments in the existing sqrt252 information-ratio/tracking-error
formulas, returning final floats. Original excess dtype/index/name/value ownership
stays intact. Constants bypass all new moments; existing float64/wider/integer
excess paths and beta/alpha/source guards/drawdown remain unchanged.

The affected family intentionally adopts wider rounded moments even where the
old narrow result was finite. No thresholds, calibration identities, schemas,
workflow or generated records change. No epsilon or data substitution.

## Evidence and limits

Independent scope review approved 83 valid public Fraction/Decimal moment oracles
and three valid source cancellation cases. Finite float32 magnitudes are below
2**128 on a 2**-149 grid; at most sys.maxsize observations bound sum magnitudes
below 2**191 and squared sums below 2**321 on a 64-bit platform. Nonzero means
and dispersion remain normal float64 measurable. The float16 range is contained.
This establishes range safety, not exact or correctly rounded arbitrary moments.
Repository RED precedes implementation, followed by independent final review,
full foreground make check-all and exact master CI.

Subtraction already rounded in the original dtype, source means/alpha and
float16/masked-byte-integer compatibility remain separate limits. The entire
comparator need not accept every finite narrow source: original alpha and other
guards can still decline. No historical market contamination is established.

## Reversal

Remove the narrow excess branch/helper and restore the original mean/std path
for this family. This reopens FINDING-228 and keeps ADR-278 source beta correction.
