# Validation Methodology (Cold Memory)

Formal specs for the validation engine (Phase 4) — the layer that makes QuantForge credible.
Read when working on `backend/app/validation/`. Citations + summaries in research-papers.md.
Each component encodes a mathematical invariant as a Hypothesis property test.

**Staleness note (added 2026-09-22 session #95, §7.8 backfilled 2026-09-22 session #96):** §7.8 was
found frozen at ADR-074's original underpowered n=45 look; it now carries ADR-076's closing n=200
result and the Pocock-boundary reasoning in full (transcribed from `docs/ARCHITECTURE.md` §0.6.1,
which remains the current authority for anything not yet folded back into this file — it updates
same-day, this file does not). §7.7's panel-null paragraph is a live exception to that lag: the
project's convention has each panel-null ADR commit append its own 2–4 line summary directly here
(see the ADR-097/098/099 sentences at the end of that paragraph), so §7.7 has stayed current on its
own without needing a periodic backfill. **`docs/ARCHITECTURE.md` §0.6.1 is still the tie-breaker**
if this file and it ever disagree — read it before citing a number here that isn't corroborated
there, since this note itself could go stale the same way the original one did.

---

## 1. Deflated Sharpe Ratio (DSR) — value form

`app/validation/deflated_sharpe.py`. Adapted from Bailey & López de Prado (2014).

We report DSR as a **deflated Sharpe value** (not a probability), so the §8 invariant
**DSR ≤ observed Sharpe** holds by construction: `DSR = observed_SR - haircut`, where the
haircut is the expected maximum Sharpe under the null of N independent trials:

```
# Expected max of N iid ~N(0, sr_std^2) Sharpe estimates (Bailey et al.):
E_max = sr_std * ((1 - γ) * Φ⁻¹(1 - 1/N) + γ * Φ⁻¹(1 - 1/(N·e)))      # γ = Euler-Mascheroni 0.5772
haircut = max(E_max, 0)        # N == 1 -> haircut 0 (no multiple-testing penalty)
DSR = observed_sr - haircut
```

- `sr_std`: dispersion of Sharpe across trials (input; default a small positive value).
- **Invariant**: `DSR ≤ observed_sr` always (haircut ≥ 0); more trials ⇒ larger haircut ⇒
  lower (or equal) DSR; N == 1 ⇒ DSR == observed_sr.

**Important source distinction (FINDING-007, resolved by ADR-054).** The paper's DSR is a
probability-form PSR against the expected-max threshold and includes sample length, skewness, and
kurtosis. QuantForge's stored `deflated_sharpe` field is a selection-adjusted Sharpe **margin**, not
that probability, and its `> 0` gate asks whether observed Sharpe clears the multiplicity threshold.
**Never call the margin the Deflated Sharpe Ratio.** Both statistics now exist:

- `probabilistic_sharpe_ratio(observed_sr, benchmark_sr, n_returns, skew, kurtosis)` — Eq. 1, with
  **RAW** kurtosis (a Normal series is 3.0, which reduces the denominator to `1/sqrt(n-1)`). pandas
  reports EXCESS kurtosis; `return_moments()` in `backtesting/metrics.py` does the conversion and is
  the only thing that should be feeding this function.
- `deflated_sharpe_probability(...)` — the paper's Eq. 2: PSR against `expected_max_sharpe`.
- `Trial.deflated_sharpe_probability` records it on every new search, nullable so the ~3,200
  pre-ADR-054 pool rows read as *not measured* rather than as a probability of zero.

ADR-182 requires complete finite real nonboolean numeric input to `return_moments` before
short/constant shortcuts. pandas must not skip NaNs while the PSR sample count includes them.
Missing/object/string/complex/boolean payloads raise; complete nullable numeric and finite signed
observations remain valid. Undefined native skew/raw kurtosis returns None, matching unmeasurable
variance. Representable estimates, sample counts, PSR formula and gate thresholds are unchanged.

ADR-203 recognizes exact constant original observations before native higher moments,
returning None rather than fabricated Normal PSR inputs from rounded false variance.
The shared primary Sharpe likewise keeps exact constant zero, preserves measurable
native answers and recovers failed native moments with maxabs-normalized sample math.
Unmeasurable recovery raises; original cost/sign properties retain their entire domains.
Finite primary scores/moment evidence change, so calibration identity advances to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-v8`.
Historical rates remain attributable; current replacement rates are unmeasured.

ADR-204 refuses native higher-moment underflow through None, consistently under
ignore/warn/raise caller state; finite kurtosis must not conceal an underflowed
fourth-moment calculation. Native source checks/estimators/counts and degenerate
precedence remain. Accounting identity advances to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-v9` because
former finite moment evidence becomes unmeasured. No rates are remeasured or claimed.

ADR-209 corrects foundation Sharpe native partial underflow and finite zero means
with lost original sum evidence. Local underflow detection and original float64
fsum zero certification route those failures to normalized sample std and stable
sum recovery. Annualization/std division precede sample-count division, preserving
representable subnormal scores lost by mean-first rounding. Other native nonzero
measurable scores remain; all original
financial property domains and gate thresholds stay. Accounting identity advances
to `whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-v10`.
Historical v9 measurements retain their executed revision and cannot certify v10;
fresh fixed-cohort evidence must record the new identity. Arbitrary finite-result
precision and nonzero native cancellation remain separate limitations.

ADR-286 / FINDING-235 corrects finite Float64 Sharpe dispersion recovery that
scaled near-equal levels before centering. Only original native/classic Float64
STD underflow or finite zero collapse selects anchored differences and original
fsum/exponent recovery. Nonfinite STD, mean/ratio-only failures, other families and
ordinary native estimates retain prior behavior. Trial accounting now advances to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-v11`.
ADR-289 subsequently advances accounting to v12 for certified PBO translation.
ADR-290 then advances to v13 for certified native primary Sharpe translation.
ADR-291 advances to v14 for certified OOS selection/test/control translation.
All historical v13/v12/v11 and frozen v10 cohorts retain their executed identity and cannot certify
v14. Those current-version distributions were unmeasured at adoption; F241
below subsequently measures one local iid-normal cohort only; frozen sources/results are not rerun, redrawn or relabeled. No actual
false graduate is established and no threshold or generated-data change is made.

Local session15's fixed v9 iid cohort completed200/noerrors/0graduates/0ADR018
survivors (F156), independently audited with a one-sided95% zero-event upper
limit of1.4867%. It is historical f1891104/v9 evidence, not v10/v11/v12/v13/v14 certification
or power/bootstrap coverage. F157 records the completed paired v10 cohort at
380df982: identical sources, 200/no errors/0 graduates/0 ADR018 survivors, and
identical result payloads except the search fingerprint. These are 200 paired
sources, not 400 independent observations; the one-sided95% zero-event upper
limit remains1.4867% for each version. Power, heavy-tail stress and bootstrap
remain separate, unmeasured controls; generated data unchanged.

FINDING-241 measures one NEW fixed local v14 iid-normal cohort at executed
66c1c5d8: 200/200 sources, zero errors/graduates/ADR018 survivors, one-sided95%
zero-event upper1.4867%. Full34/defaultGate/refine/nper3/7400/prior0/noStore;
combinedN200 bar1.3432393159670402. Historical v10/v9 sources were not rerun or
pooled. F241 alone leaves power, heavy-tail, bootstrap and published sole-writer artifacts
unmeasured; F243 subsequently measures the separate Student-t5 stress below. This local law-only result is not a threshold
permission or complete ADR102 candidate comparison. See F241 for frozen hashes,
checkpoint/source audits and pre-search reader-unit refusal/amendment.

FINDING-242 records the separate new v14 paired strong-AR execution as
incomplete: 95 durable Experiments and one unresolved started source out of
400 frozen sources (N200 per arm). The frozen no-repeat protocol prevents
continuation through that missing completion. No partial power rate, interval
or full-N inference is reported; the positive arm remains unmeasured. Original
sources and checkpoints are preserved, without retry, redraw or historical pooling.

FINDING-245 records session15's separate prospective v14 strong-AR attempt
as incomplete:69 durable Experiments/70 started markers out of400 frozen
sources (N200 per arm), unresolved NEG0069, no arm result or summary. No
partial rates or intervals are inferred; the positive arm is unmeasured.
Its frozen protocol forbids retry/redraw/budget renewal and further replacement
attempts after incompletion. F242 remains separate; neither prefix is pooled
or treated as a completed power measurement. Sources/checkpoints are preserved.

FINDING-243 records a separate NEW fixed v14 Student-t5 stress at executed
a8054a5d: all200/200 searches completed, zero errors/graduates/ADR018 survivors,
one-sided95% zero-event upper1.4867% under the stated valid-source stress model.
All7000 retained compact Trial records were checked; no raw-config matrix rescan
is claimed. Full34/defaultGate/refine/nper3/7400/prior0/noStore; all sources froze
before search. Historical F163v10 and F241iid are not pooled or rerun. Finite fourth/
infinite eighth moments limit kurtosis-precision assumptions; this does not certify
bootstrap, power, markets or an ADR102 probability-gate change. See F243 for hashes
and final verification receipts.

FINDING-247 records the prospective v14 bootstrap:SPY control at81e9429f as
incomplete:52 durable Experiments/one-symbol shards,53 starts out of200 frozen
sources, unresolved V14BOOTSPY_0052 and147 never started. No combined result,
partial rates, intervals or full-N Type-I inference. The fixed5400s single-fresh-
invocation protocol forbids unresolved retry, redraw, budget renewal or repeated
attempts until a complete/preferred result appears. Exact8485-bar empirical SPY
input/all305qualityissues/sources/checkpoints remain preserved. Current bootstrap
remains unmeasured; F241iid/F243t5 and historical evidence are not pooled.

ADR-316 preregistered one distinct local heteroskedastic null, now recorded
as incomplete by FINDING-267:
N200, 7400 bars, initial100 and7399 independent Uniform[-sqrt(3),sqrt(3)]
innovations scaled by .005/.04 alternating every252returns, starting low.
Ideal-law conditional simple-return mean is zero; variance is predictable.
Binary64 is an approximation, not exact numerical-martingale certification.
Seeds2026101809000+i and canonical causal OHLCV/ns calendars freeze together.
All200 sources need a hash-bound independent pre-search audit before any search.
The unchanged full34/defaultGate/refine/nper3/prior0/noStore procedure has one
7200s soft admission clock; one admitted call may finish later. Never renew,
retry, redraw, replace or infer rates from a prefix. Rates require200complete/
zeroerrors and final source/count/model audits; original incomplete AR/bootstrap
attempts remain frozen. Custom null-mode evidence cannot authorize ADR102 or
any threshold change. At adoption, no actual cohort draw or search had occurred.
FINDING-267 records its subsequent single-use execution as incomplete: all200
sources froze and passed independent pre-search audit; only3 Experiments/shards
and4 START markers are durable, with V14HET31_0003 unresolved and196 never
started. No combined result, summary, durable error or invalidation is recorded;
these absences establish no cause or activity state. No endpoint counts, partial
rates, intervals or full-N inference are reported. Preserve all original bytes;
no retry/redraw/fresh continuation/budget renewal/replacement attempt. This
variance-schedule control remains unmeasured, separate from all earlier cohorts.

ADR-190 validates positive nonboolean integer trial count and finite positive real dispersion
at shared expected_max_sharpe entry before N=1. Invalid accounting cannot create an unpenalized
probability; margin/probability delegate to one guard. Valid formulas, counts and gates remain.
ADR-191 resolves FINDING-126 with equivalent inverse-survival quantiles from integer-divided
reciprocal tails and finite-tail/final-haircut refusal. Counts beyond float max remain supported
when both tails are representable; ordinary estimator/threshold/identity stay unchanged.

ADR-192 validates PSR original count/scalars before existing moment/formula checks: nonboolean
integer history >=2 first, then finite real nonboolean observed/benchmark Sharpe, skew and raw
kurtosis. Probability DSR inherits the guard; valid signed/numpy/Fraction inputs and estimator
remain. Native extreme arithmetic and margin observed-score validity stay separate.

ADR-193 distinguishes retained strict Pearson moment slack (`kurtosis-skew^2-1 >0`) from
PSR SE squared (`(1-skew*SR + .25*(kurtosis-1)*SR^2)/(n-1)`). Zero slack can describe
genuine two-point distributions; the existing strict domain policy still excludes them. No
runtime guard, formula, assertion, threshold or legacy error text changes.

ADR-194 validates margin-form observed Sharpe after shared accounting checks, preserving their
error precedence, then requires a finite native subtraction. Signed/numpy/Fraction scores and
N=1 behavior remain; invalid observed evidence or overflow cannot be published as a margin.

ADR-195 requires finite native Pearson slack and finite positive PSR SE-squared, converting
native arithmetic overflow to ValueError. Whole-search probability accounting retains its
unmeasured None for refused arithmetic; the strict moment policy, formula and Gaussian CDF
tail saturation remain. This refuses extreme arithmetic rather than recovering it numerically.

**The scale trap, which is why this took two attempts.** Everything on a `Trial` is ANNUALIZED; the
PSR is a function of the PER-PERIOD Sharpe and the per-period moments TOGETHER. Mixing one
annualized input with two per-period ones silently rescales the probability instead of failing.
`whole_search_deflated_sharpe_probabilities()` divides the observed Sharpe AND the trial dispersion
by the same `sqrt(252)`; do not add a caller that skips one of them.

**The gate still gates on the MARGIN.** `PoolReport.statistic_agreement` counts how often the two
statistics reach the same verdict on the same finalist, at a stated `probability_reference` that
nothing gates on. Switching the gate to the probability is a threshold change: it requires a fresh
Type-I error and a fresh power curve for the new statistic, all three calibration workflows
re-dispatched together at the same `n_bars` (§7.2), and its own ADR.

**Search-level accounting (ADR-046/050).** A StrategyLab run first evaluates parameter configs inside
families and then selects across the family finalists. DSR must price that whole selection, not
reset inside each family. Both longitudinal and cross-sectional search pool every current candidate
Sharpe to estimate one Normal-consistent IQR scale for `sr_std`, use cumulative concrete-config
`lifetime_trials` for N, and apply the same haircut to every family finalist before the overall
argmax. The robust central scale prevents a minority of real signal-loading strategies from raising
their own supposed-null haircut without bound (ADR-050); fewer than four candidates retain sample
standard deviation. `Trial` is therefore a compact family-finalist summary with
`n_evaluated_configs`; the number of stored summaries is NOT the margin or MinTRL denominator.
Historical longitudinal pool counters predate this field and remain a lower bound; generated
records are never guessed/backfilled against today's catalog.

ADR-196 validates each original candidate Sharpe as finite float-representable real
nonboolean evidence before array conversion, rejecting nested families and coerced
strings/booleans. Both native std/IQR branches require finite dispersion before the
unchanged degenerate floor. It refuses extreme arithmetic without estimator recovery;
counts, ordinary formulas, thresholds and calibration identity remain unchanged.

ADR-295 validates original caller trial counts before arithmetic: MinBTL requires
positive nonboolean Integral counts; both public searches require nonnegative
nonboolean Integral priors before any work. Accepted NumPy integrals normalize
to Python int before cumulative addition, preventing fixed-width wrap. Valid
Python-count formulas, thresholds, v14 identity and calibration prior=0 remain.
F249's manual negative-prior counterexample is not observed production corruption;
historical schemas, lower-bound counters and frozen/generated evidence are untouched.

ADR-299 validates recorded trial counters before coercion: original positive
nonboolean Integral n_evaluated_configs (missing legacy default1 unchanged), and
original nonnegative Integral lifetime_trials on both experiment families.
After existing lineage checks, lifetime must cover the sum of current recorded
trial counts. Both memory stores reconstruct incoming models before append;
JSON writers already do. Higher priors, empty-trial zero, max aggregation,
retention and historical lower-bound meaning remain. F253 is synthetic
model/store evidence; fresh all3318 committed rows were compatible without data
writes or invented counts. No estimator, threshold, schema field or v14 change.

ADR-297 validates original MinBTL annualized_sharpe after count validation
and before its nonpositive shortcut: finite float-representable nonboolean Real.
The original score operand/sign/square/division remain; ADR-298 below separately
refuses native extreme arithmetic faults recorded in FINDING-252. F251 is standalone
synthetic evidence; gate reports already provide finite Python floats. No formula,
threshold, configuration hash, accounting-v14 or calibration procedure changes.

ADR-298 refuses unmeasurable positive-score MinBTL arithmetic (FINDING-252).
Keep native numerator/square/division order and operands; require the square's
float inspection finite and positive, verify original Integral squares against
exact Python-int multiplication, then require a finite nonnegative result.
Native arithmetic exceptions become ValueError; caller NumPy policy/warnings
remain. Binary64 inspection deliberately refuses some finite Fraction/wider
squares outside its range. No N=1 shortcut or numerical recovery; ordinary
supported native results, nonpositive infinity and huge Python trial counts
retain their meanings. Thresholds, config hash, v14 identity and frozen/generated
evidence remain unchanged; no new rates or universal precision claims.

ADR-296 validates original available track_record_years at GraduationGate after
report reconstruction and MinBTL/count evaluation. Require finite float-representable
nonboolean Real and original nonnegativity; retain the original comparison operand.
F250's direct synthetic infinite-duration graduation is refused, without inferring
production misuse. Zero available history and intentional infinite required history
keep their meanings. Formula, thresholds, reason text, hashes and v14 stay unchanged.

**Pool reporting (ADR-066).** `Experiment.lifetime_trials` is already cumulative per symbol. The
programme-wide trial headline therefore sums the maximum counter once per symbol; summing every
retained experiment would count the same prior trials repeatedly. The aggregate is the sum of the
per-symbol DSR/MinTRL denominators, not one global denominator.

---

## 2. Probability of Backtest Overfitting (PBO) — CSCV

`app/validation/pbo.py`. Bailey et al. (2015), Combinatorially-Symmetric Cross-Validation.

Input: a performance matrix `R` of shape (T observations, N configurations). Procedure:
1. Split the T rows into `S` disjoint groups (S even).
2. For each of the C(S, S/2) ways to pick S/2 groups as **in-sample (IS)** (rest = OOS):
   - rank configs by IS Sharpe; pick the IS-best `n*`.
   - compute the OOS rank of `n*` as `w = rank / (N + 1)` ∈ (0, 1).
   - `logit = ln(w / (1 - w))`; the split is "overfit" if `logit ≤ 0` (IS-best below OOS median).
3. **PBO = fraction of splits that are overfit.**

- **Invariant**: PBO ∈ [0, 1]. A matrix of pure-noise configs ⇒ PBO ≈ 0.5; a single
  dominant config ⇒ PBO ≈ 0.

**Search-level scope (ADR-104).** Production selects within parameter grids and then across strategy
families; longitudinal refinement can add another adaptively chosen grid. The gate therefore uses
one PBO over the complete matrix of every concrete candidate evaluated in the current search and
persists that same procedure-level value on each compact family-finalist summary. The former
family-local value omitted the final cross-family argmax and could pass a globally overfit selector.
Parameter stability remains family-local because unrelated families do not define a neighborhood.
ADR-104 advances calibration identity; pre-ADR-104 artifacts do not measure this PBO procedure.

**Tie handling (ADR-105).** Exact Sharpe ties use average one-based OOS ranks, and every tied IS
maximum contributes its equal-weight `logit <= 0` indicator to that split. Positional `argmax` plus
ordinal `argsort` made the same candidate set report PBO 0.167–0.500 under column permutations.
Candidate labels are not evidence; PBO is now permutation-invariant. With no ties the statistic is
unchanged. Calibration identity advances again, and the live `pbo_max` remains strictly 0.5.

**Evidence boundary (ADR-106).** PBO rejects non-matrix, non-finite, and statistically unmeasurable
inputs before computing a split. A `NaN` or infinity is not a zero-return observation: the former
guarded division silently assigned contaminated candidates Sharpe zero and returned a valid-looking,
gate-changing PBO. Every balanced half must contain at least two observations for sample standard
deviation. Finite constant candidates remain valid and retain Sharpe zero. This changes no valid
finite statistic or threshold, so calibration identity does not advance.

ADR-189 validates original PBO source dtype before float conversion (signed/unsigned integer or
real floating point only), after matrix-shape precedence. Boolean, complex, string, object and
temporal matrices cannot be reinterpreted as return evidence. Valid CSCV/tie arithmetic, finite
constant candidates, strict pbo_max and calibration identity remain unchanged.

ADR-200 retains the original source mask through PBO's finite-evidence guard. Any masked
observation is missing evidence, even when underlying storage is finite; materialization
must not replace it with that storage. All-false masks preserve exact CSCV and tied-column
permutation results. Structural precedence, history, ranks and calibration identity remain.

ADR-201 refuses nonconstant native Sharpe moments when means/dispersion/quotients are
nonfinite or dispersion underflows to zero, under either ordinary or strict error mode.
Exact constant columns get their defined zero score before moment arithmetic; rounded
false variance must not manufacture a dominant flat candidate (FINDING-138/139).
This corrects finite constant-only PBO results, so accounting identity advances to
`whole-search-budgeted-robust-iqr-pbo-ties-constant-v6`. Old calibration cannot match
the corrected procedure; new rates are unmeasured until an authorized sole-writer refresh.
Native representable nonconstant scoring, tie rules and all thresholds are retained.

ADR-289 / FINDING-238 corrects positive finite native PBO dispersion only for
original Float64 nonconstant columns with nonzero native means, strictly one sign
and maxabs<=2*minabs. The inclusive factor-two relation certifies exact first-value
subtraction. Original full-block mean/layout and all native refusal guards precede
normalized-difference STD and one frexp/ldexp per-bar quotient restoration.
Public original dtype provenance reaches every cached subset; integer/narrow/wider
sources and noneligible columns keep prior results. Constants, CSCV geometry,
ties, masks and strict pbo_max stay. Eligible finite positive partial-underflow STD
can change; zero/nonfinite native STD still refuses. The frozen synthetic matrix
changes PBO1/3 to exact-variance2/3, crossing the existing gate; no actual graduate
is established. Known-native-mean exact variance controls do not certify arbitrary
numerator accuracy or universal correct rounding/ranking. Primary Sharpe centering
is separately corrected by ADR-290 within its own certified range; OOS centering
remains separate. This PBO correction advanced accounting to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-v12`;
current distributions are unmeasured and historical v11/frozen v10 evidence stays
attributed. No cohort redraw, threshold, selector or generated-record changes.

ADR-290 / FINDING-239 corrects original native/classic Float64 primary Sharpe
only after native positive STD/nonzero mean/finite score acceptance without
detected STD/mean/ratio failure. Same-sign nonzero observations with maxabs<=2*minabs
certify exact anchor subtraction; normalized-difference sample STD and separated
mean/scale exponents retain the actual accepted native mean. Existing ADR-286
underflow recovery, zero means, other families and mixed/zero/wider-spread native
paths stay. The derived iid interval follows corrected Sharpe with unchanged
formula/assumptions; other metrics and ADR-289 PBO remain. Known-native-mean exact
variance controls do not certify arbitrary numerator accuracy or universal
rounding. Accounting now advances to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-sharpe-exact-translation-v13`;
current distributions are unmeasured, historical v12/v11 and frozen v10 retain
executed identity, and no threshold, cohort or generated-record changes occur.

---

## 3. Walk-forward evaluation (ADR-038)

`app/validation/walk_forward.py`. Expanding window: train on [0, k), test on the next block,
step forward. `walk_forward_splits` returns `list[(train_idx, test_idx)]`;
`walk_forward_evaluate(performance, splits)` then **selects the train-block argmax config and
scores it on the following test block**, returning `mean_oos_sharpe`, `consistency` (share of
windows with a positive OOS Sharpe) and Pardo `efficiency`.

Train-only selection gives a causal forward-window diagnostic alongside the locked holdout.
Each window scores the chosen config's continued full-history return path. Engine-supplied net
returns include that config's internal turnover; slices do not reconcile entry or switching
trades for one account adopting successive configs (ADR-293 / FINDING-246). Causal signals
justify fixed-config continuation, not equivalence to flat-start window backtests or a
self-financing switched portfolio. `mean_oos_sharpe` remains the equal mean of annualized window
Sharpes, not Sharpe on concatenated OOS returns. No separate WF threshold gates graduation;
nondefault `select_by="walk_forward"` may rank families by this statistic (ADR-069), while the
default remains observed selection. Arithmetic, averaging, selection, thresholds and v14
accounting remain unchanged; historical measurements retain this diagnostic meaning.

- **Invariant**: `max(train_idx) < min(test_idx)` for every split — never uses future data.
- **Invariant**: a split's selection depends only on its own train rows. Stated PER SPLIT: the
  train window EXPANDS, so a later split legitimately absorbs an earlier split's test rows.
- `efficiency` is `None` when mean in-sample Sharpe ≤ 0 — a ratio of two negative Sharpes is
  positive and would read as "efficient" while both halves lost money.

ADR-197 validates caller-supplied split rows at evaluation: nonempty one-dimensional integer
arrays, nonnegative in-range unique ascending rows, and train entirely before test. Invalid
geometry is refused without repair. Generated splits, singleton blocks, causal gaps and earlier
test blocks entering later expanding train windows retain the same selection/score/benchmark.

ADR-332 validates original nonboolean Integral splitter counts and normalizes
them before geometry: K before K+1, N before its relationship check, and explicit
min_train after that check before fold/base arithmetic. None remains the default
fold size. Fractional bases otherwise generate overlapping rows; bounded unsigned
counts can wrap into empty/out-of-range folds (FINDING-279). ADR-197 already
refuses those malformed rows at evaluation; no accepted leaky score or production
occurrence is established. Existing valid Python geometry, defaults, scoring,
selection, thresholds and v14 remain unchanged. No new N/K allocation cap or
strategy/source causality certification follows from this count boundary.

ADR-199 makes both OOS evaluators validate original i/u/f numeric source dtype and complete
finite float64 matrix/control evidence before selection or singleton/flat/fold-drop shortcuts.
Explicitly masked missing observations are refused before masks can disappear on materialization.
Valid numeric, unmasked, constant/singleton and absent-control behavior and formulas remain.

ADR-248 additionally retains original train/test index masks at both OOS
boundaries. A masked storage index is an unidentified observation, even when its
underlying integer passes geometry. Any true mask refuses before selection,
benchmark scoring or empty purged-fold dropping. Kept geometry checks retain
precedence; all-false masks and complete canonical splits keep exact results.
FINDING-197 is synthetic direct-call evidence, not observed production leakage.
No filling, filtering, score, threshold or calibration identity changes.

ADR-202 assigns exact constant diagnostic blocks their defined zero score before moments,
and refuses nonconstant unmeasurable mean/dispersion/annualized scores with ValueError.
The original one-dimensional arithmetic/order and singleton convention are preserved;
train selection, selected test and controls use the same guard. Rounded constant scores
change finite diagnostics, so identity advances to `whole-search-budgeted-robust-iqr-pbo-oos-constant-v7`.
Historical null summaries below describe their recorded earlier procedure; replacement
diagnostic distributions are unmeasured until an authorized sole-writer refresh. No thresholds change.
- **Measured under the null (2026-08-19, N=200/mode):** median +0.15 (iid) / +0.33 (bootstrap:SPY),
  p95 +0.78 / +1.05. **Below ~1.0 is indistinguishable from noise.** The bootstrap null sits higher
  because the selection earns *drift*, so any future gate on this must be stated against
  buy-and-hold on the same windows, never against zero (ADR-038 §Measured).

ADR-291 / FINDING-240 corrects original represented Float64 OOS scores only after
all existing native moment/annualized-score guards. Independent original matrix
and benchmark flags (kind f, itemsize 8, including byte order) reach every train,
selected test and kept control block. Same-sign nonzero maxabs<=2minabs certifies
exact anchor subtraction; normalized difference ddof1 STD and separated exponents
retain the actual accepted native mean. Mixed/zero/wider-spread, native zero mean,
other sources and all native failures retain their prior results/refusals.
Positive partial-underflow native STD remains eligible under the existing ignore
policy. The frozen synthetic fixture selects config0 instead of wrong config1;
no actual graduate, leakage or market effect is established. Geometry, argmax
first-index ties, benchmark windows, folds and aggregation stay. This does not
certify arbitrary numerator precision or universally exact rankings/rounding.
Accounting advances to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-anchored-dispersion-pbo-exact-translation-sharpe-exact-translation-oos-exact-translation-v14`.
At adoption current distributions were unmeasured; F241 subsequently supplies
one local iid-normal cohort and F243 separately supplies one fixed Student-t5 stress.
Power/bootstrap remain unmeasured; historical
v13/v12/v11 and frozen v10 retain executed attribution without rerun/redraw/pooling
or relabeling. Primary ADR-290 and PBO ADR-289 contracts remain independent.

---

## 4. Purged K-Fold CV (ADR-039)

`app/validation/purged_cv.py`. López de Prado (2018) ch. 7. K folds; for each test fold, **purge**
training indices within `embargo` of the test fold (overlapping labels leak), and apply the
embargo after the test block. `purged_cv_evaluate` then selects on the purged train rows and
scores that choice on the fold, reporting the mean, the **dispersion across folds**, consistency
and the embargo used.

`lookback_embargo(configs, floor)` sizes the embargo from the grid's largest integer parameter (a
documented proxy for the longest window) rather than a constant — the old fixed `embargo=2` purged
~1% of the contaminated region for a 200-bar strategy.

**Read it NEXT TO walk-forward, never instead of it.** A fold's training rows include data from
*after* its test block, so purged CV is not causal. It reports fold scores under the declared
lookback-proxy gap and retained training regimes; this geometry alone does not certify source
independence or historical point-in-time availability. Measured under
the null it scores systematically ABOVE walk-forward (median +0.26 / +0.39; p95 +0.88 / +1.06) —
that gap IS the optimistic bias, and it is why the two are never averaged.

- **Invariant**: no training index lies within `embargo` of any test index (declared row-gap geometry).
- A sample too short to hold the folds plus an honest embargo reports `purged_cv=None` plus a
  flag. Shrinking the embargo to fit would emit a leaky number labelled "purged".

FINDING-291 aligns the public About explanation with these contracts: CSCV splits
time observations and ranks configurations, null PBO depends on the supplied
candidate set, purged training may include later rows, and walk-forward reports
continued fixed-config windows without reconciling account entry/switching trades.
The reporting correction changes no diagnostic arithmetic, thresholds or API fields.

ADR-291 applies the same certified OOS scalar correction described in §3 to
purged train/selected-test scores and its independently sourced benchmark on kept
folds. Embargo, intentionally noncausal training, dropping and pairing remain.

ADR-198 verifies the evaluator's declared nonnegative integral embargo against supplied fold
rows: integer/bounded/unique ascending arrays, contiguous kept test blocks, and no train row
inside the closed embargo interval. Empty integer folds still drop; before/after training remains
valid outside that interval. No estimator, lookback sizing, threshold or causal-policy change.

ADR-330 validates the splitter's original n_splits, embargo and n_obs as
nonnegative nonboolean Integral counts immediately before their existing checks,
normalizing each to Python int before geometry. Unsigned boundary wrap could
otherwise retain a fold's own test rows (FINDING-277); ADR-198 already rejects
those rows at evaluation and ADR-325 normalizes panel requests upstream.
Existing Python-int geometry, defaults, scoring, thresholds and v14 remain.
No accepted leaky diagnostic, production occurrence or false graduate is
established. The lookback proxy and broad engine error attribution remain
separate; this count guard does not certify feature support or independence.

ADR-331 includes all original nonboolean Integral strategy parameters in the
existing largest-integer lookback proxy, converting retained values to Python
int. NumPy int64 windows otherwise vanished into the floor while identical
native-int signals received their full proxy embargo (FINDING-278). Actual
ValidationEngine reports reproduced the discrepancy; ADR-198 cannot infer an
omitted lookback from valid smaller-embargo rows. Floor operands and ignored
parameter types remain unchanged. Search/calibration reach this helper, but
shipped native catalog grids retain their exact values and accounting-v14.
No production occurrence or false graduate is established; FINDING-272's
numerical-history and general proxy limitations remain.

ADR-333 distinguishes genuine purged-fold absence with
NoUsablePurgedFoldsError(ValueError), raised only by the evaluator's existing
final empty-result check after all evidence/geometry validation. ValidationEngine
catches only that subtype. Genuine null/count0/geometry flags stay; numerical
and structural refusals propagate rather than receiving a false insufficient-
history explanation (FINDING-280). Finite scores, thresholds and v14 estimators
remain. Affected longitudinal/calibration inputs can now become recorded errors
and leave completed denominators; unchanged formulas do not certify unchanged
rates. No calibration, artifact rewrite or frozen-cohort replay is implied.

**ADR-078: it carries a drift control, exactly as walk-forward does.** `purged_cv_evaluate` takes
an optional `benchmark` of per-bar returns and reports `mean_oos_hold_sharpe` — buy-and-hold scored
on the same folds, averaged over the folds that were KEPT (a fold purged away entirely is dropped,
and a benchmark averaged over blocks the strategy was never scored on is not the paired quantity).
`ValidationEngine` passes the same series it passes to walk-forward, `run_search` stores it as
`Experiment.purged_cv_hold_sharpe`, `calibrate_gate` collects
`NullCalibration.purged_cv_hold_sharpes`, and `compare_with_null` emits a `purged-CV excess` row
beside the raw one.

**The two hold Sharpes are NOT interchangeable.** Purged CV tests every index exactly once, so its
control covers the whole searched window; walk-forward's test blocks skip the first train block, so
its control covers a suffix. Substituting one for the other mixes a correction measured on one
index set into a statistic measured on another — which is the confound both exist to remove.

ADR-068 had deferred this on the grounds that "purged CV's folds are not a prefix-ordered benchmark
window". ADR-078 overturned it: fold ordering is a fact about SELECTION, and buy-and-hold has no
config to select. The 7,400-bar nulls and the first 88-symbol matched real cohort now carry the
control (FINDING-017). Real paired excess is `-0.000`; its difference from the bootstrap null is
`+0.000 [-0.048, +0.002]` and from iid-normal is `+0.000 [-0.048, +0.000]`, clustered by symbol.
Both intervals span zero. The retained 5,400-bar nulls remain legacy and correctly unmeasured.

**ADR-080 applies to both controls.** Walk-forward and purged-CV OOS/hold values share one
per-symbol calibration record, remain independently nullable, and are paired only within that
record. Shard merge rejects mixed legacy/paired generations and duplicate symbols. This changes no
raw distribution or gate; it prevents complementary missingness from becoming cross-symbol excess.

---

## 5. ValidationReport

ADR-159 makes the report a durable claim rather than a shallowly frozen object. All headline and
nested diagnostic scalars must be finite; split/fold counts and derived summaries must agree with
their records; present diagnostic counts must agree with the top-level counts; and list/map fields
are defensively copied into immutable JSON-compatible containers. The graduation gate and API
publication boundary reconstruct the authoritative model before use, closing unchecked Pydantic
copy bypasses without changing any diagnostic calculation, pass formula, or threshold.

ADR-160 applies the same identity rule to the deterministic graduation output. `GateResult.passed`
must equal all six component booleans, reasons are defensively immutable, required MinTRL is
non-negative and non-NaN (positive infinity remains meaningful), the gate version is non-empty,
and structured holdout Sharpe/length are paired. All 4,055 committed JSON occurrences satisfied
these invariants at the compatibility audit. Probability-DSR counterfactual inference reconstructs
its complete artifacts before reading the embedded result; no gate predicate or threshold changed.

ADR-162 makes the shared trial and graduate leaves authoritative outside an enclosing experiment as
well. Trial parameters cannot mutate, every statistic is finite, PBO/stability/probability DSR stay
within `[0, 1]`, and nullable diagnostics still mean not measured. A graduate requires a passing
gate, finite wealth-preserving holdout evidence, positive length, and exact agreement with the
gate's structured holdout fields when present. Search repricing revalidates the concrete trial
subtype. All 116,919 committed trial-shaped records and 250 graduates passed the compatibility
audit; no estimator, selector, predicate, threshold, or JSON shape changed.

`app/validation/report.py` — Pydantic model aggregating the above for one strategy:
`strategy_name`, `observed_sharpe`, `deflated_sharpe`, `pbo`, `n_walk_forward_splits`,
`n_purged_folds`, `walk_forward` (ADR-038) and `purged_cv` (ADR-039) — both nullable, where
**null means NOT MEASURED and must never be read as a measured zero** — `flags` (list of
human-readable cautions), `passed` (computed: e.g. `pbo < 0.5 and deflated_sharpe > 0`). The
report is the MVP deliverable rendered by the frontend (Phase 5).

For longitudinal searches, both diagnostics are also recorded per `Trial` (`walk_forward_oos_sharpe` /
`purged_cv_oos_sharpe`) so they reach the research pool, and summarized for gate passers by
`scripts/pool_report.py` — which prints them next to `data/null_calibration/` so the
"passers vs null" comparison is two commands, not a fresh script every session.

ADR-321 adds family-local walk-forward evaluation to new cross-sectional backend
searches. Each complete allocated family matrix uses the unchanged evaluator and
search-only `asset_returns(in_sample).mean(axis=1)` benchmark on identical test
windows. Full results remain on ephemeral reports; inherited trial means persist
with experiment `walk_forward_method`, `walk_forward_hold_sharpe`,
`walk_forward_n_bars` and `walk_forward_n_splits`. The recognized method requires
complete finite family means, a common paired benchmark and valid actual geometry.
Historical method-null/unpaired constructors remain readable without backfill.
Compact scalars cannot independently reconstruct per-split selection or prove
source provenance; producer checks establish common geometry and pairing.

Selection within a family is train-only; the overall winning family is still
selected using the complete search sample. Its family score does not measure
train-only cross-family selection. Static fundamental maps are conditional supplied
snapshots, not historical point-in-time information. Scores average continued
config-window Sharpes with existing internal costs, without account entry/switch
reconciliation. The equal-weight benchmark includes the existing initial zero
and no extra turnover-cost model. Measurement errors propagate and can now refuse
a search; primary gate-bearing results stay exact on measurable controls.

ADR-325 adds restricted family-local purged evaluation to complete new search
producers for native Float64 panels and shipped configurations of xs_momentum,
xs_reversal and xs_short_term_reversal_1m. Stable known-factory identity and
actual allocated parameters establish the supported direct-shift recipe; matching
names or grids alone cannot certify custom replacements. All other factories,
static maps, parameter domains and dtypes retain explicit unsupported evidence
and remain eligible for unchanged primary search. Historical absent evidence and
unpaired inherited scalars remain legacy; no score or method is backfilled.

For the supported recipe, the net-return direct-price lag is lookback+skip+1
(momentum) or lookback+1 (reversals), including previous weights and turnover.
Use the maximum over actually allocated configs and E=max(original user floor,D).
Original floor/fold counts are nonboolean Integral evidence. The unchanged
evaluator scores the existing matrix against the search-only equal-weight
benchmark on that family's actual kept folds. Family-specific embargoes need
family-specific controls, never an invented common benchmark. The per-trial
purged_diagnostic binds recognized method/status, request geometry, support rule,
allocated lag, embargo, kept ordinals and measured score/control. Its mean must
match inherited purged_cv_oos_sharpe. Current unsupported/no-usable-fold branches
carry no scores and ephemeral count0; measured reports carry actual results/counts.
Unmeasurable evaluator errors propagate; no usable folds is explicit geometry,
not a generic exception catch or a reason to shrink E.

Original integral metadata and exact kept-set coherence validate without arrays
using Python-integer prefix/suffix geometry. Models, immutable nested claims and
store reconstruction enforce the same complete branches, same experiment request
and attributed WF-bar agreement. Compact evidence does not independently replay
all allocated configs, selected fold positions or source provenance. Primary/WF
source checks precede unmeasured classification. Scores are continued-config
fold means with internal costs, intentionally noncausal later training, no account
switching reconciliation and no separate graduation threshold. The overall winning
family is still chosen on the whole search sample; train-only cross-family
selection is not measured. Source-operand
separation does not establish independence, PIT universe availability or panel
calibration. Existing gate-bearing results stay exact on measurable controls.

ADR-327 publishes the exact inherited PCV scalar and frozen per-trial diagnostic
through the read-only API. Trial scalar/status binding, complete common request
geometry and attributed WF-bar agreement also validate at the public view boundary.
Family-specific embargoes, kept folds and benchmark means stay distinct. Full
source reconstruction retains the stronger finalist/domain checks; reduced wire
views establish structural coherence, not source provenance or allocated replay.
Historical absent evidence remains null or unpaired, without backfill.
ADR-328 also preserves this evidence at the client boundary and displays each
family's mean, paired control, explicit unmeasured state and collapsible actual
fold geometry. Safe parsed JavaScript counts use exact internal BigInt geometry
without count-sized arrays; larger Python integers refuse rather than appearing
as rounded geometry. This concerns the published integer contract, not arbitrary
raw JSON token preservation. The UI keeps server verdicts and scientific caveats.
FINDING-265 remains open for unsupported-family measurement. Legacy geometry-only
counts retain their historical meaning.
No longitudinal v14, threshold, generated file or frozen calibration/cohort change.

FINDING-272 qualifies that prospective design: nominal expression windows do not
certify exact computational source isolation for shipped low-volatility and
risk-adjusted-momentum factors. A deterministic old-price perturbation changes
late signals and ranked portfolio turnover despite identical complete nominal
price windows. This is consistent with rolling numerical state, not a proof of
compiled internals or arbitrary-length influence. It establishes neither future
leakage nor an incorrect existing cross-sectional PCV score. Before integration,
a separate ADR must choose and disclose nominal-support isolation, audited local
arithmetic, or restricted-family support; none is adopted by this evidence note.
Hidden defaults and combined windows require operator-chain analysis, and paired
benchmarks must follow each family's actual kept folds. Static snapshots retain
their point-in-time limitation. Factor arithmetic and identities stay unchanged.

ADR-322 publishes these exact persisted fields through the read-only API and panel,
validating complete measured metadata at the wire boundary. Missing scores remain
not measured; historical method-null scalars display as legacy, unpaired, without
invented benchmark attribution. The panel states the family-selection, snapshot,
continuation/account-cost and mean-window limitations above.
Historical null stays unmeasured, never zero; longitudinal calibration does not
certify this panel diagnostic. No selector, threshold or v14 change is made.

**Neither gates anything.** Both are diagnostics with an explicit, measurable trigger for
revisiting, recorded in their ADRs. Do not add a floor without arguing it from the null
distribution (charter §4).

Parameter stability and regime analysis (`parameter_stability.py`, `regime_analysis.py`) are
secondary and added after the core four are solid.

ADR-317 / FINDING-268 validates original parameter-stability observations before
Float64 conversion: nonboolean Real scalars with finite binary64 inspection,
then exactly one converted dimension before reductions. Minimum-two-config
precedence and all existing numerical operations remain. Decimal and arbitrary
coercible non-Real objects are intentionally unsupported; signed integers,
Fraction, NumPy reals and one-dimensional real sequences retain the estimator.
Native finite-input reduction overflow/underflow and finite projection precision
remain separate at that input boundary. No production corruption is established;
current callers build computed Sharpe lists. No threshold, search identity or
accounting-v14 change.

ADR-324 / FINDING-274 separately refuses nonfinite native parameter-stability
mean/sample STD and CV before issuing a summary. Finite observations could yield
infinite dispersion yet a finite zero accepted by ValidationReport. Every original
numerical expression, epsilon and clipped reciprocal remains. Under ignore/warn,
nonfinite reductions now raise ValueError; native warnings still occur, and native
raise-mode exceptions can preempt the guards unchanged. Caller NumPy state is not
modified. This narrows the successful arithmetic domain without recovery or
repricing accepted finite-intermediate estimates. No actual finite-STD/CVInf
witness was established; the CV guard specifies finite coefficient evidence.
Native underflow/zero dispersion, finite precision and direct dataclass construction
remain separate. No production occurrence, false graduate or calibration impact
is established; thresholds, schemas, search identity and v14 stay unchanged.

ADR-329 / FINDING-276 separately refuses zero native sample STD when the already
converted finite Float64 observations are unequal. The exact-equality check runs
after existing finite reductions and before unchanged CV. Exact constants and
signed zeros stay valid; ignore/warn now refuse the contradictory zero summary,
native underflow warnings remain, and native raise exceptions can preempt the
guard. No caller policy, numerical expression, epsilon or estimator is replaced.
Exact Fraction-centered variance confirms representable positive dispersion for
three tiny-input witnesses; the existing regularizer still rounds their score
to one, so no gate flip or production impact is established. Refusal is
conservative for subnormal cases whose exact STD cannot round to a positive
Float64 value. Positive partial underflow, original projection collapse and
positive computed dispersion from rounded centering of constants remain separate.
Report/direct constructors, thresholds, search identity and accounting-v14 stay.

ADR-318 / FINDING-269 requires original nonnegative nonboolean Integral regime
horizons through the unchanged shared count helper, normalizing to Python int
before alignment. Negative pct_change periods labeled earlier strategy returns
with future market prices at direct entry. Fixed default20 and all numerical
operations stay; zero retains the degenerate all-bull horizon on finite positive
sources. Current production caller uses20; no affected production result is
established. Regime partitions remain retrospective diagnostics, not executable
switching accounts. Calendar/source/alignment validity and arbitrary huge pandas
horizons remain separate; no threshold, schema, search identity or v14 change.

ADR-319 / FINDING-270 separately checks both whole original regime indexes for
unique ascending order after window validation and before alignment. Otherwise
positive positional horizons can use future calendar prices, and duplicate
alignment can repeat original returns. No sorting/deduplication or UTC/cadence
policy is added. Ordered generic/naive/aware, partial/disjoint, empty/singleton
sources retain existing behavior and all numerical statements stay. Normal
ValidationEngine already has backtest-calendar mitigation; no affected production
result is established. Source value/provenance and executable-account claims
remain separate; report schemas, thresholds, search identity and v14 stay.

ADR-320 / FINDING-271 refuses native matched strategy returns <=-1 immediately
after alignment and before regime calculations. Two negative gross factors
could otherwise publish +100%/+300% and survive report-entry validation despite
intermediate negative wealth. Original window/calendar precedence, unmatched
unsafe rows, empty/disjoint inputs and every solvent numerical operation stay.
This is a scored-factor domain, not liquidation or an executable switching
account; native product/projection, source-value and market-price limits remain
separate. Normal engine wealth checks mitigate its current route, with no
affected production result established. No schema/threshold/search/v14 change.


ADR-323 / FINDING-273 validates nonempty matched regime market prices after the
existing window/calendar/strategy-wealth guards and before pct_change. Real
nonboolean numeric dtype and complete finite positive native values are required;
object/Decimal/numeric-string containers are unsupported. Missing, zero and
boolean market sources could otherwise issue finite all-bull evidence accepted
by ValidationReport. Valid native/nullable numeric and extended-precision prices,
zero horizons, genuine warmup-bull behavior, empty/disjoint and unmatched invalid
numeric observations retain their behavior. Object dtype stays unsupported even
when its matched leaves are numeric. No Float64 narrowing or source repair is
added. Normal BacktestEngine already refuses the demonstrated malformed prices;
no affected production report or false graduate is established. Derived trailing
return arithmetic, provenance and complete-source policy remain separate. No
schema, formula, threshold, search/accounting-v14 or generated-record change.

ADR-326 / FINDING-275 adds a separate derived-sign contract: after the unchanged
trailing calculation, mature computed trailing<0 must agree with native current
price below its original lagged price. Positional native slices, without casts,
Series.shift or label alignment, retain large integer distinctions. Disagreement
refuses before labels and aggregates rather than silently publishing an all-bull
partition for descending native prices. Original source/wealth/calendar/count
checks, native warnings/exceptions, genuine warmup, zero and no-mature-row horizons,
and all accepted score expressions remain. This certifies only the bear/bull
partition, not magnitude or positive-versus-zero precision. Upstream PriceBar
float conversion can already erase distinctions; no recovery or source-provenance
claim is made. The public backtest engine does not reject the positive integer
witness, but no production occurrence, leakage or false graduate is established.
No report, shared metrics/engine, threshold, selector, v14 or generated record change.

---

## 6. Rank information coefficient (cross-sectional only)

`app/research/cross_sectional/ic.py`. ADR-035. Per-date Spearman correlation between the signal
cross-section at *t* and each asset's return from *t* to *t+1* — the same causality
`portfolio_returns` uses (rank on t, realize t+1). `summarize_ic` returns mean, std, IR (mean/std),
t-stat (IR·√periods), hit rate and period count.

- Answers the one question a dollar-neutral Sharpe cannot: **did the ranking carry information, or
  did two names carry the P&L?** At a 0.2 quantile over ~50 names each leg is ~10 positions.
- Dates with <2 ranked names, or zero dispersion on either side, are **dropped, not scored 0** —
  "not measurable" is a different observation from "no information", and zeroing biases the mean
  toward the null.
- **Diagnostic, not a gate.** An IC floor would change what graduates; per the charter that needs
  argued methodology with evidence, and no IC distribution exists yet. Trigger to revisit: ≥50
  cross-sectional trials with an IC, then compare gate-passing vs gate-failing distributions.
- The t-stat assumes independent periods, so it is **optimistic** for a slow signal whose IC series
  is autocorrelated. Newey-West adjustment is a noted, unbuilt follow-up.

Production panel acquisition is lineage-bearing as of ADR-138. Each requested vendor series must
cross the ADR-006 `ResearchDataset` boundary before it can enter the hunt. The persisted experiment
retains complete reports only for the columns surviving history/common-calendar filtering and one
ordered panel manifest binding those report identities to the selected search and executed code.

---

ADR-338 preregisters one distinct absorbing integer-price martingale null:
N200/7400bars, P0=128, symmetric integer ±1 until absorption at1, fixed
PCG64 seeds2026102107000+i and all7399 innovations drawn even after absorption.
Ideal next simple returns have conditional mean0 and state-dependent variance;
native price-ratio rounding is disclosed rather than certified as exactly zero.
Full34/defaultGate/budget200/refine/nper3/prior0/noStore search remains unchanged.
Exact protocol CI must precede source draw, all200 independently audited sources
must precede search, and a single7200s soft admission clock cannot renew.
Incomplete/error/interrupted cohorts are permanently no retry/resume/redraw/
rebudget/replacement; complete200/zeroerrors and independent final audits alone
permit separate graduation and combined-N200 strict ADR018 rates. At protocol publication
no actual cohort source or search existed. This is neither a replacement for frozen
cohorts nor ADR102 probability-gate/market-safety evidence. See ADR338 for exact
law, checkpoint identity, inference limits and pre-draw controlled-test evidence.
FINDING-286 records the subsequent complete execution at75bddc05: all200 original
sources/searches, zeroerrors/zero graduates/zero strictADR018 survivors; combined
N200 bar1.3432393159670402 and one-sided95% zero-event upper1.4867% per endpoint.
Independent final source/model/config-count/selection/fixed-holdout/joint-gate/
merge/count audits PASS; five diagnostic fields each200/200 measured. Twenty-seven
paths absorbed by the final bar. This law-only result is not a zero population-rate
guarantee, general-null/market/power/bootstrap certification, a pooled denominator
or threshold permission. No frozen cohort was rerun, repaired or replaced.

## 7. Gate calibration — Type-I error, power, and the detectable-edge frontier

The three sections above describe statistics. This one describes what has been measured about the
**gate as a whole**, which is what any claim made with it actually rests on. Re-run every part of it
after any `GateConfig` change; each is token-free cloud compute.

### 7.1 Type-I error (ADR-036/037) — `app/research/lab/calibration.py`

README measurement summaries retain historical cohorts and numeric figures,
with explicit recorded-procedure/snapshot attribution (ADR-294). They do not
certify the current default. Reference scores are stated strategies, selected
in-sample ratios are not optimal-edge fractions, and the frontier is a conditional
single-bar normal-model approximation. Near-zero references and category-gap/SE
comparisons do not prove absence of edge or rule out another selection method.
See FINDING-155/159/164 and F159's README follow-through for the public wording.

`calibrate_gate` runs the UNMODIFIED search + gate over symbols with no edge by construction:
`iid_normal_null` (textbook) and `bootstrap_null` (resamples a real symbol's bars, preserving fat
tails and vol, destroying serial structure). `null-calibration.yml` shards it and commits
`data/null_calibration/*.json`.

- Current published result — run 32354284731 (2026-08-20), ADR-046/047/048 accounting **with
  ADR-050's IQR dispersion**, judged at the hunt's own **5400-bar** history (ADR-051), N = 200 per
  mode: **0 false graduates on both nulls**, **0 clear the ADR-018 bar**, max DSR **-0.415 iid /
  -0.269 bootstrap**. The prior 1.0% / max +0.92 result belongs to the coarse-only, uncapped
  accounting procedure.
- Current 7,400-bar result — run 33287465013 (2026-08-30), N = 200 per mode: **0 false graduates on
  both nulls**, **0 clear the bar**, max DSR **-0.368 iid / -0.253 bootstrap**, `deflation_bar`
  1.343. Carries ADR-068's paired hold distribution; the 5,400-bar pair never will.
- **Only the iid-normal null is bit-reproducible across days; the bootstrap null is not, by
  construction.** Re-running the identical dispatch on 2026-08-30 reproduced iid's max DSR to the
  digit (−0.368) while bootstrap's moved −0.261 → −0.253. `_source_frame` fetches SPY up to *now*,
  so the resampled marginal changes every time the real series gains a bar. That is not drift in the
  gate and not a defect: it is the null tracking the symbol it is built from. Quote a bootstrap
  number with its run id, and never treat a small move in it as a change in the pipeline.
- **Every calibration is judged at the hunt's history length, not a round number (ADR-051).** The
  drivers previously planted 3000 bars while `scripts/shard_hunt.py` starts at 2005-01-01 and real
  names carry ~5400. `n_bars` is now a `--n-bars` driver flag, a workflow input, and a recorded
  field on both `NullCalibration` and `PowerCalibration`; an empty list means an artifact predating
  the field, never a run that saw no bars.
- A shard cannot report a final answer — the deflation bar grows with the TOTAL symbols searched,
  so `merge_calibrations` re-judges every false graduate at the combined N, and refuses to merge
  across gate config versions or null modes.
- Null experiments are NEVER written to the research pool: they would inflate the MinTRL
  denominator for real hypotheses.
- Calibration identity includes the resolved grids AND a trial-accounting-method version
  (ADR-044/046). The same hypotheses priced by a different DSR denominator are a different measured
  procedure and must not reuse an old Type-I/power artifact.
- Calibration runs production's adaptive winner-family refinement by default (`refine=True`, span
  0.25) and records those inputs in both the artifact and search identity (ADR-047). Runs before
  ADR-047 were coarse-only and do not measure the selector daily discovery deploys.
- Production enforces `GateConfig.trial_budget` across coarse and refined candidates (ADR-048).
  Families are canonicalized, receive a two-config PBO minimum, and share remaining capacity by
  fair water-filling; oversized grids use deterministic maximin parameter-space coverage. The
  refinement pass is one family-sized bucket inside the same cap. Calibration identity hashes the
  budgeted grids, refinement reserve, and allocation-method version. Pre-ADR-048 artifacts measure
  the uncapped 667-config coarse family and are stale for production.

### 7.2 Power (ADR-041/042) — the Type-II half
`measure_power` plants an edge of MEASURED (never derived) strength and counts detections in two
tiers: graduated, and cleared the ADR-018 bar.

- `autocorrelated_edge(phi)` — AR(1) on returns. phi < 0 is lag-1 mean reversion, phi > 0 trend.
  **Current published curve** (run 32355803804, production parity at the hunt's 5400-bar history):
  **64% at oracle 3.90 (32/50 clear the ADR-018 bar), 34% at oracle 3.97 reverting (17/50), 14%/22%
  at oracle ≈ 2.6, 0% at oracle ≈ 1.3.** The intermediate 0/50-everywhere result was measured on
  3000 bars and is superseded (ADR-051) — do not requote it.
- `mean_reverting_edge(half_life, deviation_share)` — a random-walk level plus an AR(1) deviation,
  i.e. band reversion at a stated horizon. Parameterized by the deviation's SHARE of return
  variance so realized volatility is constant across horizons; otherwise a horizon sweep moves the
  volatility and the effect size with it. Run 32355806443 measures **0/50 at every horizon** at
  oracle ≈ 2.6 with **DSR passing 0/50 in every cell**, while AR(1) reversion at the SAME oracle is
  detected 22% with DSR passing 39/50. The difference is capture — **20.7% / 21.8% / 24.6% / 37.2%
  at half-lives 1 / 2 / 3 / 5** against 55.1% for AR(1) — so this is what the catalog can express,
  not what the statistics permit. ADR-042's "the asymmetry was the horizon, not the family" reading
  describes the pre-ADR-046/047/048 procedure at 3000 bars and does NOT describe production: at
  full history the horizon does not rescue band reversion.
- These always-on synthetic processes measure power under their stated source laws.
  Their rates do not establish a bound on unmatched real-market power (FINDING-164).
- ADR-049 records per-component pass counts (`dsr`, `pbo`, `stability`, `mintrl`, `holdout`,
  `beats_buy_and_hold`) because a composite zero cannot identify its own mechanism. Empty counts on
  a legacy artifact mean attribution was not preserved, never that every component had zero passes.
- Diagnostic runs 32341906980/32341908789 found **DSR 0/50 in all 12 cells**. At phi +0.30,
  PBO passed 43/50, stability 40/50, and MinTRL/holdout/beat-buy-and-hold 50/50. FINDING-006 isolates
  the cause: whole-search DSR estimates null dispersion from the current candidates, so the planted
  signal widened `sr_std` from 0.510 (matched iid seed) to 1.703 and raised the haircut from 1.410
  to 4.698 against observed Sharpe 2.937. Do not lower `dsr_min`; a null-consistent dispersion
  decision requires its own ADR and full recalibration.
- ADR-050 replaces whole-search sample standard deviation with a Normal-consistent IQR scale. Its
  refresh has now landed on all three workflows (Type-I 32354284731, power 32355803804/32355806443)
  and the numbers above are that refresh. **Any further change to the estimator, the catalog, or
  the grids invalidates all three again — re-dispatch them together, at the same `n_bars`.**
- Effect size is bounded by the horizon: only `(1-rho)/2` of a deviation's variance is predictable
  one bar ahead, so slow band reversion cannot reach a large oracle Sharpe at equity volatility.
  Read half-lives ≥ 10 as a statement about that ceiling, not about the catalog.

### 7.3 The detectable-edge frontier (ADR-043) — `app/research/lab/frontier.py`
The frontier inverts a conditional iid-normal asymptotic model for crossing one bar:
`SR_true = bar(N, T) + z_p · SE(SR_true)`, with `SE = sqrt((1 + SR²/504)/T)` (Lo 2002, annualized).
ADR-292 / FINDING-244 replaces eight fixed iterations and a bounded erf quantile with
standard-library inverse-normal tails and exact-Fraction existence classification.
The open unique inverse domain is `abs(z_p) < sqrt(504*T)`; a private Decimal160
context evaluates stable signed root algebra. Boundary/nonunique/unattainable
requests or nonfinite/unrepresentable evidence raise ValueError; supported lower
powers retain signed solutions and power .5 returns the exact original bar.
This is not composite pipeline power, and its gap from measured calibration power
does not isolate capture from other model/pipeline differences. Shared standard-error,
bar, thresholds, reference scoring and v14 accounting are unchanged. At `SR = 0`
that SE is exactly the `sqrt(1/T)` in `expected_max_sharpe_under_null`.

FINDING-281 qualifies that algebraic null substitution and the bar's source
docstring: sqrt(2lnN) is a leading-order Gaussian extreme-value scale, not an
exact finite-N expectation or a cutoff calibrated to a specified alpha. Under
idealized iid Gaussian draws its single-bar exceedance probability is nonzero;
this is not measured composite-gate Type-I error or market evidence. Dependence
alone cannot certify elimination of selection luck. Runtime, thresholds and the
immutable historical ADR-018 stay unchanged.

ADR-334 extends ADR-292's previously deferred shared-SE original-scalar boundary.
sharpe_standard_error requires finite binary64-inspectable nonboolean Real
history, then its original positive-history check, then finite signed Real
Sharpe. Inspection never replaces operands; the exact native expression stays.
FINDING-282 records bool/nonfinite evidence acceptance; ordinary producer inputs
are mitigated by native/validated callers, with no production or rate claim.
Native square wrapping and derived arithmetic remain separate and unresolved by
this slice. Zero squares and some tiny floating underflow are legitimate with
the additive-one model. Thresholds, v14 estimators and frozen records remain.

ADR-335 separately resolves the integral-square defect (FINDING-283). After
original validation, the native square of an Integral score must itself be
Integral and equal the exact Python-int square; mismatches refuse before
division/sqrt. Python integers serve only as an inspection oracle, preserving
native calculation operands, warnings and exceptions. Safe squares and integer
zero remain valid; custom nonintegral square results conservatively refuse even
when exactly valued. Floating overflow, precision and final nonfinite/zero
integrity remain separate open work. Twelve previously wrapped scalar controls
intentionally become refusals; unaffected scalar/frontier evidence remains.
No threshold, score cap, model, fingerprint, v14 or historical-data change.

ADR-336 separately refuses nonfinite or nonpositive returned SE (FINDING-284).
Finite native inputs can overflow the square or history division and return
infinity despite a representable exact-model answer. In particular zero Sharpe
with Python history 2**-1074 has exact SE 2**537. The unchanged native formula
now binds and checks its final result; warnings and exceptions still propagate
without catches, normalization or intermediate representation restrictions.
Tiny square underflow remains valid when the final uncertainty is measurable.
Positive uncertainty is a preventive model contract, not an observed ordinary
native zero-SE finding. This refuses unsupported results without recovering them
or certifying finite precision, arbitrary custom operators or every intermediate.
Ordinary producers mitigate exposure; no affected production rate is established.

- Current design (607 symbols, 4.3-year holdout): a **true annualized Sharpe of 2.13** is needed to
  clear the bar 80% of the time. Printed by `scripts/pool_report.py` and by the dashboard's
  `DeflationHeadline`, computed at report time and never stored.
- Design asymmetry, and the reason a session should not "fix" the funnel by trimming the universe:
  the bar moves as `sqrt(2 ln N)` in hypotheses but `1/sqrt(T)` in holdout length — **halving the
  universe buys ~4%, doubling the holdout ~29%.**
- None of this licenses moving a threshold. A frontier the universe cannot reach is a finding to
  state plainly, not a reason to lower the bar (charter §4).
- **ADR-063 acts on that asymmetry rather than restating it.** The search window was
  `datetime(2005, 1, 1)` copied into nine drivers, so `T` was a constant, not a property of the
  data — Yahoo serves 1990 for 74% of the discovery universe. `app/research/lab/history.py` now
  holds `SEARCH_HISTORY_START` (1990-01-01, the single-name search and the calibrations that mirror
  it), `RECENT_HISTORY_START` (2005-01-01, the paper book and anything needing only a recent tail)
  and `CALIBRATION_N_BARS`. Sampled median history goes 5,448 → **7,444 bars**, holdout 4.3y →
  **5.9y**, and the required true Sharpe 2.13 → **1.82** (1.63 for the 25% of names with full
  1990 history). No threshold moves: the ADR-018 bar and MinTRL are derived from `(N, T)` per symbol
  at judgement time, and the estimate's standard error falls with the bar. **Any calibration
  artifact at `n_bars=5400` describes a gate that no longer runs** — re-dispatch all three before
  quoting a Type-I error or a power number.

- **ADR-063 MEASURED (2026-08-29, `n_bars=7400`).** Type-I error unchanged: **0/200 on both nulls**,
  max DSR −0.261 / −0.368, `deflation_bar` **1.343** (was 1.722). AR(1) detection
  **34/22/0/0/14/64% → 40/36/0/0/24/66%** for φ = −0.3…+0.3 — four of four cells that had an edge to
  find rose, none fell, on a deterministic sweep. **The ADR's own criterion FAILED**: the cells it
  named (φ = ±0.1, band half-lives 3–5) are still 0%, because it could not distinguish "0% for want
  of power" from "0% because ADR-061 showed nothing is recoverable there". Phrase the next such
  criterion over the cells where the achievable oracle exceeds the requirement.
- **Capture FELL and that is a correction, not a regression.** Band net capture
  32/29/31/45/56/58% → **31/30/30/42/51/50%**; against the achievable oracle 105/103/104% →
  **97/98/88%** at half-lives 5/10/20. ADR-045's numerator is an in-sample maximum over the searched
  grid, so 1,600 more in-sample bars regress it toward the value it estimates. **The earlier, higher
  ratios carried more selection bias — quote the new ones.**

### 7.4 Capture efficiency (ADR-045) — recorded by `measure_power`
Every power run keeps the max-DSR finalist's in-sample Sharpe for every successfully SEARCHED
symbol, including non-detections. `PowerCalibration.capture_ratio` is median finalist Sharpe /
median oracle Sharpe. It returns null for legacy or partial artifacts rather than silently changing
the denominator.

- This is a **selected in-sample ratio**, not holdout capture. Selection can inflate it,
  but does not certify a bound on future capture or make low capture conclusive (FINDING-164).
- The grid searches 2-bar configurations at both horizons and they win at neither. Fast reversion
  is a smaller, noisier state-estimation target at held-constant oracle Sharpe, not a missing-window
  problem (ADR-045's correction to ADR-042).
- The historical heuristic combines capture ≈ 0.47 and required true Sharpe 2.13 to suggest
  reference Sharpe around **4.5**. It is not a certified detection frontier: the ratio is selected
  in-sample and the reference is qualified by FINDING-155/159. A new strength needs its own
  matched calibration; this heuristic never permits lowering a bar (FINDING-164).

**ADR-055: take the ratio against the NET oracle.** `oracle_sharpes` is cost-free; every finalist in
the numerator was charged 10bp on turnover by `BacktestEngine`, and the oracle is a *sign* strategy
turning over up to 1.19 per bar. `net_oracle_sharpes` charges it the same rate, and
`net_capture_ratio` is the comparable ratio. Both are pydantic computed fields, so they are served
rather than re-derived by each reader — do not reimplement the division in a script or a component.

FINDING-155 (session15, Open) corrects the interpretation of AR(1)'s reference
label: the generator's conditional mean is phi*lagged_return+drift*(1-phi),
while the current sign reference omits the drift intercept. Report its stored
gross/net scores as historical reference-strategy scores, not the true conditional-
mean optimum or a realized-sample maximum. Search/detection counts stay valid;
no oracle correction or historical artifact relabeling is claimed. Reference
capture/frontier narratives need this qualification until a governed correction.

| planted (2026-08-20, 5400 bars) | oracle | net oracle | detected | capture | net capture |
|---|---|---|---|---|---|
| AR(1) φ = +0.30 / −0.30 | +3.90 / +3.97 | +2.83 / +2.42 | 64% / 34% | 76% / 70% | 105% / 114% |
| AR(1) φ = +0.20 / −0.20 | +2.54 / +2.63 | +1.38 / +1.15 | 14% / 22% | 64% / 55% | 118% / 126% |
| AR(1) φ = ±0.10 | +1.25 / +1.33 | **+0.02 / −0.09** | 0% | 50% / 40% | *refused* |
| band, half-life 1 / 3 / 5 | +2.60 / +2.70 / +2.65 | +1.70 / +2.13 / +2.21 | 0% | 21% / 25% / 37% | **32% / 31% / 45%** |
| band, half-life 10 / 20 | +2.03 / +1.45 | +1.71 / +1.24 | 0% | 47% / 50% | 56% / 58% |

Three rules follow. (1) **Never quote "0% power at oracle 1.3"** as a missed achievable edge:
that is the gross historical sign-reference score, while its net score is near zero.
FINDING-155 prevents concluding that no tradeable edge exists from this fixed reference.
The ratio is refused when the net reference sits inside Lo (2002)'s Sharpe
standard error at the cell's own history length. (2) **Net capture above 100% is expected, not a
bug**: the numerator is selected in-sample from a grid while the denominator is a fixed sign rule
that pays to flip. This illustrates selection and reference dependence, not a certified bound
on future capture (FINDING-164). (3) ~~**The
band gap is the standing finding** — what the catalog cannot express is fast reversion to a
slow-moving level.~~ **RETIRED by ADR-061 (2026-08-20). Do not restate it in any form.** That
reading divided by an oracle computed from the process's LATENT deviation, which no causal strategy
can see. See §7.6.

**ADR-057/058: rule 3 above is now SHARPER — the fast-half-life gap is a RECOGNITION failure.**
`PowerCalibration.finalist_strategy_names` records which strategy won each searched symbol, so a
cell's finalists can be grouped by catalog category. On band reversion (5400 bars, 34-strategy
catalog + one probe strategy, superseded artifacts `2eede83f…`):

| band half-life | 1 | 2 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| finalists from **Mean Reversion** | 18% | 44% | 64% | 94% | 94% | 82% |
| net capture | 32% | 30% | 31% | 45% | 56% | 58% |

At half-life 1 the max-DSR search selects a **Trend** strategy 68% of the time on a process that is
by construction fast reversion. Capture tracks the recognition share. The AR(1) control from the
same dispatch recognizes perfectly (100% Mean Reversion finalists at φ = −0.2/−0.3; 66–74% Trend at
φ = +0.2/+0.3; a scattered mix only in the |φ| = 0.1 cells whose historical net sign-reference scores are near zero).

**ADR-059: the headline capture at fast half-lives is not the MATCHED capture.** Each cell now
records the best in-sample Sharpe per catalog category and serves `net_capture_by_category` under
the same ADR-055 refusal. Measured on the 34-strategy catalog at 5400 bars:

| band half-life | 1 | 2 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| headline net capture | 32% | 29% | 31% | 45% | 56% | 58% |
| **Mean Reversion (the matched row)** | **22%** | 26% | 29% | 44% | 56% | 58% |
| Trend | 31% | 25% | 21% | 20% | 26% | 35% |

At half-life 1 the headline is carried by Trend — strategies fitting the random-walk level, 83% of
return variance there — while everything aimed at the planted reversion keeps 22%. **Quote 22%, not
32%, for what the catalog's reverting strategies keep of a fast planted reversion.** The AR(1) sweep
self-checks the taxonomy: Mean Reversion is the maximum row at φ = −0.3/−0.2 (114%/126%) and Trend
or Breakout at φ = +0.2/+0.3 (116%/103%, Mean Reversion 14%/5%).

**These sweeps are deterministic** — fixed seeds, no RNG in the search — so two runs of the same
catalog agree to the symbol, and a difference between two catalogs is a real effect on that sample
rather than sampling noise. Generalizing its MAGNITUDE to the population still carries ±6.6pp at
n = 50.

**Consequences for anyone tempted to close the gap with a new strategy.** ADR-056 added exactly the
strategy the old reading called for — one that estimates a slow level and a fast deviation on
independent timescales — and net capture moved ≤ +0.7pp in every cell while the new strategy won
1–5 of 50 searches. ADR-058 removed it. **At half-lives 1–3 no reverting strategy wins the in-sample
comparison, so the selection step never gets as far as asking which reverting strategy is best.**
Judge the next attempt against the finalist CATEGORY MIX at half-lives 1–3, not against capture
alone; and use `compare_power_sweeps(before, after)`, which refuses to call a capture delta
attributable unless the finalist mix moved with it (a larger grid raises an in-sample maximum on its
own).

### 7.6 Historical latent and filtered band references (ADR-061)

**Current qualification — FINDING-159 (Open):** the latent and observable
band references use conditional log-mean signs to score simple returns.
Their historical scores are reference-strategy measurements. The Gaussian
simple-return mean requires `expm1(log_mean + predictive_log_variance / 2)`;
the filtered case also needs posterior state uncertainty. The optimality,
upper-bound and no-recoverable-edge claims below are historical interpretations,
not certified conclusions. Detection counts remain unchanged; the finding
does not correct the reference or certify filter initialization.

`mean_reverting_edge` plants `log price = random-walk level + AR(1) deviation`;
only their sum is observed. The latent sign reference uses the hidden deviation.
`filtered_deviation` applies the specified two-state Kalman recursion using known
source parameters and its historical initialization. Its filtered sign reference
is scored net of the stated costs; `achievable_capture_ratio` divides the selected
in-sample finalist score by that reference under ADR-055's denominator refusals.
These measurements do not certify filter initialization or a bound on causal
strategy performance. The following historical table retains its original labels
and values: 50 symbols per cell at 5400 bars.

| band half-life | 1 | 2 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| latent-state oracle, net | +1.70 | +1.93 | +2.13 | +2.21 | +1.71 | +1.24 |
| **achievable (Kalman) oracle, net** | **−0.08** | **+0.22** | **+0.51** | **+0.95** | **+0.93** | **+0.70** |
| capture vs latent (the headline) | 32% | 29% | 31% | 45% | 56% | 58% |
| **capture vs achievable** | *refused* | 261% | 130% | 105% | 103% | 104% |

**What these band controls establish.** The recorded net filtered reference is
−0.08 at half-life 1, and the selected in-sample capture ratios from half-life 3
are near or above 100% against that specified denominator. These observations do
not establish that all recoverable edge was captured or that no other causal,
cost-aware strategy could trade shorter half-lives. Each cell's 0/50 detection
count remains a result of the executed pipeline. Comparing the largest recorded
filtered net reference, about 0.95, with the historical ADR-043 approximately 2.1
frontier can
contextualize that reference; it does not prove that a graduation would be wrong.

Two historical diagnostic comparisons remain useful within their measured scope:

- **Estimator comparison.** At the measured deviation shares and half-life 1,
  the recorded Kalman and naive EWM residual correlations with the hidden
  deviation were 0.270 and 0.271. Similar correlations for those two estimators
  do not certify the historical filter or rule out a better estimator, position
  rule or treatment of costs. ADR-056's naive estimator and proposed Kalman
  follow-up remain attributable to their executed methods.
- **Selection comparison.** The measured half-life-1 matched-family pick rates
  were 0% under max DSR, 0% under max in-sample Sharpe, 10% under max walk-forward
  OOS and 0% under max purged-CV OOS. These fixed-cohort observations do not prove
  that another selection rule cannot help. Production selection decisions and
  their separate criteria remain governed by ADR-069/070/071.

The AR(1) sweep historically records no separate achievable reference because its state is the
observed return. Capture above 100% follows from an in-sample selected numerator divided by a
fixed cost-paying reference, not from state observability. FINDING-155 also qualifies the historical
AR(1) reference's omitted conditional drift; observable state does not make that sign rule optimal.

**ADR-069/070/071: selection-rule sweeps must preserve the selected finalist.** ADR-069 measured
`observed` against `walk_forward` cross-family selection; the non-default arm failed its pre-stated
power criterion, so ADR-070 keeps `observed` as production default. FINDING-010 then found that
calibration extracted diagnostics and attribution from max DSR even when `run_search` sent the
walk-forward winner to the holdout and gate. ADR-071 makes every finalist-level artifact field use
the requested selection rule. ADR-070's detection/Type-I counts remain valid because they came from
the correctly selected gate result; its observation about the non-default null diagnostic is not
reusable without a corrected rerun. Non-default artifacts were never committed.

**ADR-079: persist the real finalist, too.** FINDING-015 found that pool reporting still rebuilt
every real finalist as max DSR. `best_strategy_name` cannot identify a trial after refinement adds
a second trial from the same family. New experiments therefore persist `selected_trial_index`, and
all finalist-level pool statistics resolve it through one checked helper. Legacy rows retain the
historical max-DSR reading; no old non-default identity is invented.

### 7.5 The real universe against the null (ADR-051) — `scripts/pool_report.py`
ADR-038/039 recorded a walk-forward and a purged-CV OOS Sharpe on longitudinal trials with a stated revisit
trigger: read them against `data/null_calibration/*.json`. Two things had to be repaired before that
was possible, and both are the general lesson.

- **Compare the same statistic on both sides.** The pool's summary read gate passers; the null
  artifacts record the max-DSR finalist of every SEARCHED symbol. `PoolReport` now carries
  `walk_forward_finalists` / `purged_cv_finalists` alongside the gate-passer fields, and the report
  distinguishes *no experiment carries it*, *no experiment passed the gate*, and a measured median.
  This matters permanently, not once: under ADR-046's repaired denominator the 2026-08-20 discovery
  run produced **0 graduates from 603 experiments**, so the gate-passer window is empty and only
  the finalist window is readable.
- **Match the identity before quoting a difference.** Compare `search_config_version` and
  `gate_config_version` on both sides and check the bar counts. `Experiment` now records the former
  (ADR-052) precisely because establishing it once required diffing commit timestamps against
  workflow start times.

**Measured (2026-08-20, matched at fingerprint `3f36fda2…` and 5400 bars).** Real: 603 finalists.
Null: 200 per mode.

| statistic | real median | bootstrap null | iid-normal null |
|---|---|---|---|
| walk-forward OOS Sharpe | **+0.561** | +0.652 | +0.414 |
| purged-CV OOS Sharpe | **+0.597** | +0.661 | +0.475 |

Mann-Whitney one-sided for real > null: **p = 1.0000 vs bootstrap** on both statistics, **p < 0.0001
vs iid-normal** on both. Every catalog strategy trades serial structure; the bootstrap null has none
and preserves SPY's return shape exactly. So the advantage over iid-normal is **distributional, not
predictive**. Read it as a joint statement about this universe and this catalog — not as a threshold
argument (charter §4), and not as "the catalog cannot capture serial structure", which ADR-042
measured to be false at 42% detection on a planted half-life-5 reversion. Limitations are in
ADR-051 §Measured; the sharpest is that the bootstrap resamples SPY rather than each symbol.

**ADR-064 made the report state that verdict instead of refusing it.** The identity check above was
implemented as exact equality between the pool's *median* `n_bars` and the null artifact's, and a
median that grows by a bar per trading day can essentially never equal a fixed integer — so from the
moment the pool grew past 5,400 the report printed `NOT COMPARABLE -- history 5444 bars vs 5400` on
all four rows. `compare_with_null(report, calibrations, experiments)` now selects the experiments
whose `n_bars` is within `HISTORY_TOLERANCE` (10%) of THAT artifact's, summarizes the real side over
exactly those, reports `matched_n` / `matched_n_bars` on every row, and refuses below `MIN_MATCHED`
(30). The search-family test reads the same subset — refusing a comparison because of rows outside
it describes a comparison nobody made. Rows with no `n_bars` are excluded, never assumed to match.

**Measured (2026-08-29): 2,427 matched experiments at a median 5,445 bars, 100% fingerprint
`3f36fda2…`, against nulls at 5,400.**

| statistic | matched real median | bootstrap null (median / p95) | iid-normal null (median / p95) |
|---|---|---|---|
| walk-forward OOS Sharpe | **+0.542** | +0.652 / +0.983 | +0.414 / +0.796 |
| purged-CV OOS Sharpe | **+0.584** | +0.661 / +1.003 | +0.475 / +0.803 |

**Does not separate on any of the four**, and against the bootstrap the real median sits *below* the
null's. The pool-wide medians are +0.567 / +0.598 — quoting those against a 5,400-bar null is the
error this repairs, so quote the matched numbers. After ADR-063 the pool goes bimodal (5,448 legacy /
7,400+ re-searched) and the two cohorts must be read against their own nulls; `matched_n` on each row
is what tells you which cohort you are looking at.

**Provenance, and why the tree can answer again (ADR-065).** Those matched numbers were measured
against the **5,400-bar** null artifacts, which ADR-063's re-dispatch overwrote in place with the
7,400-bar run (`6efcb7e`) the same day — leaving a published measurement reproducible only from
commit `dbba1ed`. The cause was the filename: one path per null mode. Artifacts are now named for
the history they measured (`bootstrap_spy_5400.json`, `bootstrap_spy_7400.json`); the superseded
5,400-bar pair was restored from `dbba1ed` under its own name and **the table above reproduces from
the working tree**. A re-run at the same length still overwrites — that is a re-measurement of the
same pair — so the directory grows once per genuine change of history length, not once per run.

## §7.6 Excess over buy-and-hold — what the OOS statistic is actually denominated in (ADR-068)

The walk-forward OOS Sharpe carries the **drift of the series it was computed on**. Measured
2026-08-30, where "underlying" is `mean/std × √252` of the daily returns the finalist was searched
over — buy-and-hold, computed exactly as `walk_forward._sharpe` computes a strategy's:

| side | underlying | finalist walk-forward OOS median | excess |
|---|---|---|---|
| `iid_normal` null (drift 0.0003 / vol 0.012) | 0.397 | +0.414 (5,400) / +0.416 (7,400) | +0.017 / +0.019 |
| `bootstrap:SPY` null (SPY 1993-01-29→2026-08-28) | 0.650 | +0.652 (5,400) / +0.622 (7,400) | +0.002 / −0.028 |
| real matched cohort (5,445 bars) | 0.546 (39-symbol sample) | +0.542 | −0.004 |

**Then measured pairwise, per symbol** (run 33287465013 → `a61beb0`, 200 nulls per mode at 7,400
bars, 0 false graduates, 16/16 shards green). The excess here is the median of the per-symbol
DIFFERENCES, which is the statistic `compare_with_null` reports — not the difference of medians:

| null (7,400 bars) | OOS median | its own hold median | paired excess (median / mean) | excess p95 | corr(OOS, hold) | beats holding |
|---|---|---|---|---|---|---|
| `bootstrap:SPY` | +0.622 | +0.652 | **−0.006** / −0.028 | +0.096 | **0.884** | 18.5% |
| `iid_normal` | +0.416 | +0.394 | **+0.000** / +0.012 | +0.325 | 0.652 | 36.0% |

Three consequences worth carrying forward:
1. **The paired excess is zero on a null**, not merely small — so the level of the raw statistic is
   the generated series' drift and nothing else.
2. **The searched finalist usually loses to holding** on structure-free data (beats it 18.5% /
   36.0% of the time): it pays turnover for a signal that is not there, as it should.
3. **The excess band is ~10× tighter** (bootstrap p95 +0.968 raw → +0.096 excess). Under §7.5's
   verdict rule that makes the drift-controlled comparison far more sensitive — a real edge no
   longer has to out-run the spread of market drift to show up.

**Every row lands on its own underlying's buy-and-hold Sharpe to within ±0.03.** Two of them are
nulls with no exploitable structure by construction, so the level is not evidence of anything — and
§7.5's −0.11 "gap" between the pool and the bootstrap null is the gap between SPY's 33-year drift
and the median pool symbol's. Read the other way it is the cleanest statement of gate honesty here:
**what the search adds out-of-sample over holding the same series across the same windows is +0.002
to +0.019 on data with no edge, and −0.004 on real symbols.**

`walk_forward_evaluate(performance, splits, benchmark=)` scores the benchmark on the SAME test
indices with the same annualization and mean-over-splits, reporting `mean_oos_hold_sharpe`;
`ValidationEngine` passes the frame's close-to-close returns; `Experiment.walk_forward_hold_sharpe`
and `NullCalibration.walk_forward_hold_sharpes` persist it; `compare_with_null` emits a
`walk-forward excess` row per null mode beside the raw row, with §7.5's verdict rule applied to it.
Rules that hold here:
- **The raw row stays.** A published verdict is not restated on a new statistic in place.
- **Absent is not zero** (ADR-067). Every artifact written before ADR-068 carries neither side of
  the difference, so the row prints `NOT MEASURED` until the pool is re-searched and the null
  re-dispatched. An excess of zero is a measurement nobody made.
- **The two null lists are paired per searched symbol.** ADR-080 makes that identity structural:
  new calibrations store one `NullSymbolDiagnostics` record per symbol and excess is derived from
  fields on that record. Equal-length partial legacy arrays are refused; positional legacy pairing
  is allowed only when both sides contain exactly `n_symbols` entries. The original arrays remain
  raw-distribution/API projections, not pairing identity.
- **Purged-CV is a separate measurement, not a reused walk-forward control.** ADR-078 later added
  its own whole-window buy-and-hold benchmark because purged folds partition the searched window;
  neither control may stand in for the other.


## §7.7 The real side of the excess row, and the two-sided band (ADR-072)

Measured 2026-08-31, the first time both sides of the difference existed. 77 experiments over 66
symbols at 7,345 bars carry `walk_forward_hold_sharpe` and match the 7,400-bar nulls under §7.5's
±10% tolerance; both sides carry fingerprint `3f36fda2…`.

| side | n | median | mean | p5 | p25 | p75 | p95 | share < 0 |
|---|---|---|---|---|---|---|---|---|
| **real, matched cohort** | 77 | **−0.125** | −0.186 | −0.549 | −0.308 | −0.018 | +0.021 | **75.3%** |
| `bootstrap:SPY` null, 7,400 | 200 | −0.006 | −0.028 | −0.233 | −0.037 | +0.000 | +0.096 | 55.5% |
| `iid_normal` null, 7,400 | 200 | +0.000 | +0.012 | −0.251 | −0.035 | +0.057 | +0.325 | 49.5% |

**What the search adds out-of-sample, with drift removed from both sides, is −0.125 on real symbols
and ≈0 on data with no edge by construction.** The real median sits at the bootstrap null's 11.5th
percentile and the iid null's 14.0th. Quote it as a statement about the search — the in-sample
argmax fits structure that does not persist — not about the market.

`NullComparison` carries `null_p5` on every row and `real_below_null_p5` on the centered one only.
The raw rows stay one-sided on purpose: §7.6 measured that their level IS each side's own drift, so
a real median under a null says the median pool symbol drifted less than SPY. **The verdict does not
flip on today's numbers** — −0.125 is inside both nulls' p5 — and that is reported rather than
worked around.

**The open question ADR-072 recorded, and how ADR-075 closed it.** The row compares a median of 77
against a band over individual null draws — the right yardstick for "could ONE SYMBOL look like
this" (one easily could), the wrong one for "is the pool's CENTRE different from the null's", which
is what the row is asked. The naive rescaling (SE of a median of 77 ≈ 0.016 → about 7 SE) assumes 77
independent draws, and they are 66 symbols over one calendar window with `fifty_two_week_high`
winning 30 of 77.

**ADR-075: `_clustered_difference_ci` reports a 95% interval for `median(real) − median(null)`,
resampling the real side BY SYMBOL** (all of a symbol's experiments enter together) and the null
side by draw (each null symbol is an independently generated series), B = 20,000, seed 7 — the same
constants §7.8's bootstrap uses.

**FINDING-011:** ADR-064/067's `comparable` guard applies before this interval is exposed. A row
refused for search-family identity, matched history, or fewer than 30 measured diagnostics retains
its medians and mismatch as context but carries no difference interval and cannot say `EXCLUDES
ZERO`. The same 30-observation floor applies to the interval's effective symbol-cluster units, not
only to experiment rows. The dashboard repeats both guards so a stale payload cannot turn a refusal
or one-cluster resample into a finding.

| null (7,400 bars) | difference | 95% CI, symbol-clustered (66 clusters) |
|---|---|---|
| `bootstrap:SPY` | **−0.119** | **[−0.215, −0.061]** — excludes zero |
| `iid_normal` | **−0.125** | **[−0.218, −0.063]** — excludes zero |

**The project's central claim becomes: the search's drift-controlled contribution on real symbols is
distinguishable from what the same search contributes on data with no edge by construction, and it
is distinguishable in the NEGATIVE direction.** Three qualifications are part of the sentence:
- **The interval is a LOWER BOUND on its own width.** Symbol clustering removes within-symbol
  repeats and symbol-level heterogeneity, not the cross-sectional correlation of one shared calendar
  window. **FINDING-012:** one correlated 200-symbol null panel is not enough—it gives one draw of
  the panel median, and feeding its symbols to the existing elementwise bootstrap erases their
  dependence again. **ADR-081 accepts the unspent design:** equal-symbol real medians, joint iid
  resampling of complete calendar vectors, 400 independent whole-panel replicates, and a separate
  manual workflow sharded only by complete panel index. The existing result remains qualified until
  that instrument is implemented, authorized, measured, and interpreted in a later ADR. The first
  non-measuring slice is in `app/research/lab/panel_null.py`: frozen cohort/replicate identity,
  batching-invariant global-index seeds, fail-closed whole-panel consolidation and equally strict
  direct final-artifact validation. Every persisted real/panel statistic must be finite. The first
  generator primitive validates an already aligned complete OHLCV panel, draws one seeded iid
  sequence of whole calendar rows, applies it across every symbol, and reconstructs each path from
  selected close returns and same-row geometry. `infer_panel_null` now applies the frozen
  equal-symbol statistic, inclusive lower/upper tail counts, plus-one two-sided Monte Carlo p-value,
  and ADR-082's two 97.5% Clopper-Pearson intervals (at least 95% simultaneous coverage). A 3/400
  tail resolves below 0.025; 4/400 remains unresolved. Purged-CV is emitted only when every real and
  null panel value exists. `prepare_panel_null_source` freezes the caller's explicit ordered symbol
  cohort, intersects complete timestamps across every frame, retains exactly the newest requested
  history, records its UTC date range, and hashes canonical ordered timestamps and OHLCV values;
  missing/unexpected symbols or insufficient common history fail closed. Real cohort selection now
  matches exact search/gate/history identity, resolves ADR-079's persisted finalist, rejects
  duplicate experiment IDs, and median-collapses repeats to one value per canonically ordered
  symbol for eligibility. **ADR-085 then remeasures the observed statistic on the frozen source:**
  one checked production search per exact common 7,400-row symbol column, matching the function
  applied to each null panel. The pool-derived repeat medians no longer enter inference. ADR-084
  applies a one-sided source-history floor before aggregation: an experiment must
  state at least the exact target bars while remaining inside the existing upper tolerance. This
  prevents a below-target symbol from entering a frozen panel it cannot physically supply; the
  fetched complete-case calendar remains the final authority. The injected fetch boundary calls
  the provider once per frozen symbol in canonical order
  and reports every provider failure before preparation; network adapter/end-date wiring remains
  pending. `bind_panel_null_cohort` refuses ordered-symbol or target-history drift between that
  selection and the prepared source, then freezes their exact values, source identity, versions,
  base seed, 400 replicates, and effective-symbol floor. One local replicate runner now revalidates
  that source/cohort identity, jointly generates the panel, calls an injected search once per
  symbol, rejects returned symbol/history/search/gate drift, and preserves symbol-attributed errors
  plus equal-symbol panel statistics. The production adapter checks the exact search/gate
  fingerprint before expensive execution and wraps unmodified `run_search`; only tests may inject
  a stand-in. Frozen source transport uses an exclusive-create, pickle-free compressed archive with
  ordered symbols, UTC nanoseconds, dense float64 OHLCV, and the canonical digest; loading requires
  the exact schema and recomputes the digest from reconstructed frames before generation. The local
  batch boundary accepts only an explicit non-empty set of unique in-range global panel indices,
  loads that exact archive, executes whole panels in canonical order, and exclusively writes a
  validated scratch shard. Direct construction and load both recheck seed/index/panel identity,
  symbol error accounting, and the effective-symbol floor. A separate immutable JSON manifest
  carries the complete cohort identity across preparation and batch jobs; it is exclusively created
  after validation and fully revalidated when loaded. ADR-083 adds the exact 40-character
  workflow-dispatch git revision to that identity; preparation records it and every batch rejects
  revision drift before constructing a production search. The local production-batch driver loads that
  manifest with the prepared-source archive, verifies the pair before constructing the checked
  production search, and executes only explicit whole-panel indices. The consolidation CLI
  revalidates every scratch shard, requires the full frozen index set, prints the fixed inference,
  and is the sole writer of an optional final artifact. The preparation CLI pins one explicit UTC
  cutoff across every yfinance request, uses the shared `CLOUD` retry policy, removes the cutoff
  day's still-forming bar, binds the current production search/gate identity, and exclusively
  writes only the source archive and cohort manifest to non-`data/` scratch paths. The production
  batch CLI resolves exactly one explicit unique index set or half-open global-index range, rejects
  existing and repository-`data/` outputs before expensive execution, and delegates the immutable
  input pair plus current production policy to the whole-panel driver. The manual-only workflow
  transports one prepared input artifact through 100 disjoint four-panel batches covering the
  exact 400-index set, then permits only full validated consolidation to write and commit the
  generated result. ADR-086 bounds each batch at 156 serial symbol searches and gives preparation
  120 minutes for ADR-085's observed-panel searches without changing seeds or inference. It has not
  been dispatched, so the measurement remains pending. ADR-087 makes recovery stage-aware: a
  pre-consolidation failure requires a full-job rerun, never a partial artifact merge; after the
  final artifact has been uploaded, publish-only recovery downloads and validates those exact bytes
  by source run ID and commits them without recomputing the fixed look. ADR-088 makes that run ID a
  provenance boundary rather than an artifact naming convention: recovery checks GitHub's
  authoritative repository, run ID, workflow path, manual event, completed state, and head SHA,
  requiring the executed SHA to equal the artifact cohort's recorded code revision before any
  generated destination mutation. ADR-089 adds the missing rerun-attempt dimension: final artifact
  names and recovery inputs contain the exact attempt, metadata comes from the attempt-addressed
  API endpoint, and a partial or mismatched run/attempt identity fails before publication.
  ADR-090 extends that attempt identity to the frozen-input pair and every complete-panel scratch
  shard, preventing a full rerun from selecting or wildcard-merging prior-attempt intermediates.
  ADR-091 persists the same positive run ID and attempt in the frozen cohort and final calibration,
  so the committed one-look record remains attributable after artifact retention expires and
  recovery must match payload, request, and authoritative metadata.
  ADR-092 requires every null replicate to search the complete frozen symbol cohort successfully,
  matching the observed arm. The eligibility floor cannot silently redefine a generated panel as a
  median over a data-dependent subset.
  ADR-097 re-derives every persisted panel ID from the complete cohort and global panel index at
  shard and final-artifact validation, matching the identity emitted by execution.
  ADR-098 reconstructs and revalidates the complete final calibration before inference, so a
  partial or identity-drifted Pydantic model copy cannot bypass the artifact invariants.
  ADR-099 checks current master before normal-mode preparation and refuses to rerun after the fixed
  generated measurement is published; post-publication operation is exact-byte recovery only.
  ADR-100 makes that recovery publication-idempotent: the recovery job checks out current master,
  identical bytes return without rewrite or commit, and a different durable measurement fails
  before destination mutation.
  ADR-101 closes the power-side capture gap left by ADR-096: every planted-edge power result now
  preserves the exact selected finalist's nullable probability-form DSR, index-aligned with its
  existing finalist fields. Future ordinary null and power runs can support matched Type-I/power
  curves for the candidate statistic; no gate or threshold changes, and legacy artifacts remain
  explicitly unmeasured through the empty-list default.
  ADR-102 prevents those marginal probabilities from being mistaken for whole-gate evidence. Every
  future null and power symbol now pairs its probability with the complete incumbent gate verdict
  and structured locked-holdout Sharpe/length, which is the minimum record that can replace only
  DSR and re-judge the unchanged conjunction plus ADR-018 survival. The only candidate rule is
  strictly `P > 0.95`; the pre-registered decision requires zero composite false graduates in both
  null modes, no loss in either `phi=+/-0.30` cell, and an exact one-sided paired McNemar improvement
  across those strong-edge cells. `compare_probability_dsr_gate` is the pure executable boundary:
  it rejects wrong modes, identity/history drift, incomplete legacy records, undersized samples,
  and missing strong-edge cells. ADR-103 extends that refusal through every nested power cell and
  embedded gate verdict and rejects duplicate strong-edge cells, so a wrapper cannot mislabel the
  records actually counted. No qualifying artifact has been read or dispatched yet.
  ADR-158 makes those complete null/power claims defensive after validation: all nested arrays,
  maps, diagnostics, verdicts, and sweep cells are immutable without changing their JSON shapes,
  and consolidation plus probability-DSR inference reconstruct inputs before use. An unchecked
  in-process model copy can no longer change the evidence that is published or interpreted.
- **The single-draw verdict is unchanged and reported beside it**, per ADR-068's rule that a
  published verdict is not restated on a new statistic in place. They size different questions.
- **It was not a blind test.** ADR-075 §"Full disclosure": the point estimate was known before the
  scheme was fixed, so the pre-registration covers the procedure, not the answer.

## §7.8 Reading a change in the SEARCH WINDOW (ADR-074)

ADR-063's second clause ("the pool's median holdout Sharpe must not fall") is **unanswerable as
phrased**: a holdout Sharpe exists only on a `Graduate`, 220 of the pool's 221 graduates are
`legacy-unspecified`, and the live family has produced exactly one in 3,029 experiments. It is the
third criterion in this project stated over a quantity nobody sized first — check the sample size
of the statistic BEFORE writing the threshold.

`compare_search_windows(experiments)` reads it on the finalist instead, and the pairing rules are
the load-bearing part:
- **Within symbol.** The cross-symbol form was measured and rejected: under one family `n_bars`
  varies mostly with listing age, and the <6,000 / ≥6,000-bar cohorts share **zero symbols**.
- **Within search family**, per §7.5's identity rule.
- **Repeat runs at one window collapse to that symbol's median**, so a name the discovery happened
  to re-search five times does not outweigh one it searched once.
- **Every delta carries a bootstrap 95% interval** (20k draws, seed 7). ADR-070: a point estimate
  with no interval is what made two pre-stated criteria unreadable.

| paired delta (long − short) | n | median | 95% CI |
|---|---|---|---|
| finalist walk-forward OOS — **surrogate**, each side carries its own window's drift | 368 symbols | −0.038 | [−0.060, −0.009] |
| finalist in-sample observed | 368 symbols | +0.012 | [−0.005, +0.034] |
| **drift-controlled excess — look 1 (ADR-074), UNDERPOWERED BY CHOICE** | 45 symbols | −0.074 | [−0.157, +0.030] |

The longer window changes which strategy the search picks on **257 of 368** symbols (later refreshed
to 296 of 422 as the pool grew — see ARCHITECTURE.md's live `/api/v1/window-comparison` row, a
descriptive report line, not a re-spend of this closed test sequence).
`scripts/window_experiment.py N` supplies the criterion's short side by re-searching a deterministic
sample at `PRE_ADR063_SEARCH_START` (pinned in `history.py`, never a literal in a driver) and
writing to its own file — the pool is read as the ADR-062 prior only. Look 1's interval includes
zero, so ADR-074's pre-stated criterion did not fire on its own — but two things it did settle:
removing the drift confound made the effect *larger* (−0.074 vs −0.038), so the confound is not
what produced the surrogate; and the same 45 deltas gave a **mean** of −0.086 against SE 0.032,
which would have fired a criterion stated on the mean. **Pre-state the ESTIMATOR, not only the
threshold** — a bootstrap median is robust but costs ≈1.6× the sample of a mean.

**ADR-076 spent the second, pre-stated look and closed the sequence.** n=45 was underpowered *by
choice*, not necessity — the candidate set held 368 symbols all along and 45 was a command-line
argument (FINDING-013). ADR-076 froze an independent 200-symbol sample
(`data/window_experiment/adr076_sample.json`, committed before any of it was searched), sized n from
look 1's own dispersion (≈87% power), and pre-registered a **Pocock two-look boundary, nominal
two-sided α = 0.0294**, so the two looks together still spend the standard 0.05. All 200 were
searched 2026-08-31:

| paired delta (long − short), n=200 | median | 95% CI | reads as |
|---|---|---|---|
| finalist walk-forward OOS — raw, drift-confounded | −0.037 | [−0.061, −0.008] | excludes zero |
| **drift-controlled excess — the criterion** | **−0.008** | **[−0.055, +0.022]** | **covers zero — criterion does not fire** |

**|δ|/SE ≈ 0.45 against the Pocock boundary of 2.178 — a measured null, not a failure to resolve.**
Look 1's n=45 point estimate (−0.074) collapsed toward zero at n=200, the opposite of what an effect
that merely needed more power would do; that contrast is itself evidence the true drift-controlled
effect is near zero, not merely undetected. **ADR-063's window stays and the two-look sequence is
now closed** — do not re-derive a third drift-controlled number from the grown pool (ADR-077's
separate `/api/v1/window-comparison` endpoint exists precisely so a descriptive report line never
gets mistaken for a third spend of this test).

## Null-calibration leaf validity (ADR-213)

NullGraduate and NullSymbolDiagnostics validate original finite real nonboolean
score evidence, positive integral history, and positive finite holdout years.
Present probability DSR is bounded to [0, 1] on the original real value before
float conversion; absent diagnostics/verdicts remain explicitly unmeasured.
Nested reconstruction and merge inherit these leaf contracts. Valid signed and
zero scores, numeric scalar types, formulas, identities and thresholds remain.
This does not establish top-level/legacy-array coherence or overflow-free
subtraction of finite diagnostics (FINDING-158).

ADR-214 / FINDING-160 closes the null paired-difference boundary separately:
`paired_excess` rejects nonfinite subtraction results in both symbol-paired
and complete legacy-array paths. Valid signed/zero differences and unmeasured
pairs retain their meanings. This does not certify other report arithmetic,
percentile operations or root scalar coherence; no threshold/identity changes.

ADR-215 / FINDING-161 separately validates null-root original count/score types,
finiteness and intrinsic bounds. Survivors <= graduates <= searched, graduate
count matches its list, and the false-graduation rate equals the exact count
ratio. Legacy optional arrays, nullable maxima and finite signed scores persist.
Root maximum/formula recomputation, legacy diagnostic-array validity and other
arithmetic remain separate; no threshold or methodology identity changes.

ADR-216 / FINDING-165 separately guards each present null-array element before
coercion: finite real nonboolean scores, positive integral nonboolean bars and
positive finite years. Empty/partial legacy arrays keep existing raw/unmeasured
and excess-pairing semantics; canonical projections and merge inherit guards.
This does not establish new array lengths, power-array contracts or overflow-free
percentiles. No threshold, formula, identity or generated-data changes.

## Historical v10 fixed AR power (FINDING-162)

The frozen 7,400-bar, 200-symbol arms at phi −0.3/+0.3 completed without
errors: 130/200 and 163/200 graduates, all surviving ADR-018's 1.3432393 bar.
Negative-arm rejections are stability; positive-arm DSR/stability failure sets
are disjoint. Shared innovations require separate n200 denominators and marginal
uncertainty, without independent pooled inference. Historical reference scores
retain FINDING-155's qualification. Executed `8e372d50`, search `969dd54d`, gate `25085698`;
this strong stationary synthetic evidence does not certify market/weak-edge
power or authorize threshold changes. See the report for full hashes/audits.

## Historical v10 fixed heavy-tail null stress (FINDING-163)

Student-t df5 simple returns at drift 0.0003 and vol 0.012 completed all 200
7,400-bar sources with no errors/graduates/ADR-018 survivors; components
DSR 0, PBO 180, stability 50, MinTRL 28, holdout 134, beat-hold 29. The conditional
one-sided 95% zero-event upper bound is 1.4867%, not a zero-error guarantee.
Sources match the interrupted frozen plan; no redraw/drop or pooled denominator.
Finite fourth/infinite eighth moments limit kurtosis-precision assumptions.
Executed `8e372d50`, search `969dd54d`, gate `25085698`; no market/bootstrap certification
or threshold change. Trial-wide maximum DSR remains a production summary.

## Finite calibration summary arithmetic (ADR-217)

The shared null/power median and linear-p95 helper validates finite original
score inputs and preserves every finite native summary. Nonfinite native
median/p95 arithmetic recovers with exact rational endpoint interpolation
at the unchanged binary virtual index. Empty arrays remain unmeasured; invalid
sources raise without filtering. This is summary arithmetic, not a power-array
construction contract or universal finite-native precision guarantee. Search,
gate, reference strategies, thresholds and fingerprints remain unchanged (F166).

## Power root evidence validity (ADR-218)

PowerCalibration requires original positive integral searched counts, nonnegative
integral detected/survivor counts, finite real rate in [0,1], and a finite
nonnegative bar. Counts satisfy survivors <= detected <= searched and rate equals
detected/searched exactly. Sweep reconstruction inherits these guards. Optional
legacy arrays and reference/process evidence are unchanged; array lengths,
component relationships and bar recomputation remain separate (F167). No search,
gate, threshold, fingerprint or generated record changes.

## Power array evidence validity (ADR-219)

Present gross/net/achievable reference, finalist and per-category scores validate
as original finite real nonboolean elements. Bars are positive nonboolean
integers; years finite and strictly positive. Nullable finalist probabilities
retain None and otherwise require original [0,1] bounds before float rounding.
Existing empty/partial array and capture refusal semantics remain; sweep
reconstruction inherits the guards. No new lengths, process/reference rules,
component relationships, thresholds or fingerprints (F169).

### Joint original scalar evidence (ADR-220)

Canonical CalibrationSymbolVerdict probability, locked-holdout score and bar
count use the established before-coercion contracts. Probability remains nullable
and original real nonboolean [0,1]; scores finite real nonboolean and history
positive nonboolean integer. Exact incumbent holdout projections, strict >0.95
and legacy absence remain unchanged. FINDING-170's coercion/range bypass is a
synthetic evidence-boundary defect, not an observed corrupt artifact or candidate
comparison result. No GateResult scalar policy or root/component reconciliation
is added, and no threshold, fingerprint, source or generated data changes.

### Power component-count bounds (ADR-221)

Each present gate_pass_counts value is an original nonboolean nonnegative
integer no larger than n_symbols, ADR-049's successful-search denominator.
FINDING-171's coerced/impossible attribution is refused before freezing or sweep
reconstruction. Empty/partial legacy mappings and existing key semantics remain;
no missing count is inferred. Composite/joint reconciliation is a separate
contract. No gate component, threshold, fingerprint, source or data change.

### Modern power joint-count agreement (ADR-222)

Complete symbol_verdicts binds n_detected to incumbent passage, survivors to
strict ADR-018 comparison at each passed record's own holdout history, and each
present known component count to its joint sum. FINDING-172's contradictory
headline/attribution is refused on reconstruction. None candidate probabilities
retain measured incumbent evidence; absent legacy joint records, partial maps
and unknown keys remain supported. No median-bar substitution, key/completeness
policy, null-side reconciliation, threshold, fingerprint or source change.

### Completed frozen AR grid (FINDING-168)

The fixed v10 phi -0.2/-0.1/+0.1/+0.2 arms each completed 200/200 with no errors,
source-identical replay loaded `29b70228`, independent 800-source/1600-reference
and full joint/count/schema audits. Detection/survival counts respectively:
117/53, 0/0, 0/0, 73/51. Marginal two-sided CP95 zero/200 upper is 1.827534%;
this differs from the separate one-sided t5 bound. The four arms share new seeds;
prior strong +/-0.3 used a different family, so no independent pooling or wholly
paired six-point inference. Historical reference scores omit drift intercept
(F155); net reference near zero does not certify absence of tradeable edge.
Stationary controls do not bound market power or authorize threshold changes;
ADR-102 still lacks matched bootstrap:SPY. See F168 for exact counts, intervals,
procedure, source/result hashes and complete operational-replay attribution.


### Explicit-drift AR sign reference (ADR-223)

ar1_conditional_mean_sign_sharpe requires known source-law phi and drift, adds
that drift intercept to lagged observed simple returns, keeps the first unavailable
lag flat, and uses the established generic gross/net scoring conventions. Original
law/cost parameters and derived predictions must be finite. No drift fitting,
extra lag, default scorer/measure_power change, artifact relabeling, threshold or
fingerprint change. F155 stays Open for explicit production method/drift
attribution; this sign reference does not certify cost-aware or sample-Sharpe
optimality or absence of tradeable edge.


### Frozen conditional-drift reference audit (FINDING-173)

The preplanned source-only comparison on exactly F168's 800 frozen laws matched
all original source hashes and 1,600 historical reference scores, then independently
verified the new gross/net scores. Per-cell median paired net Sharpe shifts at
phi -0.2/-0.1/+0.1/+0.2 are +.047443/+.107290/+.065364/+.020281, descriptive only.
No searches, gate judgments, new observations, fitting, pooling or optimality
claim. F155 production attribution remains Open; historical default meanings
and F168 detection/survival measurements remain unchanged. F173 records the
counts, separate per-rule medians, paired deltas, source law and audit hashes.


### Modern null graduate/joint agreement (ADR-224)

When all canonical null diagnostics carry joints, n_graduates equals incumbent
passage, graduate symbols are exactly that passing set, and each graduate's
locked-holdout score/history equals its verdict. n_clear_deflation_bar counts
strict ADR-018 survival at each joint passer's own history and enclosing N.
F174's synthetic contradictory Type-I claims fail on construction/unchecked merge.
Graduate ordering, absent legacy joints and nullable candidate probabilities
remain; trial-wide maximum margins and selected-finalist graduate margins are
not inferred or conflated. No threshold, fingerprint, producer or source change.


### Canonical null diagnostic holdout history (ADR-225)

A NullSymbolDiagnostics with present calibration_verdict requires holdout_years
exactly equal to that verdict's holdout_n_bars / 252. F175's contradictory finite
history attribution fails at the leaf and through root/merge reconstruction.
Absent legacy joints and nullable probabilities remain valid. Total n_bars is
not equated with holdout bars; no split fraction, root-summary, power-array or
embedded-gate-version policy is added. Source, producer, estimator, threshold,
fingerprint and generated records remain unchanged.

### Null graduate holdout maximum (ADR-226)

NullCalibration.max_holdout_sharpe equals the maximum score in its required
graduate list, or None exactly when empty. F176's contradictory finite maxima
fail on construction and authoritative merge input reconstruction, including
legacy records without joints. Nonpassing joint finalists are excluded; the
trial-wide max_deflated_sharpe is not inferred from selected graduate margins.
Signed scores, ordering, sources, thresholds and fingerprints retain their
meaning. F177 separately records the displayed-deflation-bar relationship gap
corrected by ADR-227 below: merge previously normalized that false claim while
direct construction accepted it.

### Null displayed bar and complete searched histories (ADR-227)

When holdout_years has one measurement per searched symbol, NullCalibration
requires a finite positive median, a finite unchanged ADR-018 expected maximum
at enclosing N, and exact agreement of deflation_bar with that value. F177's
false displayed benchmark and nonfinite derived evidence fail before merge can
normalize them. Incomplete or empty legacy histories remain unmeasured for this
relationship. The display uses all searched histories; individual strict survival
continues to use each graduate's own history. Power fields, approximation,
thresholds, producers, fingerprints and generated records retain their meaning.

### Unique known null graduate identities (ADR-228)

Every NullCalibration requires unique graduate symbols, including legacy records
without joints. F178's ambiguous repeated labels fail on construction and merge,
including collisions across individually valid shards. This refuses an unsafe
distinct-symbol claim; repeated labels do not prove identical underlying RNG
paths. No missing nongraduate identity is inferred, and no namespace, deduplication
or count rewrite is introduced. Empty/distinct graduates, order, legacy evidence,
combined-N arithmetic, thresholds and sources retain their meanings.

### Finite derived reference-score evidence (ADR-229)

The shared oracle_sharpe_of scorer refuses nonfinite derived net returns before
dropna, nonfinite sample mean/standard deviation and a nonfinite annualized score.
F179 shows finite costs can otherwise become a false zero through variance
overflow or NaN through turnover-cost overflow. Historical and explicit-drift
AR wrappers inherit refusal. Ordinary native scores, cost defaults, sign/lag/
startup, ddof=1, short histories and genuine finite zero variance are preserved.
No scaled fallback, clipping, filtering, new original-scalar policy, historical
relabeling, threshold or fingerprint change is introduced.

### Original reference close-source evidence (ADR-230)

All three reference scorer entries validate complete finite strictly positive
real nonboolean numeric closes before pct_change or short-history shortcuts.
F180's missing, negative and complex prices cannot become finite effect-size
claims through dropped returns or real-component projection. Original numeric
Series feed unchanged native scoring; complete nullable and empty numeric input
remain supported. Conditional-mean missing startup stays flat. This establishes
source-value validity, not calendar causality, reference optimality or universal
extreme arithmetic precision. No thresholds, defaults, fingerprints or data change.

### Reference source calendar ordering (ADR-231)

The shared checked-return helper requires unique ascending source indexes before
return construction and short-history shortcuts. F181's later-dated AR lag and
ambiguous duplicate observations fail through all three entries. No sorting or
deduplication occurs; ordered generic and naive/aware indexes retain exact scores.
This makes positional adjacency consistent with source index ordering, without
certifying arbitrary supplied predictions, daily cadence or acquisition lineage.
Defaults, references, thresholds, fingerprints and generated records stay intact.

### Original reference cost evidence (ADR-232)

The generic scorer validates original cost as finite float-representable real
nonboolean evidence before its negative comparison and short-history shortcut.
F182's boolean/nonfinite costs cannot obtain measured-looking reference scores;
historical AR inherits this guard and explicit AR retains ADR-223 precedence.
Validation preserves the original native cost operand and original negativity
comparison, including exact negative values rounding to signed zero. No finite
cost cap, prediction policy, default, method, threshold, fingerprint or data
change. Scalar validity does not certify every mixed-dtype/extreme calculation.

### Present reference prediction evidence (ADR-233)

Before sign or short-history shortcuts, the generic scorer requires real
nonboolean numeric conditional means and finite float-representable present
values across every supplied label. F183's infinite/complex predictions cannot
become finite effect sizes. Missing means, nullable input, sparse coverage and
unmatched labels retain their established flat semantics; scoring uses the
original Series. No prediction-index/completeness/fitting/causality guarantee,
reference/default replacement, threshold, fingerprint or generated data change.

### Band-filter observed log-price evidence (ADR-234)

filtered_deviation requires one-dimensional original real nonboolean numeric
complete finite float64-representable log-price observations after existing
parameter checks and before recursion. Masked entries are missing source
evidence; invalid observations cannot disappear into flat forecasts (F184).
Validation preserves original np.diff input, native dtype arithmetic, signed
logs, empty/singleton sources and first-unmeasured estimates. No source repair,
parameter/initialization/optimality change, threshold, fingerprint or generated
data change. F159 remains Open; derived arithmetic and precision are separate.

### Band-filter original process scalars (ADR-235)

filtered_deviation requires original finite float-representable real nonboolean
rho, level_vol, deviation_vol and drift before source recursion. Validation
retains original operands and exact range comparisons: stationary rho, zero
level noise allowed, strictly positive deviation noise and signed drift. F185
invalid process evidence cannot become missing forecasts and finite scores.
Scalar validity precedes combined malformed scalar inputs; existing valid-range
errors still precede source errors. No normalization, initialization, filter
formula, reference/default, threshold, fingerprint or data change. Derived
arithmetic and general mixed-type measurability remain separate; F159 stays Open.

### ADR-236 — Native filter arithmetic must remain measurable (2026-10-11)

FINDING-186 extends original scalar/source validation: finite volatility can
square to infinite noise or zero covariance, and finite innovations can overflow
a recursive residual. Missing/zero states can otherwise become finite reference
scores. Refuse nonfinite initialized noise/covariance and recursive quantities;
require original finite residual variance strictly positive before division.
Inspect separate float64 inspection arrays without replacing native operands (including
Fraction object arrays). Preserve zero level noise, semidefinite covariance and
startup NaN; translate native arithmetic overflow into ValueError and restore
caller NumPy policy. No floor, scaling recovery, precision/conditioning guarantee,
initialization or reference change; FINDING-159 remains Open.

### ADR-237 — Preserve original band-generator scalar provenance (2026-10-11)

FINDING-187 records boolean half-life/share/volatility/start price becoming finite
sources and reference scores after arithmetic erased their original types.
mean_reverting_edge now validates original finite real nonboolean half_life,
deviation_share, total_vol, drift and start_price without replacing operands.
Retain n_bars-first and existing half-life/share range precedence; no new domain,
seeded draw, initialization, reference, threshold or fingerprint change. Exact
negative Fraction range comparisons remain original; general mixed-type producer
support and derived source arithmetic remain separate. FINDING-155/159 stay Open.

### ADR-238 — Refuse wrapped native integer filter differences (2026-10-11)

FINDING-188 records unsigned decreases and signed overflow becoming finite false
innovations/states. After original source guards, require exact adjacent Python
integer differences within the original np.iinfo range. Refuse otherwise and keep
original np.diff for accepted sources. Do not float-normalize observations:
uint64[max-1,max] has difference one that float projection erases. Signed decreases,
nondecreasing unsigned sources, inclusive boundaries, masks, byte order and short
histories remain supported. No precision guarantee, source reconstruction,
initialization/reference/threshold/fingerprint change; FINDING-155/159 remain Open.

### ADR-239 — Source-facing band reference qualifications (2026-10-11)

FINDING-159 stays Open. Source docstrings/comments now match the existing UI and
finding: supplied lagged sign-reference scores use simple returns; band fields
store historical latent/filtered log-mean predictions. The specified zero-state,
diagonal-covariance filter initialization is not certified MMSE, and the score gap
is not an upper bound or proof of irrecoverable edge. Generator normalization and
predictable fractions concern stationary log-return variance, not realized
volatility or simple-return/Sharpe bounds. Executable AST, defaults, field names,
source draws, fingerprints, thresholds and artifacts are unchanged. F155's AR
attribution and F159's mathematical/posterior correction remain separate and Open.

### ADR-240 — Original legacy AR reference coefficient evidence (2026-10-11)

FINDING-189 records original boolean/NaN phi obtaining finite reference scores,
and infinite phi on flat prices becoming all-missing predictions and score zero.
oracle_sharpe validates original finite real nonboolean phi before returns, without
replacing its multiplier. Invalid phi now precedes source errors; valid-phi
source-before-delegated-cost ordering stays unchanged. No new stationarity range,
lag/cost/default/reference/source/threshold/fingerprint change. General mixed-type
support stays separate; F155's omitted drift/production attribution and F159's
band mathematical/posterior qualifications remain Open.

### ADR-241 — Original optional power process metadata (2026-10-11)

FINDING-190 records coercive boolean/string and nonfinite phi, half_life and
deviation_share evidence in PowerCalibration and reconstructed sweeps. One before
validator preserves None/absence and otherwise uses the established original
finite real nonboolean leaf guard. Existing float normalization and broad finite
domains remain; this does not certify generator domains or process-family
completeness. No source, reference, threshold, fingerprint or artifact change.
FINDING-155 and FINDING-159 remain Open.

### SIC composition-test publication (ADR-242)

ADR-161's SIC division test is a completed single look; its published result
cannot authorize another inference on the growing pools. FINDING-191 exposed
the driver's unconditional recomputation and replacement path. The driver now
refuses an occupied output before input access and publishes exclusively, so a
late competing result retains its bytes. No actual-cohort rerun, statistic,
seed, run gate, classification or generated-data change. This guards published
results and replacement; it does not serialize concurrent absent-start analyses
or guarantee atomic completion after process interruption. A follow-up still
requires its own pre-registration.

### Finite derived power capture evidence (ADR-243)

FINDING-192 shows that finite power-array elements can still yield infinite
capture, false zero or a false noise refusal. All four capture accessors check
the existing executed native medians, history years, unchanged Lo standard error
and quotients, and normalize arithmetic overflow to ValueError. Native history
operands, ordinary exact values, signed zero, finite underflow and legitimate
partial/legacy/noise refusals persist. Incomplete categories remain omitted.
This fails closed without estimator recovery, filtering or threshold changes;
some representable mathematical ratios with overflowing native intermediates
are refused. It does not certify finite precision or resolve FINDING-155/159's
reference qualifications. No source, search, fingerprint or artifact change.

### Bootstrap source observation identity (ADR-244)

FINDING-193 reproduces duplicate-label expansion that pairs a sampled return
with another source bar's geometry; reordered calendars also change adjacency.
bootstrap_null now requires a unique increasing source index before calculating
returns or drawing randomness. It refuses rather than sorting or deleting source
observations. Ordered generic, naive, aware and irregular calendars keep exact
native seeded outputs; empty/singleton and n_bars refusals retain precedence.
This establishes the source-calendar boundary only, without a new price/geometry
policy. Synthetic direct-call evidence does not establish production corruption,
changed null rates or false graduates. No cohort, search, threshold, fingerprint
or generated artifact changes.

### Finite paired power capture deltas (ADR-245)

FINDING-194 records finite capture endpoints overflowing native subtraction in
compare_power_sweeps; JSON rendered those invalid deltas as unmeasured nulls.
The matched capture-difference producer now refuses a nonfinite executed result
after its original None early return. Exact finite native differences, signed
zero, missing/unmatched/noise refusals and finalist attribution persist. Direct
comparison-row construction is outside this guard. Synthetic records do not
establish corrupt production comparisons or revised calibration rates. No
estimator, threshold, source, search, fingerprint or generated artifact change.

### Unique paired capture cell identity (ADR-246)

FINDING-195 follows ADR-103/FINDING-035's existing refusal of ordering-selected
evidence at the separate ADR-057 capture consumer. Duplicate effect keys silently
selected the last cell and could reverse an attributable delta's sign. The
capture comparator now refuses collisions within either side after its existing
identity refusals and before dictionary construction, using its unchanged
phi/half-life/legacy-zero key. Equal signed zero and identical duplicates collide.
Unique matched/unmatched output and attribution remain exact; collection/schema
and nested wrapper binding remain separate. No production duplicate or changed
rate is inferred from synthetic evidence; no threshold or artifact change.

### Nested paired capture identity (ADR-247)

FINDING-196 follows ADR-103's nested-binding principle at the capture consumer:
matched headers could mislabel cells' process, gate, search or measured history.
Before reading endpoints, capture comparison binds cell edge/gate/search to the
header and checks each recorded history's original int(median(n_bars)) summary.
Nonempty all-absent histories require the collector's zero marker. Partial,
heterogeneous and mixed known/absent histories and direct empty sweeps retain
existing meaning; probability strong-cell completeness is not imported. Native
summary overflow refuses without changing the median. Earlier header/duplicate
refusals persist. Synthetic mislabeled wrappers do not establish corrupt artifacts
or revised rates; no reference, threshold, source, search or artifact changes.

### AR power CLI positional identity (ADR-307)

The AR driver excludes known option values by token position rather than their
text. Otherwise seed7400 with --n-bars7400 silently becomes seed0, and an equal
symbol-count token can disappear. First-option lookup, defaults, positional order,
seed/shard arithmetic, generators and search remain. Repeated option values are
all excluded from positionals while the first wins; new value flags must join the
registry. Mocked CLI evidence establishes the parser defect, not an affected
historical cohort. No source/cohort retry, threshold or v14 change (F262).


### Explicit AR reference attribution (ADR-308)

The supported production opt-in carries `ar1_reference` on cells and sweep.
Known legacy phi-lag sign has null drift; conditional-mean sign requires explicit
original finite float-representable nonboolean Real drift and stationary phi.
The driver passes the same explicit drift to source and reference; arbitrary
supplied-frame law correspondence remains the caller's responsibility. Default
legacy math/calls remain. Historical absent/null metadata remains unknown.

Authoritative model reconstruction and collection bind header/cell identity;
capture comparison refuses known/unknown or unequal method/drift after its
existing header/search guards. None/None retains historical comparison semantics.
Detection-only probability-DSR comparison retains joint-count math and existing
identity rules; central sweep coherence still applies. Method is not a search
fingerprint or gate threshold. Reports/API/UI retain attribution and describe
selected in-sample reference-relative ratios, with gross/net cost distinctions.

ADR-223 and F173 paragraphs above record their historical adoption boundaries;
ADR-308 supplies the separately governed production opt-in. No historical scores,
source draws, generated artifacts, accounting-v14, gate/search or thresholds are
changed. No new power estimate is claimed. Neither sign reference certifies
cost-aware optimality, a sample maximum or absence of tradeable edge. F159's
band-reference issue remains separate and open.

### Band-filter startup evidence (FINDING-159, 2026-10-17)

The zero-initialized band generator has first deviation variance
`q=deviation_vol²*(1-rho²)`, while the historical filter's first difference
update uses a stationary deviation prior. Exact Gaussian conditioning of a
hand-built two-price example gives different gains (historical 0.4 versus
zero-init differences-only 9/19). Including the first price with a known source
start gives a third gain 45/67. These are distinct information sets, not empirical
power results. F159 records the matrices, probe and independent reproduction.
No filter correction, historical remeasurement or source-law inference is made;
a future posterior/reference contract must explicitly choose startup law and
observations and retain posterior variance for simple-return prediction.

### Holdout predicate projection (ADR-309 / FINDING-256)

The gate retains original native comparisons but refuses a result if converting
Sharpe and the active benchmark to binary64 changes either holdout predicate.
The checked Sharpe snapshot is published. This accepts same-side rounding and
refuses both exact positive underflow and NumPy-native false/projected-true
threshold mismatches, without changing thresholds or using projected decisions.
An inactive benchmark remains inactive. Original total-return wealth validity
and exact integral count normalization stay; downstream wealth projection is
separate. The guard acts while source/config are available and does not make
GateResult, which lacks benchmark/floor fields, a complete replay record.

### Explicit full-price band posterior (ADR-310)

`research/lab/band_posterior.py::band_price_posterior` takes explicit rho,
level/deviation volatility, drift and known pre-shock start price. Under known
zero pre-shock level/deviation it returns owned posterior mean/variance arrays,
conditioning on all prices through each index, including the first price.
It computes a declared binary64 law from validated original scalars and a copied
complete real numeric ndarray. Empty valid sources return empty arrays after
law validation; singletons assimilate their first observation. Genuine zero
level noise remains valid; positive noise/uncertainty lost to zero refuses.

The fixed variance recurrence uses a nonnegative determinant expression rather
than cancellation/clipping. ADR-310 records formulas and precision limits. This
standalone helper does not replace the historical filter, alter any generator or
score, infer source provenance, or wire a production reference. F159 remains Open
for separately attributed simple-return references; posterior correctness does
not certify strategy optimality or measured power.

### Horizon power CLI positional identity (ADR-311 / FINDING-263)

The horizon driver follows ADR-307's token-position policy for --out, --half-life,
--deviation-share and --n-bars. Equal count/seed text remains independent; every
repeated option value is excluded by position while first-option lookup stays.
Defaults, source/scorer/measurement calls, seed+i, report/output behavior and
scientific identity remain. No historical affected cohort is established and
no source retry or artifact rewrite follows from this parser correction.

### Horizon reference-report qualification (ADR-312 / FINDING-159)

Horizon console gross/net latent and specified filtered net scores are reference
strategy comparisons, with selected in-sample, selection-biased ratios. Historical
log-mean signs are scored on simple returns; historical filter startup/posterior
is uncertified. No upper bound, cost-aware optimum, realized-sample maximum or
no-edge inference follows. A refused filtered ratio covers existing completeness,
history and denominator requirements; it cannot be described solely as low signal.
Numeric fields, refusal predicates, display presence policies, calls and artifacts
remain unchanged. This is reporting, not activation of ADR-310 or a corrected
method. F159 remains Open; historical tables retain their original bytes.

### Explicit band simple-mean sign reference (ADR-313)

The optional versioned `band_reference` retains explicit drift, total volatility
and known pre-shock start price at cell and sweep. Known cells bind band edge,
absent phi, present half-life/share and AR/band exclusivity. Original and
normalized scalar ranges validate before existing coercion; original share<1
rounding to1 refuses lost positive level noise. Historical absence stays unknown.
The conditional mode normalizes one nominal binary64 Gaussian law, preserves the
historical generator recipe and uses the unchanged ADR-310 full-price posterior.
Rounded innovation sampling scale and nominal q need not agree bitwise; no
universal source-law correspondence or conditioning accuracy is certified.

All-symbol source/deviation snapshots and aligned predictions validate before
any reference scorer/search. Index0 is unavailable; observed prediction index1
uses posterior index0. Latent variance is q+R; observed variance also includes
(rho-1)^2 times previous posterior variance, refusing a lost-positive component.
The fixed finite score 2*m+V supplies only a sign to the existing gross/net scorer.
Gaussian monotonicity and exact binary64 lattice arithmetic preserve the sign of
computed finite m,V under gradual underflow; this does not certify earlier
exact-law arithmetic or an expected-return magnitude. No numerical fallback,
extra lag, fitting, cost model or detection/search/count change is introduced.

Measurement owns all three arrays in known mode and rejects external arrays or
contradictory mode evidence before scientific execution. Conditional CLI requires
explicit law flags and validates before generation; legacy calls remain exact.
Collection/model reconstruction preserve common identity. Capture comparison
refuses known/unknown or unequal common identities after existing header guards,
and mismatched shares at matched known-band half-lives after structural checks
but before row arithmetic. Unmatched cells retain no-delta rows; unknown/unknown
retains historical semantics. Detection-only probability inference stays intact.
API/UI/reports preserve attribution, coordinates, unknown provenance and all served
values. The reference is neither cost-aware optimal nor a sample maximum, bound
on every causal strategy, no-edge result or newly measured power curve.

F159's supported explicit production correction gap is resolved by ADR-313.
Historical scores/unknown metadata and all provenance/optimality qualifications
remain; this opt-in is not a fresh power measurement or artifact migration.
