# ADR-376: Preregister one sparse-jump additive martingale null

- **Status:** Accepted — prospective protocol; no sources or measurement yet
- **Date:** 2026-10-26
- **Deciders:** Codex autonomous session1, ISO2026-W44; research/data review
- **Extends:** ADR-036/037/044/046/048/050
- **Relates to:** ADR-338/358, FINDING-241/243/286

## Question and alternatives

Does the unchanged default longitudinal pipeline falsely graduate on a discrete,
strongly asymmetric price martingale with rare positive jumps and endogenous
simple-return scale? This differs from completed Gaussian/Student-t5 controls,
symmetric absorption and persistent-variance protocols. It changes several source
properties together; any difference cannot be attributed to skewness alone.
This is a distinct prospective law, never a replacement, continuation or pooled
extension of a completed/incomplete cohort. All old cohorts/timing roots stay frozen.

Keeping existing controls leaves this question unmeasured. Mirroring, reflecting,
conditioning on jump counts, redrawing a quiet path or tuning the law after results
would change the question; none is allowed. No search pilot or old timing rerun.

## Fixed law and numerical scope

Exactly N=200 sources, 7,400 bars each, seeds2026102601000+i for i=0..199.
Require NumPy default_rng/PCG64 and exactly one
integers(0,1024,size=7399,dtype=np.int64) draw per seed. Symbols
V14SPARSEW44S1_0000..0199. Pre-adoption namespace/seed text search found no overlap.

Let integer X0=16384. Each draw0 gives increment+1023; all other draws give-1.
Xnext=Xprev+increment; close=X/128. Across the full finite horizon,
8985<=X<=7585561: integer states and dyadic Float64 prices are exact, positive
and bounded. No clipping, absorption, reflection, repair, resampling or selection.
The ideal conditional increment mean is (1023/1024)*(-1)+(1/1024)*1023=0;
variance is1023. Thus next simple return has conditional mean zero at each state.
A fixed bounded predictable position has zero expected next-bar gross simple P&L;
nonnegative turnover costs cannot create an expected edge. This is not a claim
about search-selected in-sample Sharpes, zero log drift or guaranteed zero events.

Native ratio-minus-one returns are rounded, not an exact numerical martingale.
Ratios lie between0.5 and2, so Sterbenz makes subtraction of1 exact after division.
Under correctly rounded binary64 division, a conservative conditional-mean error
bound is (1025/1024)*2^-54, about5.55654e-17. This bounds that operation only,
not indicators, wealth, costs or estimators. Keep unmodified native arithmetic.

Expected full-path jumps=7399/1024=7.2255859375. Over1480 held-out innovations,
the ideal zero-jump probability is (1023/1024)^1480≈0.235506. These are design
characteristics, never sample-admission criteria or subset test denominators.
Retain every original quiet/no-jump path. No iid-return or market-realism claim.

Use generic business-day UTC labels from2000-01-03, explicitly nanoseconds.
open0=close0; later open=previous close; high=max(open,close); low=min(open,close);
volume=1,000,000. Columns open,high,low,close,volume, all native Float64.
Completed-bar information has no next innovation; engine position.shift(1) stays.
Calendar/geometry/volume are synthetic, not vendor/liquidity/holiday evidence.

## Published procedure and artifact contract

Publish this protocol and verify exact master CI before original source draws.
Controlled fake RNG/search tests and independent presearch/final-auditor readiness
must precede draws. Scratch runner /tmp/qf-w44-s1-sparse-null.py, law helper
/tmp/qf-w44-s1-sparse-law.py, independent auditor
/tmp/qf-w44-s1-sparse-audit.py; root /tmp/qf-w44-s1-v14-sparse-jump created
exclusively. Missing historical scratch runners do not authorize recreating old
cohorts/helpers and imply nothing about interruption causes or activity.

Bind runner/helper/auditor/protocol bytes, executed full revision, full tracked
backend/app content, lock/dependency/RNG versions, NumPy policy, relevant thread
environment, exact catalog/grids and gate/search fingerprints before searching.
Only explicit revision literals may change when binding tested scripts to the
published protocol revision; compare complete ASTs excluding only those literals.
No live settings dump, keys, providers, brokers or generated repository writes.

Freeze all200 originals in exclusive pickle-free sources.npz with exactly
values(native Float64,shape200x7400x5) and calendar_ns(int64,shape7400) arrays.
No object/pickle arrays; load with allow_pickle=False. Metadata records source
law, ordered seeds/symbols, per-source canonical decompressed array/calendar
hashes, ordered aggregate hash and actual archive hash. Keep archive and logical
hashes separate. Exclusive JSON writes flush/fsync; no overwrite/repair path.

Independent presearch audit must reconstruct all200 exact seed/law sources
read-only, validate every byte/hash/dtype/shape/calendar/OHLCV and environment/
code/settings binding, then exclusively write presearch-audit.json proving
200 valid originals and zero searches. Absent/partial/mismatched audit refuses.
Any actual source/draw/audit failure stops the cohort without repair/redraw/retry.

Use unmodified calibrate_gate once per source with custom null_mode
sparse_jump_additive_martingale_v14_w44s1, canonically sorted34 catalog names,
default GateConfig/candidate budget200, n_per_param3, refine=True/span0.25,
observed selection, prior_trials0 and no ExperimentStore. Search5920/holdout1480
bars; deflation holdout years1480/252. No new source, estimator, gate, selector,
threshold or accounting-v14 change. New direct-search admission policy stays
unknown; no universe pre-screen is introduced.

A record-only observer verifies exact call identity, exclusively checkpoints the
original validated Experiment, and returns the same object without modifications.
Each symbol has durable START before search, original Experiment and official
one-symbol calibration shard, then durable DONE binding their hashes. Stop on
any error; retain ERROR/unresolved START/partial bytes and never substitute them.
No error or incomplete source becomes a zero/non-graduate.

## One invocation and feasibility

One exclusive execution identity records one7,200-second soft admission clock
only after all preflight/audit evidence passes. No new source starts at/after its
deadline; an admitted call may finish afterward. No budget renewal, source retry,
fresh continuation, marker removal, repair, redraw or replacement attempt.
A later invocation permits all-complete read-only replay only, never new searches.
Interruption, error, unresolved START or missed admission means permanently
incomplete; publish only inventory/status, no partial rates or inferred causes.

Published longitudinal controls near2,270–2,312seconds support planning only;
completion/runtime for this new law is unestablished. This five-hour session
started07:00UTC. If protocol CI, controlled tests and auditor readiness are not
complete by08:45UTC, defer original draws. Admit the single fresh execution only
by09:00UTC, preserving at least the entire7200s plus substantial audit/gate/CI
margin before12:00UTC. Neither deadline is extended because outcomes or progress
look promising. A hanging admitted call can still cause incomplete execution;
no completion guarantee or unbounded final-call allowance is promised.

## Inference and reporting

Only all200 original completions, zero errors and independent final source/code/
identity/model/selection/joint-gate/count audits authorize rates. Recompute strict
ADR-018 survival with unmodified merge_calibrations at combined N200, never sum
shard survivors. Preserve all original Experiments and diagnostic missingness.
Report both endpoints, component counts and marginal one-sided95% exact binomial
upper limits: Beta.ppf(.95,k+1,200-k) for k<200;1 for k=200. At zero use
-expm1(log(.05)/200)≈1.4867%, not a zero-population-rate guarantee. Endpoints are
correlated on the same200 sources, not400 independent observations; no simultaneous
coverage or cross-law pooled inference. Source-regime summaries are descriptive.

A false graduate or mechanics failure gets a written finding with unchanged
outcomes, never tuned parameters/thresholds. This law does not certify market
safety, general-null robustness, bootstrap calibration or AR power. It is not the
ADR-102 matched iid/bootstrap pair and cannot authorize probability-gate adoption.
Scratch retention is not guaranteed; retain law/seeds/code/environment identities.
All work is local/free; no API keys, paid services, cloud dispatch/resources,
broker actions, pool writes or generated data/*.json changes.

## Reversal

Before draws, defer/cancel by later decision. After freeze preserve all original
bytes and markers and publish complete or incomplete status; never rerun/replace.

## Execution disposition — 2026-10-26, session 3

At review at 17:01 UTC, the prescribed 08:45 readiness and 09:00 fresh-execution
admission deadlines had elapsed. Session 3 defers execution and does not extend
either deadline; no new execution may start under this protocol's expired window.
Session 3 initiated no original source draws or searches. This is an execution
disposition, not a calibration measurement or a claim of zero false graduates.

The retained scratch inventory contains law/auditor tooling and controlled-test
artifacts; the specified runner and actual cohort root are absent at the inspected
paths. This bounded inventory does not establish historical inactivity, source
loss or an interruption cause. It does not authorize recreating missing artifacts,
retrying any frozen cohort or treating missing completions as zero outcomes.

Independent research review approved this append-only disposition. The original
law, seeds, single-use identity and timing constraints above remain preserved.
Any future cohort requires a separate prospective decision and review; it must
not extend or revive this execution identity or replace an incomplete cohort.
