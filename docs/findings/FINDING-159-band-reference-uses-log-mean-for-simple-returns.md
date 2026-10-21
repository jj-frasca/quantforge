# FINDING-159: Band reference uses log mean for simple returns

- **Date:** 2026-10-08
- **Severity:** High — reference optimality and power interpretation
- **Status:** Resolved by ADR-313 explicit production opt-in; historical reference meanings retained
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

## Horizon console qualification (ADR-312)

The horizon driver's console retained unsupported upper-bound/recoverable-edge
claims after the earlier source/UI qualifications. ADR-312 separately governs
these printed claims: latent gross/net and specified filtered net strategy scores
are reference comparisons, and selected in-sample ratios remain selection biased.
Historical log-mean signs are scored on simple returns; the historical filter's
startup/posterior is uncertified. The driver identifies its historical convention
without certifying provenance for arbitrary supplied score arrays. Reported history
is supplied synthetic history, not a claim of equality to every real hunt.

A refused filtered ratio can mean incomplete finalist/reference evidence or missing
history as well as a denominator failing the existing noise check. The unchanged
branch now describes those generic evidence/denominator requirements; refusal does
not establish absence of tradeable edge. No cost-aware optimum, realized-sample
maximum or bound on every causal strategy follows from these reference scores.
The module's variance explanation and three shared PowerCalibration docstrings
receive the same qualifications. No accepted historical ADR or artifact is rewritten.

Six hand-built report cases failed in test bodies before the print changes
(`/tmp/qf-w42-s28-report-red.log`, 2.72s). They exercise positive ratios, small/zero
denominators, missing history, partial finalists and absent optional metrics; no
source generator, scorer, posterior or search is called. Expected displayed medians,
percentiles, ratios, counts, versions, history and costs retain their values.
F159 remains Open for the separately governed production correction; ADR-310's
posterior is not activated by this reporting change.

Independent final research review approved all six paths and independently passed
21 report/parser cases. Parent focused verification passed 73 report/parser/capture
cases. Exact AST comparisons preserve the entire calibration module after excluding
only the three named docstrings, and the entire horizon module after excluding its
introductory docstring and report text. Every report interpolation/format specifier,
branch and scientific call remains exact; all existing tests/frontend/data remain
unchanged. Receipt: `/tmp/qf-w42-s28-report-source-audit.json`, horizon source SHA256
`993c0db646cbd16bdda18397ab172599eaac3e078aaa6239ec75c26bbeaec405`.

Session30 resumed the same six owned paths without source edits. Fresh independent
research review approved them and passed all six reporting cases. A fresh parent
AST audit confirmed the same scoped exclusions and exact expressions, predicates
and formats (`/tmp/qf-w42-s30-report-audit.json`); horizon source SHA256 remains
`993c0db646cbd16bdda18397ab172599eaac3e078aaa6239ec75c26bbeaec405`.
Fresh full foreground `make check-all PYTEST_WORKERS=4` completed successfully:
12,710 backend tests (97.40% coverage) and 401 frontend tests (97.68% statements),
with lint, formatting and strict types green. Receipt:
`/tmp/qf-w42-s30-check312.log`. All local verification is closed. This reporting
correction leaves F159 Open and does not activate a conditional reference mode.

## Explicit conditional-simple-mean sign opt-in (ADR-313)

ADR-313 governs the complete production correction separately from historical
reporting. One explicit versioned known-law mode retains drift, total volatility
and pre-shock start, alongside per-cell half-life/share. Historical missing method
metadata remains unknown; no old array, artifact or frozen cohort is rewritten.
Known cells cannot also carry AR metadata or phi, and reconstructed sweep headers
and cells must agree. Capture deltas refuse changed common reference identity or
changed paired-cell share rather than attributing a new denominator to a catalog.
Detection-only probability comparison retains its existing statistical meaning.

Under the declared nominal zero-initialized Gaussian law, latent prediction uses
the preceding supplied deviation; observed prediction uses ADR-310's full-price
posterior through the preceding bar. Predictive log variance is q+R for the latent
rule and q+R+(rho-1)^2*p for the observed rule. The latter assimilates the first
price, so its first scored return can be at index1, with no extra startup lag.
Index0 remains unavailable under the established cost/return convention.

The new rule supplies the finite binary64 sign score `2*m+V`, not a conditional
mean magnitude. Gaussian monotonicity makes its sign that of the conditional
simple-return mean. Finite doubling is exact and the binary64 subnormal lattice
preserves nonzero exact addition signs under gradual underflow. This avoids
half-variance/expm1 underflow without a fallback or tolerance, but certifies only
the already-computed binary64 m,V. Earlier posterior/law/source rounding remains
explicit. Positive posterior uncertainty lost to a zero product refuses; ordinary
finite rounding otherwise remains accepted. Fixed nonfinite intermediates refuse
rather than applying clipping, jitter or a preferred-sign repair.

The original generator, historical filter and generic scorer remain intact.
The nominal q convention and rounded sampling-scale arithmetic are not claimed
universally bitwise equivalent. All conditional source/deviation evidence is
snapshotted and validated for every symbol before scoring/search; explicit CLI
law validates before generation. The new source domain uses NumPy-backed numeric
columns; object-backed or unsupported extension evidence conservatively refuses. These checks establish dispatch and evidence
coherence, not arbitrary latent/source provenance. Latent gross/net and full-price
observed net scores use the established scorer and turnover costs.

The supported correction still establishes neither cost-aware optimality nor a
realized-sample maximum, recoverable-edge bound, absence of tradeable edge or new
power measurement. Historical results retain their original scientific limits.
Verification of the complete production opt-in is recorded below when complete.

ADR-313 verification completed after the following actual RED observations:
seven central behavioral cases before implementation, one later categorical-axis
ownership failure and one scalar-conversion failure before their respective
corrections; 15 mocked CLI/report failures; three API retention failures; and
35 frontend schema/panel failures plus one dashboard failure. Expanded boundary
cases were added after green and are not claimed as pre-code RED.

Final central verification passed 111 focused cases with 97.56% utility coverage
against the unchanged 85% floor; CLI/report regression verification passed 105;
frontend focused verification passed 116. Independent final research review
approved frozen source/tests/docs and independently passed 77 new-suite cases.
Frontend integrated review approved transport/presentation and API contracts.
Fresh full foreground `make check-all PYTEST_WORKERS=4` passed 12,787 backend tests
(97.39% coverage) and 438 frontend tests (97.69% statements), with lint, formatting
and strict typing green. The first full attempt stopped at a new API-test
formatting issue before tests; formatting was corrected before the fresh gate.
Receipt: `/tmp/qf-w42-s30-check313-final.log`.

Parent exact Fraction full-joint Gaussian conditioning independently compared
48 prefix sign scores: maximum absolute difference 8.67e-19 against the stated
2e-12 tolerance (`/tmp/qf-w42-s30-band-math-audit.json`). This bounded arithmetic
check is not universal accuracy or source correspondence certification. A separate
successful mocked measurement retained explicit known metadata and matched every
non-reference payload field to an equivalent supplied-array control; all three
reference scoring calls and both searches were mocked, with no source generation
(`/tmp/qf-w42-s30-band-dispatch-audit.json`). It is one no-graduate control,
not a power result.

Fresh audits preserved both historical sweeps' 12 semantic cells and raw hashes,
36 existing calibration definitions, the entire ADR-310 helper bytes, the original
measurement/search/count tail and exact legacy horizon generator/scorer/measurement
calls. All prior frontend test bytes remain; new cases are appended. Receipts:
`/tmp/qf-w42-s30-band-compat-receipt.json`,
`/tmp/qf-w42-s30-band-source-guard.json`, and frozen production hashes in
`/tmp/qf-w42-s30-band-source-hashes.json`. No generated JSON, frozen cohort,
threshold, accounting-v14 or search/gate identity was authored or changed.
This resolves the supported explicit production correction gap; historical
qualifications and arbitrary provenance/optimality limitations remain.

## Residual README publication gap — 2026-10-21

At `46f7baf6`, README still describes the historical filtered reference as an
upper bound on every causal price strategy, treats low reference scores as
absence of recoverable edge and says any graduate in those cells would be wrong.
Its recognition-versus-expression assertion also says no reverting strategy wins
despite the same paragraph's recorded 18% reverting finalists. These are residual
public claims already ruled out by this finding and ADR-239/312; they are not new
measurements or a reopening of the supported ADR-313 opt-in correction.

The same public section calls low historical AR net reference scores proof of
no tradeable edge (FINDING-155), presents old measurements as current production
evidence (ADR-294), and treats an individual-score Lo standard error as an
uncertainty test for a selected dependent category difference. That descriptive
comparison cannot prove insufficient information or explain a graduation count.
The frontier likewise describes a conditional single-bar iid-normal asymptotic
model, not composite pipeline power or a universal minimum edge (ADR-292).

The documentation-only correction applies the existing F155/F159/F164 and
ADR-239/292/294/312 boundaries to README. Historical numbers and cohort identities
remain intact. Recorded snapshots are explicit; references and selected in-sample
ratios carry no optimality, market-power or absence-of-edge guarantee. Build/test
counts remain historical snapshots rather than fabricated current measurements.
No accepted historical ADR, artifact, scorer, posterior, search, threshold or
frozen cohort is changed. This records follow-through in the existing finding
under ADR-239 rather than creating a duplicate mathematical finding.

Verification: independent final three-path review approved the wording. Parent
audit preserves all 331 prior numeric-token occurrences; an independent tokenizer
preserves all 318 of its prior occurrences, each of the 13 table rows' numeric
multisets and 14 explicit cohort contexts. These lexical checks supplement the
contextual review; they are not a recomputation of historical results. All 1,293
tracked backend/frontend/data files remain byte-identical to `46f7baf6`.
Receipts: `/tmp/qf-w43-s13-readme-review.md`, `-review.json` and
`-numeric-audit.json`. Final README SHA256:
`b4b2c816a3006ac56f3271dbcfcdcb5b54e48d74357361af58746f5fce613a73`.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed 13,811 backend tests
(97.38% coverage), 566 frontend tests (97.83% statements), lint, formatting and
strict types (`/tmp/qf-w43-s13-check-readme.log`). All local verification closed
before individual publication; exact master CI is checked after pushing. No
wording-mirroring tests, source draws, searches, provider/broker calls, threshold
changes, historical ADR edits or generated-data writes were needed.
