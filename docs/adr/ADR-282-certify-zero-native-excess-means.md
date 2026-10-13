# ADR-282: Certify zero native excess means before reporting zero information ratio

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 8, ISO 2026-W42
- **Resolves:** FINDING-231
- **Extends:** ADR-209's zero-evidence principle; preserves ADR-281 dispersion recovery

## Context

Native float64/classic Float64 strategy [0,1e-100,2] versus benchmark [2,0,0]
has excess [-2,1e-100,2] but publishes IR0. Native sample std2 is measurable
without underflow; ordinary summation loses the positive mean. Original fsum
retains1e-100. ADR-281 deliberately fixes dispersion underflow only and leaves
this native-zero mean outside scope. An initial smallest-subnormal hypothesis
was dismissed: that residual already triggers ADR-281 and correctly reports
IR1.5e-323. No historical contamination is established.

## Alternatives and decision

Certify only zero native means for nonconstant native float64/classic Float64
EXCESS with positive finite native dispersion and without ADR-281 recovery.
Evaluate the original excess mean once. A zero mean requires original math.fsum
zero evidence; true zero retains zero IR. If fsum is nonzero, compute IR from
that original total and the EXISTING measured native std: frexp(total) and
frexp(std), bounded sqrt252*sum_mantissa/std_mantissa/n, then final ldexp.
Refuse sum/range overflow or nonfinite IR. Never use a normalized sum as a zero
certificate. Mantissas stay between .5 and1 in magnitude; for n<=sys.maxsize the
intermediate is bounded, and final ldexp determines representability.

On the common 2**-1074 grid a nonzero exact sum cannot round to zero in fsum;
intermediate overflow must decline rather than invent a zero certificate.
The ratio is the same sample mean/std statistic, with annualization and count
division ordered to retain measurable residuals before final conversion.

Tracking error and existing sample dispersion remain EXACTLY unchanged, even
when the native estimator has its own rounding. Original nonzero native means
retain their original arithmetic/outputs. Exact constants, ADR-281 recovery,
narrow/wider/integer/other excess families, source beta/alpha, drawdown, input
ownership and metadata retain their existing paths. No threshold, calibration
identity, workflow, schema or generated record changes.

Replacing every moment or recomputing std is rejected as unnecessary scope.
Certifying zero using the rounded mean itself or a normalized sum repeats the
loss of evidence. Nonzero native reductions retain their separate precision
limits; this is not universal summation or whole-comparator certification.

## Evidence and limits

Independent scratch approved 360 original Fraction-sum/KNOWN-native-std oracles
across both 64-bit families, n3–100, signs, residual exponents-500..-10 and scales2..1e100;
300 complete outside comparisons stay exact. 36 extreme-range public cases at
scale 5e153 and n100/4096/10000 pass the independent ratio oracle. Draft 61 tests
passed before adoption. Require repository RED before production, independent
final review, foreground make check-all and exact master CI.

The oracle uses existing rounded sqrt252 as an exact Fraction, exact original
sum and the known native std. Normal checks use 1e-12 relative precision;
subnormal range claims at most 1 output ULP with sign/nonzero evidence retained,
following ADR-212. No correctly rounded arbitrary ratio is claimed. Some extreme
public log1p calculations retain their preexisting strict-state limitations.

## Reversal

Remove the zero-mean certification helper and its narrow eligibility branch.
This reopens FINDING-231 and retains ADR-281 dispersion recovery unchanged.
