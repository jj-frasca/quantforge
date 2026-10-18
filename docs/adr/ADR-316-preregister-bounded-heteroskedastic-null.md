# ADR-316: Preregister one bounded heteroskedastic zero-mean null

- **Status:** Accepted — prospective protocol; no measurement yet
- **Date:** 2026-10-18
- **Deciders:** Codex autonomous session 31, ISO 2026-W42
- **Extends:** ADR-036/037/044
- **Relates to:** ADR-291, FINDING-241/243

## Question and rationale

Does the unchanged default longitudinal search/graduation procedure produce
false graduates on a specified zero-conditional-mean law with predictable,
time-varying variance? Completed F241 Gaussian and F243 Student-t5 nulls do not
answer this variance-schedule question. This is a distinct negative control,
not a retry, replacement, extension or pooled denominator for any prior cohort.
All incomplete AR/bootstrap attempts remain frozen and incomplete.

## Options Considered

1. One prospectively frozen bounded symmetric heteroskedastic cohort.
   - Pro: zero ideal-law conditional mean and strictly positive support prices,
     with a new variance stress independent of any observed search result.
   - Con: substantial local compute, nonstationary design, limited realism and
     risk of an incomplete single-use execution.
2. Mean-zero simple Gaussian increments with changing variance.
   - Pro: familiar conditional-normal model.
   - Con: unbounded support permits returns<=-1; redraw/conditioning changes law.
3. Rerun or replace the incomplete bootstrap/AR cohorts.
   - Pro: might complete a familiar measurement.
   - Con: prohibited by their frozen one-look protocols; not an option here.
4. Use only the completed constant-variance nulls.
   - Pro: no new computation or incomplete-cohort risk.
   - Con: leaves this specific variance-stress question unmeasured.

## Fixed source law

Exactly N=200 sources, each 7,400 price bars and 7,399 innovations. Source i uses
PCG64 through NumPy default_rng(seed=2026101809000+i), i=0..199. This namespace
was checked against all five current W42 frozen metadata seed ranges and repo
references before adoption. Symbols are V14HET31_0000..0199. No seed replacement.

For innovation j=0..7398, independently draw U_j uniformly from
[-sqrt(3),+sqrt(3)] using one uniform call per source. Set sigma_j=.005 when
floor(j/252) is even and .04 otherwise; r_j=sigma_j*U_j. Set close[0]=100 and
close[1:]=100*cumprod(1+r), using binary64 NumPy arithmetic. Thus each block
contains 252 returns, starting with low variance; the final block may be partial.

Under the ideal law E[r_j|past]=0 and Var[r_j|past]=sigma_j^2. Any causal
predictable position has zero expected next-bar gross simple return; nonnegative
turnover costs cannot create positive expected net return. Predictable variance
is not a directional conditional-mean edge. This does not guarantee zero
finite-sample Sharpe or zero false graduates. Binary64 RNG, prices and reconstructed
returns approximate the ideal law; exact numerical conditional means are not
certified. The generator has bounded support |r|<.07; even worst-support
7,399-step prices from100 stay positive and finite in binary64.

Use a generic business-day UTC calendar starting 2000-01-03 with explicit ns
resolution. open[0]=close[0], open[1:]=close[:-1]; high=max(open,close),
low=min(open,close); volume=1,000,000. Column order is open,high,low,close,volume.
No intrabar, volume, exchange-holiday or vendor-realism claim. All source bytes,
calendar units, metadata and their aggregate digest freeze before search.

## Frozen execution and audit boundary

Publish this protocol and verify exact CI before generating the actual cohort.
The one-off scratch runner uses existing audited checkpoint helpers without
changing them. Test its new mechanics with controlled fixtures outside the
cohort; fix bugs before any actual source draw. Bind the final runner bytes,
protocol, dependency/RNG versions, git revision, full backend/app source tree,
resolved grids, gate/search fingerprints and all source-law metadata at freeze.
The executed revision is the published protocol-bearing HEAD; it must remain
unchanged through execution. No inherited nonzero drift or scalar-volatility
metadata may survive into the new law's identity.

Exclusive root /tmp/qf-w42-s31-v14-heteroskedastic. One freeze only; all200 original
sources validate shape, native finite positive OHLCV, exact calendar/columns and
law/hash reconstruction before any search. An independent pre-search audit must
validate all200 with zero searches and exclusively write a receipt bound to the
frozen metadata, archive, ordered-source, protocol, runner and executed revision.
The run refuses without that receipt. Read-only deterministic source reconstruction
for equality checks is permitted; replacement files or new cohorts are not.

Call the unmodified calibrate_gate once per source, with custom null_mode
zero_mean_uniform_alternating_variance_v14_session31, all34 canonically ordered
catalog names, default GateConfig/candidate budget200, n_per_param3, refine=True,
refine_span=.25, observed selection, prior_trials0 and no ExperimentStore.
Search5,920/holdout1,480 bars; holdout1480/252 years. Preserve every raw Experiment
through an observational wrapper around the original run_search, verify exact
call identity/kwargs, and durably write START before the call plus completion or
error afterward. The underlying search and gate remain unmodified.

Exactly one fresh search-phase invocation has a fixed 7,200-second **soft
admission deadline**: no new original search starts at/after it; an admitted
in-flight call may finish later. The historical F241 2,290-second duration supports
planning margin, not a completion guarantee. Record this clock once after
preflight; never renew it. After execution.json exists, subsequent invocation is
completed-result replay only and must never start a fresh original search.

Any draw/source/audit failure aborts this cohort without repair/redraw; any
unresolved START/error/deadline/interruption preserves incomplete state. Never
retry sources, remove markers, resume fresh work, renew a clock or create another
replacement attempt. No partial rates or cause/activity inference. Complete
read-only replay requires all200 original experiments and shards with zero errors.

## Inference and limits

Only all200 completed exactly once, zero errors and passing independent final
identity/count/model/source audits authorize a cohort rate. Unmodified
merge_calibrations combines the one-symbol shards and recomputes ADR-018 at N200;
never add shard survivor counts. Preserve full experiments, selected joint gate
verdicts and diagnostic missingness. Report graduates, survivors, strict bar,
component counts and a one-sided95% binomial upper bound; zero events gives
1-.05**(1/200), not a zero population error guarantee. Graduation and survival
are two endpoints on the same200 sources, not400 independent observations.

A false graduate is a written finding, never permission to alter the source,
search or thresholds. Do not pool this cohort with Gaussian/t5 or frozen AR/
bootstrap attempts, attribute unpaired differences to variance alone, or claim
market safety, arbitrary-schedule robustness, bootstrap behavior or AR power.
The custom mode is not ADR-102's required matched iid/bootstrap comparison and
cannot authorize a probability gate or any threshold change.

All execution is local and free. No vendor/API key, paid API, cloud resources,
workflow dispatch, broker, generated data/*.json write, pool write, threshold,
search estimator or accounting-v14 change. Scratch retention is not guaranteed;
record exact law, seeds, code and environment for scientific reproduction.

## Pre-draw verification

The scratch runner's controlled tests observed 21 missing-implementation failures,
then a separate early CLI-guard failure and four pre-freeze identity failures
before their corrections. All29 controlled cases subsequently passed independently;
three observer controls were added after initial GREEN and are not claimed as
precode RED. Fake RNG/search fixtures forbid actual default_rng calls. Existing
checkpoint/observer operations retain the prior audited implementation, apart
from clarified soft-deadline wording. Final publication binds only the runner's
revision literal; its full AST and hashes are checked again before source freeze.
No actual cohort source, calibration or search existed at this preregistration.

## Reversal

Before any draw, cancel the protocol with a superseding decision. After freeze
or execution, retain every original byte and outcome/marker; report its complete
or incomplete status without rerunning/replacing it. Any genuinely different
future question requires a separately justified prospective protocol.
