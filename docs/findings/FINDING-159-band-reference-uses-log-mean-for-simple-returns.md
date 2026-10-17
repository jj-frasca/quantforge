# FINDING-159: Band reference uses log mean for simple returns

- **Date:** 2026-10-08
- **Severity:** High — reference optimality and power interpretation
- **Status:** Open
- **Reviewed implementation:** `bb3ef2e0`; unchanged at `1c319fdf`

## Reproduction and derivation

ADR-042's generator constructs `close = 100 * exp(level + deviation)`.
Conditional on the previous latent deviation `d`, its next log return is
Gaussian with mean `m = drift + (rho - 1) * d` and variance
`v = level_vol**2 + deviation_vol**2 * (1 - rho**2)`.
The generator's `conditional_mean` stores `m`. `oracle_sharpe_of` takes its
sign, but scores `close.pct_change()`, which is a simple return.

The exact conditional mean of that simple return is `expm1(m + v / 2)`.
Its sign differs from the stored reference for `-v / 2 < m < 0`.
With half-life 1, deviation share 0.5, total volatility 0.012, drift
0.0003 and previous deviation 0.00065, `rho = 0.5`, `v = 0.000126`,
`m = -0.000025`, and the conditional simple mean is approximately
`+0.000038000722`. The historical reference shorts a positive conditional
simple-return mean.

An independent NumPy reconstruction used 4,096 bars with those generator
parameters and seeds 2026100800, 2026100801 and 2026100802. It reproduced
the production conditional log-mean series exactly and found respectively
38, 17 and 19 opposing signs among each seed's 4,095 usable predictions.
These are source-only sign checks, not search trials or power estimates.
Root and independent research review both reproduced the issue.

## Consequences and scope

Historical gross/net band scores remain scores of the implemented reference
strategy. They do not establish a conditional simple-mean benchmark, a
cost-aware optimum, a sample maximum, or an upper bound on causal strategies.
ADR-061's observable reference uses the same log-mean sign convention.
If its Gaussian filtered posterior is correct, the predictive log variance
also includes `(rho - 1)**2 * posterior_deviation_variance`; substituting
only the latent innovation variance would not correct that reference.
This finding does not certify the filter's initialization or posterior.

Claims that near-zero observable net reference scores prove no recoverable
edge, or that every graduation would necessarily be wrong, need qualification.
No change to search outcomes, detector counts, or historical measured scores
is asserted. This is distinct from FINDING-155's AR drift-intercept omission.

A future governed correction needs test-first simple-return conditional-mean
and predictive-variance contracts, review of filter initialization, explicit
methodology attribution and its own ADR. This report changes no generator,
reference implementation, threshold, calibration identity or data artifact.

The session17 UI follow-up labels band columns as latent/filtered references,
explains the log/simple-return mismatch and removes the optimal-filter/entire-
edge claim. This qualifies display interpretation; the mathematical reference
correction and filter initialization review remain Open.

## Verification

The analytic Gaussian expectation, numerical counterexample, independent
source reconstruction and research review above precede this documentation
change. Independent final research review approved the report and cold-memory
qualification. Full foreground `make check-all PYTEST_WORKERS=4` passed
3,237 backend tests (97.54% coverage) and 359 frontend tests (97.63% statements).

The subsequent display qualification and FINDING-164 scope correction passed
21 focused frontend cases and full foreground `make check-all PYTEST_WORKERS=4`:
3,318 backend tests (97.56% coverage) and 363 frontend tests (97.63% statements).

## Source documentation qualification — 2026-10-11, ADR-239

Before ADR-239, source docstrings described the band log mean as E[simple return],
the specified recursion as certified MMSE, and the latent/filtered gap as
unrecoverable edge. The generic scorer accepts supplied lagged predictions; it
cannot certify their mean or strategy optimality. These source-facing claims required
the same qualifications already present in the UI and this finding; ADR-239
now applies them to the source.

Generator variance statements also require a stationary-model qualification.
With stationary latent variance deviation_vol**2, Var(delta deviation) is
2*(1-rho)*deviation_vol**2 and Var(conditional log-mean deviation) is
(1-rho)**2*deviation_vol**2. Their ratio is (1-rho)/2. Together with level noise,
the chosen stationary log-return variance is total_vol**2. This does not fix
finite-sample realized volatility, the initialized transient, simple-return
variance or a strategy's Sharpe bound. Independent research review approved this
qualification before documentation edits.

ADR-239 changes only explanatory source wording and records these limits;
mathematical references and initialization remain unchanged and this finding
remains Open. Parent and independent review confirmed the entire executable
module AST unchanged after excluding actual docstrings. Final independent review
approved all four paths and the variance derivation. Full foreground make
check-all passed 4616 backend and 363 frontend tests, with lint, strict types and
coverage green. No wording-mirroring tests or source redraws were added.

## Residual active guidance qualification — 2026-10-14

The remaining PowerCalibration field comment and active cold-memory/architecture
advice still described the filtered reference as a recoverable-edge bound and
ruled out better estimators or selection rules. These claims now describe only
the specified strategies and measured comparisons. Low net reference scores do
not establish no tradeable edge; historical 0/50 detections do not establish that
another causal, cost-aware strategy could not graduate. The historical band table
is unchanged, including its original labels and values. FINDING-155's AR drift
qualification is also retained. No historical accepted ADR is rewritten.

The entire calibration module AST, including docstrings, compares exactly with
the published predecessor: only two explanatory comments change. The historical
cold-memory band table also compares byte-for-byte. This qualification implements
the existing reporting scope of ADR-239/F159/F164; it neither corrects the
mathematical reference nor certifies filter initialization. This finding remains Open.

Independent final research review approved all five paths, the exact entire
module AST and table comparisons, and the retained historical finalist shares
(18% Mean Reversion versus 68% Trend at half-life1). Full foreground
`make check-all` passed 11,311 backend tests (97.38% coverage) and 363 frontend
tests (97.63% statement coverage), with lint, formatting and strict typing green.

## Concrete startup covariance mismatch — 2026-10-17

A deterministic source review at `fcf6ef10` establishes a specific initialization
mismatch, without drawing a source or measuring a score. Write
`s² = deviation_vol²`, `q = s²(1-rho²)` and `R = level_vol²`.
The generator starts `d[-1]=0` and draws `d[i]=rho*d[i-1]+epsilon[i]`,
with independent Gaussian innovations of variance `q`. Consequently
`Var(d[0])=q`, rather than stationary variance `s²`.

The historical filter ignores the first absolute log price and first updates on
`z[1]=y[1]-y[0]-drift=d[1]-d[0]+eta[1]`. Its initialized diagonal
covariance `diag(s²,s²)`, followed by its transition, instead supplies

```text
P_historical([d[1], d[0]]) = [[s², rho*s²], [rho*s², s²]].
P_zero_init([d[1], d[0]])  = [[rho²*q+q, rho*q], [rho*q, q]].
```

For `P=[[a,c],[c,b]]` and observation vector `[1,-1]`, elementary Gaussian
conditioning gives gain `(a-c)/(a+b-2*c+R)` for the current deviation. The two
matrices therefore produce different posterior means even using only observed
differences. This is a startup-law discrepancy, independent of the separate
log-return/simple-return mismatch.

There is a further information-set choice. If the source start price is known,
`w[0]=y[0]-log(start_price)-drift=d[0]+eta[0]` is already informative.
Conditioning on it gives initial posterior mean `q/(q+R)*w[0]` and variance
`p=q*R/(q+R)`. Before the first difference update the corresponding matrix is
`[[rho²*p+q, rho*p], [rho*p, p]]`. A differences-only correction would still
exclude this first-price information. Arbitrary supplied prices do not establish
a known start price or this source law; a future corrected reference must declare
its information set explicitly.

A finite hand-built example uses log prices `[0, 0.01]`, `rho=0.5`,
`deviation_vol=0.02`, `level_vol=0.01`, `drift=0`, and, for the full-price
interpretation, `start_price=1`. The historical function returns first estimate
NaN and second estimate `0.004`, a gain of `0.4`. Independent exact Fraction
conditioning gives gain `9/19` (approximately `0.473684`) from differences only,
and `45/67` (approximately `0.671642`) from both prices with the known start.
Here `w[0]=0`, so both correct initial means are zero; the unequal gains result
from the different covariance assumptions. The returned posterior is at index 1;
the generator's existing shift uses it to predict index 2.

Parent and independent research review reproduced these calculations. Receipts:
`/tmp/qf-w42-s28-band-startup-review.md` (derivation and executable probe;
SHA256 `c84a7041a6e33a709e659d3e92e8580e7c16db48a854ccce5adabd52184752b3`)
and `/tmp/qf-w42-s28-band-startup-parent-receipt.json`. No RNG, generator,
reference scorer, search, artifact rewrite or frozen cohort was invoked.

This does not quantify any historical score, sign, power or long-run effect, and
does not certify a replacement filter. The existing filter and its historical
measurements retain their meanings. A future separately governed helper should
specify startup law and available observations, and expose posterior variance as
well as mean: a filtered simple-return prediction needs predictive log variance
`q+R+(rho-1)²*posterior_variance`. Correcting only latent innovation variance
would omit state uncertainty. Even exact conditional means do not establish a
cost-aware optimum or a realized-sample maximum. This finding remains Open.

Final independent research review approved both documentation paths and the exact
conditioning calculations. Fresh full foreground `make check-all` passed 12,560
backend tests (97.40% coverage) and 401 frontend tests (97.68% statements), with
lint, formatting and strict types green. Backend, frontend and generated-data
paths are unchanged; no wording-mirroring tests were added.

## Additive known-start posterior prerequisite (ADR-310)

ADR-310 supplies a separately named `band_price_posterior` in
`app/research/lab/band_posterior.py`, leaving the historical filter and generator
intact. It requires explicit rho, level/deviation volatility, drift and source
start price. Its law has known zero level and deviation before the first shock;
the start price is the pre-shock scale, not the observed first close. Every output
conditions on all observed prices through its own index, including index 0.

The two owned output arrays contain posterior deviation means and variances.
The scalar variance update uses the nonnegative covariance-determinant identity
recorded in ADR-310, without subtracting nearly equal variances, clipping or
introducing artificial noise. Genuine zero level noise yields zero posterior
variance and an observable deviation. Positive noise or posterior variance lost
to zero through the selected arithmetic refuses rather than claiming certainty.

This new helper explicitly computes a normalized binary64 model, not preserved
native wide/exact arithmetic. Original finite nonboolean scalars/ranges and
original complete real numeric ndarray evidence validate before conversion;
normalization does not certify prior caller coercions or source-law provenance.
Derived law validates even for empty input. Finite checks may conservatively
refuse mathematically representable results when fixed intermediates fail; finite
output does not certify arbitrary numerical conditioning or universal accuracy.

A precode independent exact Fraction calculation matched scalar posterior mean
and variance to full joint-Gaussian conditioning for 96 hand-built prefix cases,
including negative/zero rho, nonzero drift and zero level noise. It verifies the
mathematical identity on that grid, not the eventual binary64 implementation.
No generator, source draw, scorer, search, data artifact or frozen cohort is used.

This is a posterior component, not the corrected simple-return reference or its
production opt-in. Historical meanings, source/filter/scorer bodies, schemas,
defaults, search/gate accounting and thresholds stay unchanged. F159 remains Open;
future use still needs predictive variance, explicit method/law/startup/observation
attribution and separate governance. No cost-aware optimum, realized-sample Sharpe
maximum, recoverable-edge bound or new power result is established.

Actual behavioral RED closed with 83 failed cases before the implementation
module existed (`/tmp/qf-w42-s28-posterior-red.log`); failure occurred in test
bodies, not collection/setup. Final focused verification passed 91 cases; eight
boundary cases were added after green and are not claimed as pre-code RED.
Ruff, formatting and mypy passed. Tests independently condition full exact
Gaussian covariance matrices, check causal prefixes and path-independent
variances, and cover first-price assimilation, zero level noise, original versus
normalized scalar/source validity, underflow, ownership and NumPy policy.

Parent independent review approved the source and tests. A separate exact
Fraction joint-conditioning audit compared 96 prefix mean/variance pairs with
the binary64 helper: maximum absolute differences were 2.61e-18 for means and
8.14e-20 for variances. This bounded tolerance comparison does not assert
universal or bitwise numerical accuracy. Receipt:
`/tmp/qf-w42-s28-posterior-parent-audit.json`, source SHA256
`6f4138d73fbeec187859098768b9a595b714720f803e80f3dabb42112d68baa9`.
All existing backend, frontend and data paths remain byte-unchanged; only the
standalone module and its tests are new. Fresh full foreground `make check-all`
passed 12,689 backend tests (97.40% coverage) and 401 frontend tests (97.68%
statements), with lint, formatting and strict types green. All local verification
is closed; exact master CI is checked after individual publication. F159 remains
Open for separately attributed simple-return references and production wiring.
