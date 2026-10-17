# ADR-310: Add an explicit known-start band-price posterior

- **Status:** Accepted
- **Date:** 2026-10-17
- **Deciders:** Codex autonomous session 28, ISO 2026-W42
- **Extends:** ADR-061/235/236/238/239
- **Relates to:** FINDING-159

## Context

F159's startup audit distinguishes the historical stationary-prior filter from
conditioning under the band's actual zero initialization. Differences alone also
omit information in the first absolute price when the source start price is known.
A future filtered simple-return reference needs both posterior mean and variance,
not merely a substituted sign rule. Replacing the historical filter would silently
change published reference meanings before method/law attribution exists.

## Options considered

1. Add a standalone known-law, full-price posterior helper. Makes the mathematical
   prerequisite testable without changing historical source or reference wiring.
2. Replace filtered_deviation or its initialization in place. Silently restates
   existing references and still lacks production attribution; rejected.
3. Correct simple-return signs using only latent innovation variance. Omits
   posterior uncertainty in the observable reference; rejected.
4. Fit parameters or infer start price from the first close. Changes the assumed
   information set and source law; rejected.

## Decision

Add `band_price_posterior` in the isolated module
`app/research/lab/band_posterior.py`, importing no calibration implementation.
All law inputs `rho`, `level_vol`, `deviation_vol`, `drift`, `start_price` are
explicit required keyword arguments. Return a small named result containing newly
owned float64 arrays `deviation_mean` and `deviation_variance`, one entry per input
observation, without shifts or startup NaNs. No scoring or prediction is performed.

The model is `L[-1]=d[-1]=0`, `L[i]=L[i-1]+drift+eta[i]`,
`d[i]=rho*d[i-1]+epsilon[i]`, `y[i]=log(start_price)+L[i]+d[i]`, with
independent Gaussian innovations of variances `R=level_vol²` and
`q=deviation_vol²*(1-rho²)`. Output index i conditions on every price y[0:i+1].
The supplied start is the pre-shock scale, not the first observed close. No law
or source correspondence is inferred or certified for arbitrary observations.

First assimilate `w=y[0]-log(start_price)-drift` with `S0=q+R`,
`m0=(q/S0)*w`, `p0=(q*R)/S0`. Thereafter, with previous posterior m,p:

```text
z = (y[i]-y[i-1])-drift
S = (rho-1)²*p+q+R
C = rho*(rho-1)*p+q
residual = z-(rho-1)*m
m_new = rho*m+(C/S)*residual
p_new = (q*(p+R)+rho*rho*p*R)/S
```

Fix this operation order for the new binary64 method. The nonnegative variance
numerator equals the predicted covariance determinant; it avoids subtracting
nearly equal variances. Inspect C/gain for finiteness without adding a sign restriction. No clipping,
variance floor, jitter, numerical repair or adaptive fallback is introduced.

Validate original nonboolean finite Real scalars before conversion, original
and normalized ranges `-1<rho<1`, `level_vol>=0`, `deviation_vol>0`,
`start_price>0`, and finite signed drift. Explicitly normalize this new method's
law operands and observations to binary64; no exact-real/wider/native integer
precision guarantee is made. This is a new method, not a change to ADR-238's
historical native-difference arithmetic.

Require an original one-dimensional real numeric NumPy ndarray; refuse sequence,
boolean, string/object, complex, missing/masked or nonfinite evidence before
normalization. Inspect original masks before stripping subclass metadata, then
copy the finite float64 snapshot. All-false masks, noncontiguous and integer
arrays remain supported under the declared binary64 observation contract.
An ndarray cannot certify any coercions already performed by its caller.

Validate derived law arithmetic even for empty input. Require finite positive
deviation variance, q and initial/each residual variance, finite log(start),
state, differences, covariance, gain, numerator and outputs. Positive original
level noise must not become zero through normalization/squaring. For R>0 require
strictly positive posterior variance; zero from underflow refuses rather than
claiming certainty. Genuine R=0 is valid and yields zero posterior variance.
Translate arithmetic failures to ValueError and preserve caller NumPy policy.
Fixed intermediates may conservatively refuse cases whose mathematical final
ratio is representable; finite output is not universal conditioning/accuracy
certification. Underflowed means or signed covariances alone are not refused.

Validate all law/source evidence before output; empty valid input returns two
empty arrays, singleton assimilates the first price. No minimum track record,
tradeability inference, full persistent-claim freezing or calendar inference is
added. Caller mutation cannot change source arrays or another invocation.

Historical calibration.py, filtered_deviation, generators, PlantedEdge, scorers,
measurement/defaults, schemas, CLI/API/UI, search/gate thresholds, accounting-v14,
fingerprints, generated records and all frozen cohorts remain unchanged. F159
remains Open for a separately attributed simple-return reference/production
correction. Even a correct posterior does not establish cost-aware or sample
Sharpe optimality, recoverable-edge bounds or power. No source draw, search,
recalibration or workflow dispatch is authorized by this decision.

## Verification and reversal

Actual RED precedes implementation. Independently condition full finite joint
Gaussian covariance matrices, rather than copying the scalar recurrence; compare
all prefix means and variances. Protect first-price gain 45/67 and initial
assimilation, signed rho/drift, known-start offsets, genuine zero level noise,
empty/singleton, invalid original evidence and arithmetic refusal. Use Hypothesis
for posterior/oracle, causal-prefix and path-independent variance properties.
Check fresh ownership, source nonmutation and NumPy policy preservation.

Precode exact Fraction recurrence/joint-conditioning review matched 96 bounded
prefix cases; it verifies algebra, not the future binary64 implementation. Parent
source audit must show all existing production/test bytes unchanged. Require
focused checks, independent final review, full foreground make check-all,
individual publication and exact master CI. Removing only the standalone module
and its tests reverses this additive component; historical references never move.
