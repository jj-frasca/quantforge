# FINDING-138: PBO variance failures become flat candidates

- **Date:** 2026-10-07
- **Severity:** Medium — finite inputs can produce fabricated CSCV ranks
- **Status:** Resolved — ADR-201

## Evidence

Repeat `[.01, .02, .03, .04]` four times as one candidate and its negative as
another. Four-group CSCV PBO is 0.0. Multiply both columns by the same positive
factor `1e200` or `1e-200`: every observation remains finite, but PBO becomes 1.0.
The candidate ordering and mathematical Sharpe ratios have not changed.

At the large scale, NumPy's squared deviations overflow and sample standard
deviations become infinite. Division by infinity gives zero Sharpe. At the small
scale, those squares underflow and sample standard deviations become zero, so the
guarded division assigns zero Sharpe. Both candidates are now fabricated flat ties.
With NumPy error mode set to raise, the same calls raise FloatingPointError instead
of the validation boundary's ValueError. Finite-input checks alone cannot certify
measurable native moments. This is a synthetic direct-call numerical defect, not
a measured false production graduate.

## Correction and limits

Fail closed on nonfinite derived means/dispersion and on zero dispersion for a
nonconstant column before IS selection or OOS ranking. Identify actual constant
columns from observations and retain their explicit zero score, including huge
finite constants whose unnecessary moment arithmetic would overflow. Require
finite quotients. Local NumPy error handling makes refusal independent of ambient
strict mode. Preserve original arithmetic on representable nonconstant evidence;
do not rescale or introduce a new estimator. Ordinary finite rounding, cancellation
and finite quotient underflow precision remain separate questions.
